# Docker setup — DurgasAI Backend (`ai.backend`)

These files define **production** and **development** stacks. Images use **Python 3.11** (see `Dockerfile` / `Dockerfile.dev`).

## Step 1 — Prerequisites

- [Docker Engine](https://docs.docker.com/engine/install/) + Docker Compose v2 (**v2.20+** recommended if you use root `compose.yaml` with `include:`).
- Ports **free on the host**:
  - `8000` — API
  - `8080` — Supabase Kong (REST / Auth / Realtime / Storage API)
  - `3001` — Supabase Studio (dashboard)
  - `5432` — Postgres (Supabase DB)
  - `6379` — Redis
  - `8001` — ChromaDB (mapped from container `8000`)
  - `11434` — Ollama

## Step 2 — Self-hosted Supabase (recommended)

The stack includes **Supabase** services via [`docker-compose.supabase.yml`](docker-compose.supabase.yml) (merged by `include`). Components: Postgres (`db`), **Kong** API gateway, **GoTrue** (auth), **PostgREST**, **Realtime**, **Storage**, **pg-meta**, **Studio**, **Logflare** (analytics for Studio).

### 2a — Create `docker/supabase/supabase.env`

```bash
cd ai.backend
cp docker/supabase/supabase.env.example docker/supabase/supabase.env
# Edit: POSTGRES_PASSWORD, JWT_SECRET, ANON_KEY, SERVICE_ROLE_KEY, LOGFLARE_* tokens,
# PG_META_CRYPTO_KEY, SECRET_KEY_BASE, DASHBOARD_PASSWORD, etc.
```

Use the same values as in **`ai.backend/.env`** for Compose interpolation (`POSTGRES_PASSWORD`, `ANON_KEY`, `SERVICE_ROLE_KEY`, `JWT_SECRET`). Either duplicate keys into `.env` or maintain one file and symlink — Compose reads **`ai.backend/.env`** for `${VAR}` substitution in `docker-compose.yml`.

Official key generation (JWT / API keys):

- See [Supabase self-hosting Docker](https://supabase.com/docs/guides/self-hosting/docker#configuring-and-securing-supabase)
- Reference scripts in the upstream repo: `supabase/docker/utils/generate-keys.sh`

### 2b — Application schema + storage buckets (first deploy)

After Postgres is up:

```bash
docker compose -f docker/docker-compose.yml exec -T db psql -U postgres -d postgres < supabase/migrations/001_init.sql
docker compose -f docker/docker-compose.yml exec -T db psql -U postgres -d postgres < supabase/seed.sql
```

### 2c — URLs for clients

| Purpose                               | URL                                                    |
| ------------------------------------- | ------------------------------------------------------ |
| Kong / Supabase API (anon key)        | `http://localhost:8080`                                |
| Studio                                | `http://localhost:3001`                                |
| Backend → Supabase **inside Compose** | `http://kong:8000` (set via `SUPABASE_URL` in compose) |

Backend [`app/config.py`](../app/config.py) merges **`SUPABASE_*` and `DATABASE_URL`** environment variables over `config.json`, so Docker env wins.

## Step 3 — Environment file (`ai.backend/.env`)

Compose references **`../.env`** from files under `docker/`, i.e. **`ai.backend/.env`** next to `compose.yaml`.

```bash
cd ai.backend
cp .env.example .env
# Edit: API keys, JWT_SECRET_KEY, POSTGRES_PASSWORD, ANON_KEY, SERVICE_ROLE_KEY, JWT_SECRET, SUPABASE_* ...
```

If `.env` is missing, Compose may fail on `env_file`. Creating an empty `.env` is enough for some setups; production should set secrets explicitly.

## Step 4 — Configuration JSON

Mount **`config/config.json`** read-only (already wired in compose). Ensure it exists:

```bash
cp config/config.example.json config/config.json
```

For Docker, prefer leaving Supabase fields empty in JSON and **driving URLs/keys from `.env`** (`apply_environment_overrides` in `app/config.py`).

## Step 5 — Choose a stack

### Quick start

Bootstrap scripts create `.env` from `.env.example` and `docker/supabase/supabase.env` from `supabase.env.example` when missing, then run Compose with both env files.

**Linux / macOS** — from **`ai.backend`**:

```bash
chmod +x scripts/docker-up.sh
./scripts/docker-up.sh
```

Development stack:

```bash
./scripts/docker-up.sh dev
```

**Windows** — from **`ai.backend`**:

```bat
scripts\docker-up.bat
```

Development stack:

```bat
scripts\docker-up.bat dev
```

### Production-like stack (Supabase + Redis + ChromaDB + Ollama + backend)

From **`ai.backend`** (requires both env files so `${POSTGRES_PASSWORD}` and keys interpolate):

```bash
docker compose --env-file .env --env-file docker/supabase/supabase.env -f docker/docker-compose.yml up -d --build
```

Or with root compose (**Compose 2.20+**):

```bash
docker compose --env-file .env --env-file docker/supabase/supabase.env -f compose.yaml up -d --build
```

### Development stack (mounted source, `--reload`, Redis + ChromaDB + Ollama + Supabase)

```bash
docker compose --env-file .env --env-file docker/supabase/supabase.env -f docker/docker-compose.dev.yml up --build
```

Or:

```bash
docker compose --env-file .env --env-file docker/supabase/supabase.env -f compose.dev.yaml up --build
```

### Supabase only (optional)

```bash
docker compose -f docker/docker-compose.supabase.yml --env-file docker/supabase/supabase.env up -d
```

You must attach services to `durgasai_network` — easiest to use the **full** compose files above, which `include` Supabase and define the network.

## Step 6 — Verify

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ | head
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/rest/v1/
```

- **HTTP GraphQL**: `POST http://localhost:8000/graphql`
- **WebSocket JSON-RPC**: `ws://localhost:8000/ws/gateway`
- **Supabase Studio**: `http://localhost:3001`

## Service matrix

| File                     | Backend image                        | Database                 | Supabase       | Redis | Chroma | Ollama |
| ------------------------ | ------------------------------------ | ------------------------ | -------------- | ----- | ------ | ------ |
| `docker-compose.yml`     | Multi-stage prod `Dockerfile`        | Supabase Postgres (`db`) | Yes (included) | Yes   | Yes    | Yes    |
| `docker-compose.dev.yml` | `Dockerfile.dev` + bind-mount `app/` | Supabase Postgres        | Yes (included) | Yes   | Yes    | Yes    |

## Troubleshooting

- **Compose “variable is not set. Defaulting to a blank string”** (many `POSTGRES_*`, `JWT_*`, Logflare, SMTP, …): **`docker/supabase/supabase.env` was missing or empty**, so Compose could not interpolate `docker-compose.supabase.yml`. Copy from `supabase.env.example` (or run `./scripts/docker-up.sh` / deploy bootstrap, which refills missing, empty, or newline-only files that contain no `KEY=value` lines), then set secrets. Do **not** commit real `supabase.env`.
- **Deploy fails validation after `printf … > supabase.env` with an unset secret**: An empty **`SUPABASE_ENV_CONTENT`** GitHub secret becomes a newline-only file (still “non-empty” to `test -s`). **`deploy/remote-deploy.sh`** refills from **`supabase.env.example`** when the file has no `KEY=value` lines; for production, set **`SUPABASE_ENV_CONTENT`** to your full `supabase.env` body.
- **`supabase-db` unhealthy / `dependency failed to start: container supabase-db`**: Usually the same blank-env issue (Postgres gets empty password/host/db name). Fix env files, then run `docker compose … down` and **`docker compose … up -d --build`** again. If the DB volume initialized badly, remove only after backup: `docker volume rm …supabase_db_data` (name from `docker volume ls`).
- **`Docker Compose is configured to build using Bake, but buildx isn't installed`**: Install **`docker-buildx-plugin`** on the host, or upgrade Docker Compose; startup scripts no longer set **`COMPOSE_BAKE=false`** (that flag is deprecated in newer Compose releases).
- **Build slow / huge context**: ensure **`ai.backend/.dockerignore`** exists (excludes `venv/`, `.git`, tests).
- **`env_file` errors**: create `ai.backend/.env` from `.env.example` and `docker/supabase/supabase.env` from `docker/supabase/supabase.env.example`.
- **`${POSTGRES_PASSWORD}` empty in compose**: set variables in **`ai.backend/.env`** (Compose interpolates from project `.env`, not only `env_file` on services).
- **chromadb** from app: use `http://chromadb:8000` inside the Compose network (not `localhost`) when the backend runs in a container.
- **GPU / Ollama**: uncomment `deploy.resources` in `docker-compose.yml` under `ollama` for NVIDIA.
- **Kong / Realtime errors**: confirm `docker/supabase/volumes/api/kong.yml` and `kong-entrypoint.sh` exist (shipped from upstream Supabase layout).

## Files in this folder

| File                            | Purpose                                                           |
| ------------------------------- | ----------------------------------------------------------------- |
| `Dockerfile`                    | Multi-stage production image, uvicorn 4 workers                   |
| `Dockerfile.dev`                | Dev image + `pip install -r requirements-dev.txt`, hot reload CMD |
| `docker-compose.yml`            | Backend + Redis + Chroma + Ollama + **includes Supabase**         |
| `docker-compose.dev.yml`        | Dev backend + Redis + Chroma + Ollama + **includes Supabase**     |
| `docker-compose.supabase.yml`   | Supabase services (included; not usually run alone)               |
| `supabase/supabase.env.example` | Secrets template for Supabase stack                               |
| `supabase/volumes/api/kong.yml` | Kong declarative config (from Supabase upstream)                  |
| `supabase/volumes/db/*.sql`     | Postgres init scripts (from Supabase upstream)                    |
