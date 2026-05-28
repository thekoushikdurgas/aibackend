# EC2 deployment (54.146.221.133)

Production API: **HTTP** on port **8000** (no TLS in this setup).

| Endpoint          | URL                                                        |
| ----------------- | ---------------------------------------------------------- |
| Health            | `http://54.146.221.133:8000/health`                        |
| GraphQL           | `http://54.146.221.133:8000/graphql`                       |
| WebSocket gateway | `ws://54.146.221.133:8000/ws/gateway`                      |
| Socket.IO         | `http://54.146.221.133:8000/realtime` (default mount path) |

## One-time host setup

Run on the Ubuntu instance as `ubuntu` (or use [`ec2-bootstrap.sh`](ec2-bootstrap.sh)):

```bash
bash deploy/ec2-bootstrap.sh
```

### AWS security group

| Direction | Port                    | Source                    | Purpose                                 |
| --------- | ----------------------- | ------------------------- | --------------------------------------- |
| Inbound   | 22                      | Your IP                   | SSH                                     |
| Inbound   | 8000                    | `0.0.0.0/0` or restricted | FastAPI API                             |
| —         | 5432, 6379, 11434, 8001 | **Do not open**           | Compose binds these to `127.0.0.1` only |

### Clone and configure

```bash
git clone https://github.com/thekoushikdurgas/aibackend.git /home/ubuntu/aibackend
cd /home/ubuntu/aibackend
cp .env.example .env
nano .env   # production values — see below
```

**Required production `.env` fields:**

- `ENVIRONMENT=production`, `DEBUG=false`
- `JWT_SECRET_KEY` (≥ 32 random chars), `API_KEY` (non-placeholder)
- `POSTGRES_PASSWORD` (strong; used by Compose `db` service)
- `CORS_ORIGINS` — include every browser origin that calls the API (e.g. `http://localhost:3000`, your Vercel URL)
- `USE_REDIS=true`
- `STORAGE_SIGNED_URL_SECRET` (random)

Compose overrides `DATABASE_URL`, `POSTGRESQL_URL`, `REDIS_URL`, and `OLLAMA_BASE_URL` inside the **backend** container. You do not need to set `OLLAMA_BASE_URL=http://ollama:11434/api` in `.env` unless running uvicorn outside Docker.

After first `docker compose up`, pull your default Ollama model:

```bash
cd /home/ubuntu/aibackend
docker compose --env-file .env -f compose.yaml exec ollama ollama pull steamdj/llama3.1-cpu-only
```

## Manual deploy (fallback)

From `/home/ubuntu/aibackend`:

```bash
git fetch origin main
git reset --hard origin/main
# Ensure .env exists (edit locally or copy from backup)
bash deploy/remote-deploy.sh
bash deploy/verify-stack.sh
curl -fsS http://127.0.0.1:8000/health
```

From your laptop (security group must allow 8000):

```bash
curl -fsS http://54.146.221.133:8000/health
# or
bash deploy/verify-public.sh
```

## GitHub Actions deploy

Repository: [thekoushikdurgas/aibackend](https://github.com/thekoushikdurgas/aibackend).

### Secrets (Settings → Secrets and variables → Actions)

| Secret        | Example / notes                        |
| ------------- | -------------------------------------- |
| `EC2_HOST`    | `54.146.221.133`                       |
| `EC2_USER`    | `ubuntu`                               |
| `EC2_SSH_KEY` | Full PEM private key for the instance  |
| `ENV_FILE`    | Entire production `.env` file contents |

### Variables (optional)

| Variable                | Recommended                                     |
| ----------------------- | ----------------------------------------------- |
| `EC2_REPO_ROOT`         | `/home/ubuntu/aibackend`                        |
| `VERIFY_SLEEP_SECONDS`  | `30`                                            |
| `VERIFY_REQUIRE_DOCKER` | `1`                                             |
| `VERIFY_STRICT_READY`   | `0` (set `1` when all providers are configured) |

### Triggers

1. **Automatic:** after [API CI](../.github/workflows/api-ci.yml) succeeds on `main` (workflow_run).
2. **Manual:** Actions → **Deploy API to EC2** → **Run workflow**.

See also [GITHUB_SECRETS.md](GITHUB_SECRETS.md) for a copy-paste checklist.

## DurgasOS / frontend

In `durgasos/.env` (or hosting provider env):

```env
NEXT_PUBLIC_BACKEND_URL=http://54.146.221.133:8000
BACKEND_GRAPHQL_URL=http://54.146.221.133:8000/graphql
```

Match `CORS_ORIGINS` on the API with your Next.js origin (e.g. `https://your-app.vercel.app`).

## Remote Ollama (optional)

If you use Ollama on another host (not the Compose `ollama` service), set in `.env`:

```env
OLLAMA_BASE_URL=http://<other-host>:11434/api
```

Stop or remove the `ollama` service in Compose to save RAM, or leave it unused.

## Troubleshooting

| Symptom | Check |
| ------- | ----- |
| `validate_env: missing pydantic_settings` on host | Expected without a venv. Use `bash deploy/remote-deploy.sh` (dotenv-only on host, full check in Docker). Do **not** `pip install -r requirements.txt` on Python 3.14. |
| `torch==2.2.0` not found (host pip) | Host `python3` may be 3.14; torch 2.2 has no wheel. Deploy via **Docker** only. |
| `python3-venv` / `ensurepip` errors | Optional for host venv; not required for Docker deploy. |
| `docker compose` include error | `docker compose version` ≥ 2.20 |
| Backend unhealthy | `docker compose logs backend` |
| Postgres connection refused | `docker compose ps`; `db` healthy? |
| Ollama timeouts | Model pulled? `docker compose exec ollama ollama list` |
| CORS errors in browser | `CORS_ORIGINS` includes exact frontend origin |
| Deploy skips verify | `VERIFY_REQUIRE_DOCKER=1`; docker on PATH for SSH user |
| `permission denied` on `docker.sock` | After bootstrap: `newgrp docker` or exit SSH and reconnect; or re-run deploy (auto `sudo docker` fallback) |
