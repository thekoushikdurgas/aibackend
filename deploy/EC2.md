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
nano .env   # production values — see below (do **not** use sudo nano / sudo chmod on .env)
chmod 600 .env
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

| Symptom                                                          | Check                                                                                                                                                                                                                             |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `validate_env: missing pydantic_settings` on host                | Expected without a venv. Use `bash deploy/remote-deploy.sh` (dotenv-only on host, full check in Docker). Do **not** `pip install -r requirements.txt` on Python 3.14.                                                             |
| `torch==2.2.0` not found (host pip)                              | Host `python3` may be 3.14; torch 2.2 has no wheel. Deploy via **Docker** only.                                                                                                                                                   |
| `python3-venv` / `ensurepip` errors                              | Optional for host venv; not required for Docker deploy.                                                                                                                                                                           |
| `docker compose` include error                                   | `docker compose version` ≥ 2.20                                                                                                                                                                                                   |
| `bitnami/kafka:3.7: not found` on `docker compose up`            | Bitnami removed public Kafka tags from Docker Hub. `git pull` (uses `apache/kafka:3.7.1` in `docker/docker-compose.yml`), then `bash deploy/remote-deploy.sh`. Remove old volume only if Kafka fails to start: `docker volume rm aibackend_kafka_data`. |
| `aibackend-kafka-1 is unhealthy` / `dependency kafka failed`     | Usually the healthcheck could not find `kafka-topics.sh` on PATH. `git pull` (healthcheck uses `/opt/kafka/bin/kafka-topics.sh`), then `bash deploy/remote-deploy.sh`. Confirm: `docker exec aibackend-kafka-1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list`. |
| Backend unhealthy                                                | `docker compose logs backend`                                                                                                                                                                                                     |
| Postgres connection refused                                      | `docker compose ps`; `db` healthy?                                                                                                                                                                                                |
| Ollama timeouts                                                  | Model pulled? `docker compose exec ollama ollama list`                                                                                                                                                                            |
| CORS errors in browser                                           | `CORS_ORIGINS` includes exact frontend origin                                                                                                                                                                                     |
| Deploy skips verify                                              | `VERIFY_REQUIRE_DOCKER=1`; docker on PATH for SSH user                                                                                                                                                                            |
| `curl: (56) Recv failure: Connection reset by peer` on `/health` | Backend still starting (Chroma/RAG lifespan). Re-run `bash deploy/verify-stack.sh` or set `VERIFY_SLEEP_SECONDS=30`. After `git pull`, verify retries HTTP automatically. Check `docker compose logs backend`.                    |
| `Restarting (1)` / `Could not connect to 127.0.0.1:8000`         | Backend **crash-loop**. `docker compose --env-file .env -f compose.yaml logs backend --tail 50` — common: `ModuleNotFoundError: imageio` → `git pull` and `bash deploy/remote-deploy.sh` (rebuilds image with full requirements). |
| `ModuleNotFoundError` in backend logs                            | Missing pip package in `requirements.txt` (e.g. `imageio`, `jwt` → install **PyJWT**). Rebuild: `bash deploy/remote-deploy.sh` or `docker compose … build backend && up -d --force-recreate backend`.                             |
| `OLLAMA_MODE … is not a valid OllamaMode` / IP in mode           | Set `OLLAMA_MODE=localhost` (or `cloud`). Put the server URL in `OLLAMA_BASE_URL` only. Compose overrides `OLLAMA_MODE=localhost` and `OLLAMA_BASE_URL=http://ollama:11434/api`.                                                  |
| Google/Gmail GraphQL `401` / OpenRouter/Groq `401`               | Missing or expired OAuth token / API keys in `.env` — configure in DurgasOS or disable those widgets until keys are set.                                                                                                          |
| Hyperbolic `402 Payment Required`                                | Billing/credits on Hyperbolic account, or remove key from `.env`.                                                                                                                                                                 |
| `validate_env --import-app exited 137`                           | Often OOM during import on small instances; deploy now runs import check in a one-off container **before** uvicorn starts.                                                                                                        |
| `Permission denied` on `.env` / `validate_env`                   | `.env` is root-owned from `sudo nano` or `sudo chmod 600 .env`. Fix: `sudo chown ubuntu:ubuntu .env && chmod 600 .env`, then re-run deploy. Edit with `nano .env` only (no sudo).                                                 |
| `permission denied` on `docker.sock`                             | After bootstrap: `newgrp docker` or exit SSH and reconnect; or re-run deploy (auto `sudo docker` fallback)                                                                                                                        |
| `cannot assign requested address` on `54.x.x.x:11434`            | Remove `OLLAMA_PUBLISH_HOST` / `*_PUBLISH_HOST` from `.env` if set to the public IP. Only port **8000** is exposed; Ollama is `http://ollama:11434` inside Compose.                                                               |
| `unexpected character "~" in variable name "[200~`               | Corrupted paste in `nano` (bracketed paste). Run `cp .env.example .env`, edit again, or `scp` a clean `.env` from your PC. Deploy scripts now sanitize KEY=VALUE lines automatically.                                             |
| `verify` Redis `got: <empty>` after long wait                    | Often a hung `docker exec` (Ctrl+C). Re-run `bash deploy/verify-stack.sh`; script uses timeouts and a container-running fallback.                                                                                                 |
| `verify` Postgres not ready but `db` is healthy                  | `docker exec` under sudo can fail while the DB is fine. Re-run verify after `git pull`; script falls back to compose health.                                                                                                      |
| `[200~curl: command not found`                                   | Bracketed-paste in SSH terminal — type commands manually or disable bracketed paste in your SSH client.                                                                                                                           |
