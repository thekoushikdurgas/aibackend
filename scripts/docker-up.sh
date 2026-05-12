#!/usr/bin/env bash
# Bootstrap .env and start Docker Compose from ai.backend root.
#
# Usage (from ai.backend):
#   ./scripts/docker-up.sh
#   ./scripts/docker-up.sh dev
#
# Environment:
#   SKIP_VALIDATE_ENV=1  — do not run python scripts/validate_env.py before compose.
#   SKIP_COMPOSE_VERSION_CHECK=1 — skip Compose v2.20+ warning (root compose.yaml uses include:).
#
# Requires Docker Compose v2.20+ for compose.yaml (include). See compose.yaml header.

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

compose_min_major=2
compose_min_minor=20

_check_compose_version() {
  if [[ "${SKIP_COMPOSE_VERSION_CHECK:-}" == "1" ]]; then
    return 0
  fi
  local short
  short="$(docker compose version --short 2>/dev/null || true)"
  short="${short#v}"
  if [[ -z "$short" ]]; then
    echo "WARNING: could not read 'docker compose version --short'; ensure Compose v2.20+ for compose.yaml (include:)."
    return 0
  fi
  local major minor rest
  major="${short%%.*}"
  rest="${short#*.}"
  minor="${rest%%.*}"
  if ! [[ "$major" =~ ^[0-9]+$ && "$minor" =~ ^[0-9]+$ ]]; then
    echo "WARNING: unexpected Compose version string '${short}'; ensure v${compose_min_major}.${compose_min_minor}+ for compose.yaml (include:)."
    return 0
  fi
  if [[ "$major" -lt $compose_min_major ]] || { [[ "$major" -eq $compose_min_major ]] && [[ "$minor" -lt $compose_min_minor ]]; }; then
    echo "WARNING: Docker Compose is ${short}; root compose.yaml uses 'include:' (needs v${compose_min_major}.${compose_min_minor}+)."
  fi
}

if ! docker compose version >/dev/null 2>&1; then
  echo "ERROR: 'docker compose' is not available. Install the Docker Compose v2 plugin."
  exit 1
fi

_check_compose_version

if [[ ! -f .env ]]; then
  if [[ -f .env.example ]]; then
    cp -f .env.example .env
    echo "Created .env from .env.example — edit JWT_SECRET_KEY, API_KEY, POSTGRES_PASSWORD before production."
  else
    echo "WARNING: No .env.example found; create .env manually."
  fi
fi

if [[ "${SKIP_VALIDATE_ENV:-}" != "1" ]]; then
  _py=""
  if command -v python3 >/dev/null 2>&1; then
    _py="python3"
  elif command -v python >/dev/null 2>&1; then
    _py="python"
  fi
  if [[ -n "$_py" ]]; then
    "$_py" scripts/validate_env.py --docker || true
    if ! "$_py" scripts/validate_env.py; then
      echo "ERROR: validate_env.py failed — fix .env or run with SKIP_VALIDATE_ENV=1."
      exit 1
    fi
  fi
fi

run_compose() {
  docker compose --env-file .env "$@"
}

if [[ "${1:-}" == "dev" ]]; then
  echo "Starting development stack (compose.dev.yaml)..."
  run_compose -f compose.dev.yaml up --build
else
  echo "Starting production-style stack (compose.yaml)..."
  run_compose -f compose.yaml up -d --build
fi

echo "Tip: curl -fsS http://localhost:8000/health  (API + Socket.IO path in README / docker/README.md)"
