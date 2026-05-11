# Docker Compose (DurgasAI backend)

The stack is defined in [`docker-compose.yml`](docker-compose.yml) and included from the repo root via [`compose.yaml`](../compose.yaml).

## Services

- **db** — PostgreSQL 15 (credentials via `POSTGRES_PASSWORD` in `.env`, default `postgres`)
- **backend** — FastAPI app (port `8000`)
- **redis**, **chromadb**, **ollama** — optional dependencies

## Quick start

From `ai.backend` root:

```bash
cp .env.example .env
# Edit .env — set JWT_SECRET_KEY, API_KEY, POSTGRES_PASSWORD for Docker, etc.

./scripts/docker-up.sh          # production-style (detached)
./scripts/docker-up.sh dev      # dev compose with hot reload
```

Or manually:

```bash
docker compose --env-file .env -f compose.yaml up -d --build
```

## Notes

- Set `DATABASE_URL` / `POSTGRESQL_URL` in `.env` for local (non-Docker) runs; Compose overrides these for the backend container to point at the `db` service.
- Local file uploads use `STORAGE_ROOT` (default `./data/storage`); ensure the `backend_data` volume or bind mount includes that path.
- Socket.IO is mounted at `SOCKETIO_MOUNT_PATH` (default `/realtime`) for push events.
