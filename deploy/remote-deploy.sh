#!/usr/bin/env bash
# Remote deploy hook (GitHub Actions SSH step runs this after git reset on EC2).
# Matches scripts/docker-up.sh: dual env files for Compose variable interpolation (Supabase + app).

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
  # Missing, empty, or newline-only supabase.env (e.g. empty GitHub SUPABASE_ENV_CONTENT) must not skip the template.
  local f="docker/supabase/supabase.env"
  local ex="docker/supabase/supabase.env.example"
  if [[ -f "$ex" ]] && { [[ ! -f "$f" ]] || [[ ! -s "$f" ]] || ! grep -qE '^[A-Za-z_][A-Za-z0-9_]*=.+' "$f" 2>/dev/null; }; then
    mkdir -p docker/supabase
    cp -f "$ex" "$f"
    echo "[deploy] Created/refilled docker/supabase/supabase.env from supabase.env.example (set SUPABASE_ENV_CONTENT for production overrides)."
  fi
}

compose_env_args() {
  local merged
  merged="$(mktemp "${TMPDIR:-/tmp}/aibackend.deploy.compose.XXXXXX.env")"
  cat .env docker/supabase/supabase.env >"$merged"
  chmod 600 "$merged" 2>/dev/null || true
  COMPOSE_MERGED_ENV="$merged"
  COMPOSE_ENV=(--env-file "$COMPOSE_MERGED_ENV")
}

cleanup_compose_merged_env() {
  [[ -n "${COMPOSE_MERGED_ENV:-}" ]] && rm -f "$COMPOSE_MERGED_ENV"
}

trap cleanup_compose_merged_env EXIT

validate_supabase_env() {
  local f="docker/supabase/supabase.env"
  [[ -f "$f" && -s "$f" ]] || {
    echo "[deploy] ERROR: $f missing or empty. Set SUPABASE_ENV_CONTENT secret or copy supabase.env.example on the server."
    exit 1
  }
  local req=(
    POSTGRES_PASSWORD JWT_SECRET ANON_KEY SERVICE_ROLE_KEY
    PG_META_CRYPTO_KEY LOGFLARE_PUBLIC_ACCESS_TOKEN LOGFLARE_PRIVATE_ACCESS_TOKEN
    SECRET_KEY_BASE DASHBOARD_USERNAME DASHBOARD_PASSWORD
  )
  local missing=()
  local k
  for k in "${req[@]}"; do
    if ! grep -qE "^${k}=." "$f" 2>/dev/null; then
      missing+=("$k")
    fi
  done
  if ((${#missing[@]})); then
    echo "[deploy] ERROR: $f missing non-empty keys: ${missing[*]}"
    echo "[deploy] Fix: set GitHub secret SUPABASE_ENV_CONTENT to the full supabase.env body, or edit $f on the server (see supabase.env.example)."
    exit 1
  fi
}

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
validate_supabase_env

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
