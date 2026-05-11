#!/usr/bin/env bash
# Remote deploy hook (GitHub Actions SSH step runs this after git reset on EC2).
# Matches scripts/docker-up.sh: Compose uses `.env` for variable interpolation.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Non-login SSH sessions often use a minimal PATH; docker may be in /usr/local/bin or /snap/bin.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin${PATH:+:$PATH}"

echo "[deploy] ROOT=$ROOT"

if ! docker buildx version >/dev/null 2>&1; then
  export DOCKER_BUILDKIT=0
fi

bootstrap_env_files() {
  if [[ ! -f .env ]] && [[ -f .env.example ]]; then
    cp -f .env.example .env
    echo "[deploy] Created .env from .env.example — replace secrets for production."
  fi
}

compose_env_args() {
  local merged
  merged="$(mktemp "${TMPDIR:-/tmp}/aibackend.deploy.compose.XXXXXX.env")"
  cat .env >"$merged"
  chmod 600 "$merged" 2>/dev/null || true
  COMPOSE_MERGED_ENV="$merged"
  COMPOSE_ENV=(--env-file "$COMPOSE_MERGED_ENV")
}

cleanup_compose_merged_env() {
  [[ -n "${COMPOSE_MERGED_ENV:-}" ]] && rm -f "$COMPOSE_MERGED_ENV"
}

trap cleanup_compose_merged_env EXIT

if ! command -v docker >/dev/null 2>&1; then
  echo "[deploy] Docker not available — repo updated only."
  echo "[deploy] Start the app with: uvicorn app.main:app --host 0.0.0.0 --port 8000"
  exit 0
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[deploy] ERROR: 'docker compose' is not available (Compose v2 plugin missing)."
  echo "[deploy] Install: sudo apt-get update && sudo apt-get install -y docker-compose-plugin && sudo systemctl restart docker"
  exit 1
fi

bootstrap_env_files

if [[ ! -f .env ]] || [[ ! -s .env ]]; then
  echo "[deploy] ERROR: .env is missing or empty. Set ENV_FILE secret or add .env on the server."
  exit 1
fi

compose_env_args
if [[ -f compose.yaml ]]; then
  echo "[deploy] docker compose --env-file … -f compose.yaml up -d --build"
  docker compose "${COMPOSE_ENV[@]}" -f compose.yaml pull || true
  set +e
  docker compose "${COMPOSE_ENV[@]}" -f compose.yaml up -d --build
  up_rc=$?
  set -e
  exit "$up_rc"
fi

if [[ -f docker/docker-compose.yml ]]; then
  echo "[deploy] docker compose --env-file … -f docker/docker-compose.yml up -d --build"
  docker compose "${COMPOSE_ENV[@]}" -f docker/docker-compose.yml pull || true
  set +e
  docker compose "${COMPOSE_ENV[@]}" -f docker/docker-compose.yml up -d --build
  up_rc=$?
  set -e
  exit "$up_rc"
fi

echo "[deploy] ERROR: No compose.yaml or docker/docker-compose.yml found under $ROOT"
exit 1
