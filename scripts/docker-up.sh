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

if [[ ! -f docker/supabase/supabase.env ]]; then
  if [[ -f docker/supabase/supabase.env.example ]]; then
    cp -f docker/supabase/supabase.env.example docker/supabase/supabase.env
    echo "Created docker/supabase/supabase.env from supabase.env.example — edit before docker compose."
  fi
fi

ENV_FILES=(--env-file .env --env-file docker/supabase/supabase.env)

if [[ "${1:-}" == "dev" ]]; then
  echo "Starting development stack (compose.dev.yaml)..."
  docker compose "${ENV_FILES[@]}" -f compose.dev.yaml up --build
else
  echo "Starting production-style stack (compose.yaml)..."
  docker compose "${ENV_FILES[@]}" -f compose.yaml up -d --build
fi
