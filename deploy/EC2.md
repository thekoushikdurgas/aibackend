# EC2 Docker deployment (44.208.230.7)

**This is EC2 + Docker Compose production — not AWS Lambda.** A Lambda / API Gateway WebSocket rewrite is explicitly out of scope.

Production API: **HTTP** on port **8000** (no TLS in this setup; ALB/ACM is a follow-up when a domain is ready).

| Endpoint          | URL                                                   |
| ----------------- | ----------------------------------------------------- |
| Health            | `http://44.208.230.7:8000/health`                    |
| GraphQL           | `http://44.208.230.7:8000/graphql`                   |
| WebSocket gateway | `ws://44.208.230.7:8000/ws/gateway`                  |
| Socket.IO         | `http://44.208.230.7:8000/realtime` (default mount)  |

Compose entry for production: [`compose.prod.yaml`](../compose.prod.yaml) (includes [`compose.yaml`](../compose.yaml) → [`docker/docker-compose.yml`](../docker/docker-compose.yml)).

**Current host:** Elastic IP **`44.208.230.7`**, instance tag `aibackend-prod`, SG `aibackend-prod` (`sg-0d34473946f8d3ae1`). MinIO is optional (`--profile minio`) because Docker Hub often denies anonymous `minio/minio` pulls.

## One-time host setup

Run on the Ubuntu instance as `ubuntu` (or use [`ec2-bootstrap.sh`](ec2-bootstrap.sh)):

```bash
bash deploy/ec2-bootstrap.sh
```

### AWS security group

| Direction | Port                                      | Source                    | Purpose                                      |
| --------- | ----------------------------------------- | ------------------------- | -------------------------------------------- |
| Inbound   | 22                                        | Your IP                   | SSH                                          |
| Inbound   | 8000                                      | `0.0.0.0/0` or restricted | FastAPI API (HTTP + WebSocket + Socket.IO) |
| —         | 5432, 6379, 8001, 8080, 9000, 9001, 9090, 9092, 3001, 5050, 11434 | **Do not open** | Sidecars bind to **`127.0.0.1` only** via `COMPOSE_PUBLISH_HOST` (default). Security group must not allow them from the internet. |

Audit / tighten rules: [`harden-sg.md`](harden-sg.md).

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
- `JWT_SECRET_KEY` (â‰¥ 32 random chars), `API_KEY` (non-placeholder)
- `POSTGRES_PASSWORD` (strong; used by Compose `db` service)
- `CORS_ORIGINS` — include every browser origin that calls the API (e.g. `http://localhost:3000`, your Vercel URL)
- `USE_REDIS=true`
- `STORAGE_SIGNED_URL_SECRET` (random)

Do **not** set `COMPOSE_PUBLISH_HOST=0.0.0.0` on EC2. Leave unset (defaults to `127.0.0.1`) so Postgres/Redis/Chroma/Kafka/MinIO/admin UIs are loopback-only.

Compose overrides `DATABASE_URL`, `POSTGRESQL_URL`, `REDIS_URL`, and `OLLAMA_BASE_URL` inside the **backend** container. You do not need to set `OLLAMA_BASE_URL=http://ollama:11434/api` in `.env` unless running uvicorn outside Docker.

After first `docker compose up`, pull your default Ollama model:

