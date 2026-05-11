#!/usr/bin/env bash
# Bootstrap .env and start Docker Compose from ai.backend root.
# Usage (from ai.backend):
#   ./scripts/docker-up.sh
#   ./scripts/docker-up.sh dev

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found on PATH. Install Docker Engine first."
  exit 1
fi

# Compose v2.37+ may prefer Bake; stock Ubuntu Docker often lacks the buildx CLI plugin → noisy warning.
if ! docker buildx version >/dev/null 2>&1; then
  export DOCKER_BUILDKIT=0
fi

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

# One merged env file for Compose interpolation (same semantics as two --env-files: later lines win).
merge_compose_env_files() {
  local out
  out="$(mktemp "${TMPDIR:-/tmp}/aibackend.compose.XXXXXX.env")"
  cat .env docker/supabase/supabase.env >"$out"
  chmod 600 "$out" 2>/dev/null || true
  echo "$out"
}

run_compose() {
  local merged merged_rm
  merged="$(merge_compose_env_files)"
  merged_rm() { rm -f "$merged"; }
  trap merged_rm EXIT

  if docker compose version >/dev/null 2>&1; then
    docker compose --env-file "$merged" "$@"
    return
  fi
  if command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
    if docker-compose --help 2>&1 | grep -qF -- '--env-file'; then
      docker-compose --env-file "$merged" "$@"
      return
    fi
  fi
  echo "ERROR: Docker Compose v2 is not available for this user (need 'docker compose')."
  echo "Install the plugin, then verify with: docker compose version"
  echo "  sudo apt-get update && sudo apt-get install -y docker-compose-plugin"
  echo "  sudo systemctl restart docker"
  echo "If you use sudo, the plugin must be installed system-wide (apt package above), not only under ~/.docker/cli-plugins."
  exit 1
}

if [[ "${1:-}" == "dev" ]]; then
  echo "Starting development stack (compose.dev.yaml)..."
  run_compose -f compose.dev.yaml up --build
else
  echo "Starting production-style stack (compose.yaml)..."
  run_compose -f compose.yaml up -d --build
fi
