# GitHub Actions secrets checklist (EC2 deploy)

Configure at: **Repository → Settings → Secrets and variables → Actions**

## Secrets (required)

| Name          | Value                                                                                                                      |
| ------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `EC2_HOST`    | `54.146.221.133`                                                                                                           |
| `EC2_USER`    | `ubuntu`                                                                                                                   |
| `EC2_SSH_KEY` | Contents of the `.pem` file used to SSH to the instance                                                                    |
| `ENV_FILE`    | Full production `.env` (same as on server). Include `POSTGRES_PASSWORD`, `JWT_SECRET_KEY`, `API_KEY`, `CORS_ORIGINS`, etc. |

## Variables (recommended)

**Settings → Secrets and variables → Actions → Variables**

| Name                    | Value                    |
| ----------------------- | ------------------------ |
| `EC2_REPO_ROOT`         | `/home/ubuntu/aibackend` |
| `VERIFY_SLEEP_SECONDS`  | `30`                     |
| `VERIFY_REQUIRE_DOCKER` | `1`                      |

## Verify setup

1. Complete [EC2.md](EC2.md) one-time host bootstrap.
2. Actions → **Deploy API to EC2** → **Run workflow** (workflow_dispatch).
3. Confirm green run; on server: `docker compose -f compose.yaml ps`.
4. `curl -fsS http://54.146.221.133:8000/health` from your machine.

Automatic deploys run after **API CI** succeeds on `main` (see `.github/workflows/deploy.yml`).