```bash
cd /home/ubuntu/aibackend
docker compose --env-file .env -f compose.prod.yaml exec ollama ollama pull steamdj/llama3.1-cpu-only
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

`remote-deploy.sh` starts dependency services (db, redis, chromadb, kafka, minio, ollama), waits for them, then builds/recreates **backend**. It prefers `compose.prod.yaml`.

From your laptop (security group must allow 8000):

```bash
curl -fsS http://44.208.230.7:8000/health
# or
bash deploy/verify-public.sh
```

## GitHub Actions CI/CD

Repository: [thekoushikdurgas/aibackend](https://github.com/thekoushikdurgas/aibackend).

| Stage | Workflow | When |
| ----- | -------- | ---- |
| CI | [api-ci.yml](../.github/workflows/api-ci.yml) | Push/PR to `main` / `develop` |
| CD | [deploy.yml](../.github/workflows/deploy.yml) | After successful API CI on `main`, or **workflow_dispatch** |

### One-time: git checkout on the host

Actions runs `git fetch` + `reset --hard origin/main`. Bootstrap once:

```bash
bash deploy/bootstrap-git-on-ec2.sh
```

### Secrets / variables

See [GITHUB_SECRETS.md](GITHUB_SECRETS.md). Fast path (laptop, `gh` logged in):

```powershell
.\deploy\setup-github-secrets.ps1
```

| Secret / variable | Value |
| ----------------- | ----- |
| `EC2_HOST` | `44.208.230.7` |
| `EC2_USER` | `ubuntu` |
| `EC2_SSH_KEY` | Contents of `aibackend-ec2.pem` |
| `ENV_FILE` | Full production `.env` |
| `EC2_REPO_ROOT` | `/home/ubuntu/aibackend` |
| `VERIFY_REQUIRE_DOCKER` | `1` |
| `PUBLIC_VERIFY` | `1` |

### Triggers

1. **Automatic:** after API CI succeeds on `main` (`workflow_run`).
2. **Manual:** Actions → **Deploy API to EC2** → **Run workflow**.

The deploy job uses a **60m** SSH `command_timeout` (torch image builds exceed the appleboy default of 10m).

## DurgasOS / frontend

In `durgasos/.env` (or hosting provider env):

```env
NEXT_PUBLIC_BACKEND_URL=http://44.208.230.7:8000
BACKEND_GRAPHQL_URL=http://44.208.230.7:8000/graphql
```

Match `CORS_ORIGINS` on the API with your Next.js origin (e.g. `https://your-app.vercel.app`).

## Remote Ollama (optional)

If you use Ollama on another host (not the Compose `ollama` service), set in `.env`:

```env
OLLAMA_BASE_URL=http://<other-host>:11434/api
```

Stop or remove the `ollama` service in Compose to save RAM, or leave it unused.

## Troubleshooting

