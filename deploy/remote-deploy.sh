#!/usr/bin/env bash
# Remote deploy hook (GitHub Actions SSH step runs this after git reset on EC2).
# Customize for systemd, Docker, or manual uvicorn.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[deploy] ROOT=$ROOT"

if command -v docker >/dev/null 2>&1; then
  if [ -f docker/docker-compose.yml ]; then
    echo "[deploy] docker compose -f docker/docker-compose.yml up"
    docker compose -f docker/docker-compose.yml pull || true
    docker compose -f docker/docker-compose.yml up -d --build
    exit 0
  fi
  if [ -f compose.yaml ]; then
    echo "[deploy] docker compose (compose.yaml)"
    docker compose pull || true
    docker compose up -d --build
    exit 0
  fi
fi

echo "[deploy] Docker Compose not available or no compose file — repo is updated only."
echo "[deploy] Start the app with: uvicorn app.main:app --host 0.0.0.0 --port 8000"
exit 0
