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

# Empty supabase.env breaks ${POSTGRES_*}, JWT, Logflare, etc. interpolation (Compose warns + db unhealthy).
if [[ (! -f docker/supabase/supabase.env) || (! -s docker/supabase/supabase.env) ]] && [[ -f docker/supabase/supabase.env.example ]]; then
  mkdir -p docker/supabase
  cp -f docker/supabase/supabase.env.example docker/supabase/supabase.env
  echo "Created docker/supabase/supabase.env from supabase.env.example — edit secrets before docker compose."
fi

ENV_FILES=(--env-file .env --env-file docker/supabase/supabase.env)

# Compose v2.37+ may use Bake; avoid noisy warning when docker-buildx-plugin is not installed.
export COMPOSE_BAKE="${COMPOSE_BAKE:-false}"

if [[ "${1:-}" == "dev" ]]; then
  echo "Starting development stack (compose.dev.yaml)..."
  docker compose "${ENV_FILES[@]}" -f compose.dev.yaml up --build
else
  echo "Starting production-style stack (compose.yaml)..."
  docker compose "${ENV_FILES[@]}" -f compose.yaml up -d --build
fi
