#!/usr/bin/env bash
# Bootstrap .env and start Docker Compose from ai.backend root.
# Usage (from ai.backend):
#   ./scripts/docker-up.sh
#   ./scripts/docker-up.sh dev

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp -f .env.example .env
    echo "Created .env from .env.example — edit secrets before production."
  else
    echo "WARNING: No .env.example found; create .env manually."
  fi
fi

# Empty or newline-only supabase.env breaks Compose (CI may write SUPABASE_ENV_CONTENT as blank → file still "non-empty" for -s).
ensure_supabase_env_template() {
  local f="docker/supabase/supabase.env"
  local ex="docker/supabase/supabase.env.example"
  [[ -f "$ex" ]] || return 0
  if [[ ! -f "$f" ]] || [[ ! -s "$f" ]] || ! grep -qE '^[A-Za-z_][A-Za-z0-9_]*=.+' "$f" 2>/dev/null; then
    mkdir -p docker/supabase
    cp -f "$ex" "$f"
    echo "Created/refilled $f from supabase.env.example — edit secrets before docker compose."
  fi
}
ensure_supabase_env_template

ENV_FILES=(--env-file .env --env-file docker/supabase/supabase.env)

validate_supabase_env() {
  local f="docker/supabase/supabase.env"
  [[ -f "$f" && -s "$f" ]] || {
    echo "ERROR: $f missing or empty. Copy docker/supabase/supabase.env.example and set secrets."
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
    echo "ERROR: $f must define non-empty values for: ${missing[*]}"
    echo "Copy docker/supabase/supabase.env.example to supabase.env and fill secrets."
    echo "If the file looks empty but exists, remove it or fix it — newline-only files are refilled from the example automatically on the next run."
    exit 1
  fi
}

validate_supabase_env

if [[ "${1:-}" == "dev" ]]; then
  echo "Starting development stack (compose.dev.yaml)..."
  docker compose "${ENV_FILES[@]}" -f compose.dev.yaml up --build
else
  echo "Starting production-style stack (compose.yaml)..."
  docker compose "${ENV_FILES[@]}" -f compose.yaml up -d --build
fi
