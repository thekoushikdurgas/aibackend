#!/usr/bin/env bash
# Convert /home/ubuntu/aibackend into a git checkout so GitHub Actions can
# `git fetch` + `git reset --hard origin/main` during deploy.
#
# Run on the EC2 host (or via SSH):
#   bash deploy/bootstrap-git-on-ec2.sh
#
# Preserves .env. Does not stop running containers (named volumes survive).

set -euo pipefail

REPO_ROOT="${EC2_REPO_ROOT:-/home/ubuntu/aibackend}"
REPO_URL="${EC2_REPO_URL:-https://github.com/thekoushikdurgas/aibackend.git}"
BRANCH="${EC2_BRANCH:-main}"

echo "[bootstrap-git] REPO_ROOT=$REPO_ROOT"
echo "[bootstrap-git] REPO_URL=$REPO_URL branch=$BRANCH"

if [[ -d "$REPO_ROOT/.git" ]]; then
  echo "[bootstrap-git] Already a git checkout."
  cd "$REPO_ROOT"
  git remote set-url origin "$REPO_URL" || git remote add origin "$REPO_URL"
  git fetch origin "$BRANCH"
  git checkout -B "$BRANCH" "origin/$BRANCH"
  git status -sb
  exit 0
fi

mkdir -p "$(dirname "$REPO_ROOT")"
ENV_BAK=""
if [[ -f "$REPO_ROOT/.env" ]]; then
  ENV_BAK="$(mktemp /tmp/aibackend.env.XXXXXX)"
  cp -a "$REPO_ROOT/.env" "$ENV_BAK"
  echo "[bootstrap-git] Preserved .env -> $ENV_BAK"
fi

if [[ -d "$REPO_ROOT" ]]; then
  STASH="${REPO_ROOT}.pre-git.$(date +%s)"
  echo "[bootstrap-git] Moving existing tree to $STASH"
  mv "$REPO_ROOT" "$STASH"
fi

git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$REPO_ROOT"
cd "$REPO_ROOT"

if [[ -n "$ENV_BAK" && -f "$ENV_BAK" ]]; then
  cp -a "$ENV_BAK" .env
  chmod 600 .env
  rm -f "$ENV_BAK"
  echo "[bootstrap-git] Restored .env"
elif [[ -f .env.example && ! -f .env ]]; then
  cp -f .env.example .env
  chmod 600 .env
  echo "[bootstrap-git] Created .env from .env.example — edit secrets before deploy."
fi

echo "[bootstrap-git] Done. Next: bash deploy/remote-deploy.sh && bash deploy/verify-stack.sh"
git status -sb