| Symptom                                                          | Check                                                                                                                                                                                                                                                                                    |
| ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `validate_env: missing pydantic_settings` on host                | Expected without a venv. Use `bash deploy/remote-deploy.sh` (dotenv-only on host, full check in Docker). Do **not** `pip install -r requirements.txt` on Python 3.14.                                                                                                                    |
| `torch==2.2.0` not found (host pip)                              | Host `python3` may be 3.14; torch 2.2 has no wheel. Deploy via **Docker** only.                                                                                                                                                                                                          |
| `python3-venv` / `ensurepip` errors                              | Optional for host venv; not required for Docker deploy.                                                                                                                                                                                                                                  |
| `docker compose` include error                                   | `docker compose version` â‰¥ 2.20                                                                                                                                                                                                                                                          |
| `bitnami/kafka:3.7: not found` on `docker compose up`            | Bitnami removed public Kafka tags from Docker Hub. `git pull` (uses `apache/kafka:3.7.1` in `docker/docker-compose.yml`), then `bash deploy/remote-deploy.sh`. Remove old volume only if Kafka fails to start: `docker volume rm aibackend_kafka_data`.                                  |
| `aibackend-kafka-1 is unhealthy` / `dependency kafka failed`     | Usually the healthcheck could not find `kafka-topics.sh` on PATH. `git pull` (healthcheck uses `/opt/kafka/bin/kafka-topics.sh`), then `bash deploy/remote-deploy.sh`. Confirm: `docker exec aibackend-kafka-1 /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list`. |
| Backend unhealthy                                                | `docker compose --env-file .env -f compose.prod.yaml logs backend`                                                                                                                                                                                                                       |
| Postgres connection refused                                      | `docker compose ps`; `db` healthy?                                                                                                                                                                                                                                                       |
| Ollama timeouts                                                  | Model pulled? `docker compose --env-file .env -f compose.prod.yaml exec ollama ollama list`                                                                                                                                                                                              |
| CORS errors in browser                                           | `CORS_ORIGINS` includes exact frontend origin                                                                                                                                                                                                                                            |
| Deploy skips verify                                              | Workflow defaults `VERIFY_REQUIRE_DOCKER=1`; docker on PATH for SSH user                                                                                                                                                                                                                 |
| `curl: (56) Recv failure: Connection reset by peer` on `/health` | Backend still starting (Chroma/RAG lifespan). Re-run `bash deploy/verify-stack.sh` or set `VERIFY_SLEEP_SECONDS=30`. After `git pull`, verify retries HTTP automatically. Check `docker compose logs backend`.                                                                           |
| `Restarting (1)` / `Could not connect to 127.0.0.1:8000`         | Backend **crash-loop**. `docker compose --env-file .env -f compose.prod.yaml logs backend --tail 50` — common: `ModuleNotFoundError` → `git pull` and `bash deploy/remote-deploy.sh`.                                                                                                     |
| `ModuleNotFoundError` in backend logs                            | Missing pip package in `requirements.txt`. Rebuild: `bash deploy/remote-deploy.sh`.                                                                                                                                                                                                      |
| `OLLAMA_MODE â€¦ is not a valid OllamaMode` / IP in mode           | Set `OLLAMA_MODE=localhost` (or `cloud`). Put the server URL in `OLLAMA_BASE_URL` only. Compose overrides `OLLAMA_MODE=localhost` and `OLLAMA_BASE_URL=http://ollama:11434/api`.                                                                                                         |
| Google/Gmail GraphQL `401` / OpenRouter/Groq `401`               | Missing or expired OAuth token / API keys in `.env` — configure in DurgasOS or disable those widgets until keys are set.                                                                                                                                                                 |
| Hyperbolic `402 Payment Required`                                | Billing/credits on Hyperbolic account, or remove key from `.env`.                                                                                                                                                                                                                        |
| `validate_env --import-app exited 137`                           | Often OOM during import on small instances; deploy now runs import check in a one-off container **before** uvicorn starts.                                                                                                                                                               |
| `Permission denied` on `.env` / `validate_env`                   | `.env` is root-owned from `sudo nano` or `sudo chmod 600 .env`. Fix: `sudo chown ubuntu:ubuntu .env && chmod 600 .env`, then re-run deploy. Edit with `nano .env` only (no sudo).                                                                                                        |
| `permission denied` on `docker.sock`                             | After bootstrap: `newgrp docker` or exit SSH and reconnect; or re-run deploy (auto `sudo docker` fallback)                                                                                                                                                                               |
| `cannot assign requested address` on `54.x.x.x:11434`            | Remove `OLLAMA_PUBLISH_HOST` / `*_PUBLISH_HOST` from `.env` if set to the public IP. Only port **8000** is exposed publicly; Ollama is `http://ollama:11434` inside Compose.                                                                                                              |
| Sidecar port reachable from internet                             | Compose binds sidecars to `127.0.0.1`. Also remove that port from the EC2 security group — see [`harden-sg.md`](harden-sg.md).                                                                                                                                                            |
| `unexpected character "~" in variable name "[200~`               | Corrupted paste in `nano` (bracketed paste). Run `cp .env.example .env`, edit again, or `scp` a clean `.env` from your PC. Deploy scripts now sanitize KEY=VALUE lines automatically.                                                                                                    |
| `verify` Redis `got: <empty>` after long wait                    | Often a hung `docker exec` (Ctrl+C). Re-run `bash deploy/verify-stack.sh`; script uses timeouts and a container-running fallback.                                                                                                                                                        |
| `verify` Postgres not ready but `db` is healthy                  | `docker exec` under sudo can fail while the DB is fine. Re-run verify after `git pull`; script falls back to compose health.                                                                                                                                                             |
| `[200~curl: command not found`                                   | Bracketed-paste in SSH terminal — type commands manually or disable bracketed paste in your SSH client.                                                                                                                                                                                  |
