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

run_compose() {
  if docker compose version >/dev/null 2>&1; then
    docker compose --env-file .env "$@"
  elif command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1; then
    if docker-compose --help 2>&1 | grep -qF -- '--env-file'; then
      docker-compose --env-file .env "$@"
    else
      echo "ERROR: docker-compose is too old (needs --env-file). Install docker-compose-plugin."
      exit 1
    fi
  else
    echo "ERROR: Docker Compose v2 is not available (need 'docker compose')."
    exit 1
  fi
}

if [[ "${1:-}" == "dev" ]]; then
  echo "Starting development stack (compose.dev.yaml)..."
  run_compose -f compose.dev.yaml up --build
else
  echo "Starting production-style stack (compose.yaml)..."
  run_compose -f compose.yaml up -d --build
fi
