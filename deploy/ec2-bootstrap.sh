#!/usr/bin/env bash
# One-time EC2 bootstrap for ai.backend (Ubuntu).
# Run on the instance: bash deploy/ec2-bootstrap.sh
#
# Prerequisites: security group allows SSH (22). API port 8000 opened after deploy.

set -euo pipefail

REPO_ROOT="${EC2_REPO_ROOT:-/home/ubuntu/aibackend}"
REPO_URL="${EC2_REPO_URL:-https://github.com/thekoushikdurgas/aibackend.git}"

echo "[bootstrap] Installing packages..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl git python3

if ! command -v docker >/dev/null 2>&1; then
  echo "[bootstrap] Installing Docker Engine..."
  curl -fsSL https://get.docker.com | sudo sh
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[bootstrap] Installing docker-compose-plugin..."
  sudo apt-get install -y docker-compose-plugin
fi

COMPOSE_VER="$(docker compose version --short 2>/dev/null || true)"
echo "[bootstrap] docker compose version: ${COMPOSE_VER:-unknown} (need >= 2.20 for compose.yaml include:)"

if id ubuntu >/dev/null 2>&1; then
  sudo usermod -aG docker ubuntu || true
  echo "[bootstrap] Added ubuntu to docker group (log out/in if docker permission denied)."
fi

if [[ ! -d "$REPO_ROOT/.git" ]]; then
  echo "[bootstrap] Cloning $REPO_URL -> $REPO_ROOT"
  sudo mkdir -p "$(dirname "$REPO_ROOT")"
  if [[ ! -d "$REPO_ROOT" ]]; then
    git clone "$REPO_URL" "$REPO_ROOT"
  fi
else
  echo "[bootstrap] Repo already exists at $REPO_ROOT"
fi

cd "$REPO_ROOT"
if [[ ! -f .env ]] && [[ -f .env.example ]]; then
  cp -f .env.example .env
  echo "[bootstrap] Created .env from .env.example — edit secrets before production deploy."
fi

echo "[bootstrap] Done."
echo "  1. Edit $REPO_ROOT/.env (JWT_SECRET_KEY, API_KEY, POSTGRES_PASSWORD, CORS_ORIGINS, …)"
echo "  2. Open security group TCP 8000"
echo "  3. cd $REPO_ROOT && bash deploy/remote-deploy.sh && bash deploy/verify-stack.sh"
echo "  4. curl -fsS http://127.0.0.1:8000/health"
echo "  Note: Do not pip install requirements on the host unless using Python 3.11/3.12."
echo "        Production runs in Docker (python:3.11-slim). Host python3 is only for validate_env --dotenv-only."
echo "  See deploy/EC2.md for GitHub Actions secrets."
