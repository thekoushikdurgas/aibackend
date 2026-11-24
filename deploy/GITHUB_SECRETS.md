# GitHub Actions secrets checklist (EC2 Docker deploy)

**EC2 + Docker Compose — not AWS Lambda.**

Configure at: **Repository → Settings → Secrets and variables → Actions**  
Or run from this machine (requires `gh auth login`):

```powershell
cd ai.backend
.\deploy\setup-github-secrets.ps1
```

## Secrets (required)

| Name          | Value                                                                                                                      |
| ------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `EC2_HOST`    | `44.208.230.7`                                                                                                             |
| `EC2_USER`    | `ubuntu`                                                                                                                   |
| `EC2_SSH_KEY` | Private key for the instance (e.g. `%USERPROFILE%\.ssh\aibackend-ec2.pem`)                                                 |
| `ENV_FILE`    | Full production `.env` (same as on server). Include `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `API_KEY`, `CORS_ORIGINS`, etc. |

Do **not** put `COMPOSE_PUBLISH_HOST=0.0.0.0` in `ENV_FILE` on EC2.

## Variables (recommended)

**Settings → Secrets and variables → Actions → Variables**

| Name                    | Value                                              |
| ----------------------- | -------------------------------------------------- |
| `EC2_REPO_ROOT`         | `/home/ubuntu/aibackend`                           |
| `EC2_REPO_URL`          | `https://github.com/thekoushikdurgas/aibackend.git` |
| `VERIFY_SLEEP_SECONDS`  | `30`                                               |
| `VERIFY_REQUIRE_DOCKER` | `1` (workflow defaults to `1` if unset)            |
| `PUBLIC_VERIFY`         | `1` (Actions runner curls public `/health`)        |

## One-time EC2 git checkout

Actions deploys with `git fetch` + `git reset --hard origin/main`. The host must be a clone:

```bash
# On EC2 (preserves .env)
bash deploy/bootstrap-git-on-ec2.sh
```

Or from your laptop:

```powershell
ssh -i $env:USERPROFILE\.ssh\aibackend-ec2.pem ubuntu@44.208.230.7 "bash -s" < deploy/bootstrap-git-on-ec2.sh
```

## Pipeline flow

1. **API CI** (`.github/workflows/api-ci.yml`) on push/PR — lint, format, tests.
2. **Deploy API to EC2** (`.github/workflows/deploy.yml`) after successful API CI on `main`, or manual **workflow_dispatch**.
3. SSH to EC2 → sync `main` → write `.env` from `ENV_FILE` → `deploy/remote-deploy.sh` → `deploy/verify-stack.sh` → public `/health`.

Torch image builds need a long SSH command timeout (`command_timeout: 60m` in the workflow).

## Verify setup

1. Complete [EC2.md](EC2.md) host bootstrap + [harden-sg.md](harden-sg.md) SG audit + [bootstrap-git-on-ec2.sh](bootstrap-git-on-ec2.sh).
2. Set secrets (table above or `setup-github-secrets.ps1`).
3. Push deploy changes to `main`, or Actions → **Deploy API to EC2** → **Run workflow**.
4. Confirm green run; on server: `docker compose --env-file .env -f compose.prod.yaml ps`.
5. `curl -fsS http://44.208.230.7:8000/health` from your machine.
