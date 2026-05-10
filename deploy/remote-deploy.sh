#!/usr/bin/env bash
# Remote deploy hook (GitHub Actions SSH step runs this after git reset on EC2).
# Matches scripts/docker-up.sh: dual env files for Compose variable interpolation (Supabase + app).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Non-login SSH sessions often use a minimal PATH; docker may be in /usr/local/bin or /snap/bin.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin${PATH:+:$PATH}"

echo "[deploy] ROOT=$ROOT"

bootstrap_env_files() {
  if [[ ! -f .env ]] && [[ -f .env.example ]]; then
    cp -f .env.example .env
    echo "[deploy] Created .env from .env.example — replace secrets for production."
  fi
  # Empty file still breaks interpolation; refill from example when missing or zero-length
  if [[ (! -f docker/supabase/supabase.env) || (! -s docker/supabase/supabase.env) ]] && [[ -f docker/supabase/supabase.env.example ]]; then
    mkdir -p docker/supabase
    cp -f docker/supabase/supabase.env.example docker/supabase/supabase.env
    echo "[deploy] Created docker/supabase/supabase.env from supabase.env.example."
  fi
}

compose_env_args() {
  COMPOSE_ENV=(--env-file .env)
  if [[ -f docker/supabase/supabase.env ]] && [[ -s docker/supabase/supabase.env ]]; then
    COMPOSE_ENV+=(--env-file docker/supabase/supabase.env)
  else
    echo "[deploy] WARNING: docker/supabase/supabase.env missing or empty — Supabase/Kong compose vars may fail."
  fi
  # Compose v2.37+ Bake requires buildx; avoid noisy warning on minimal Docker installs.
  export COMPOSE_BAKE="${COMPOSE_BAKE:-false}"
}

if ! command -v docker >/dev/null 2>&1; then
  echo "[deploy] Docker not available — repo updated only."
  echo "[deploy] Start the app with: uvicorn app.main:app --host 0.0.0.0 --port 8000"
  exit 0
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
  docker compose "${COMPOSE_ENV[@]}" -f compose.yaml up -d --build
  exit 0
fi

if [[ -f docker/docker-compose.yml ]]; then
  echo "[deploy] docker compose --env-file … -f docker/docker-compose.yml up -d --build"
  docker compose "${COMPOSE_ENV[@]}" -f docker/docker-compose.yml pull || true
  docker compose "${COMPOSE_ENV[@]}" -f docker/docker-compose.yml up -d --build
  exit 0
fi

echo "[deploy] ERROR: No compose.yaml or docker/docker-compose.yml found under $ROOT"
exit 1
