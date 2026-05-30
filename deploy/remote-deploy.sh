#!/usr/bin/env bash
# Remote deploy hook (GitHub Actions SSH step runs this after git reset on EC2).
# Matches scripts/docker-up.sh: Compose uses .env for variable interpolation.
#
# Environment:
#   SKIP_VALIDATE_DEPLOY=1 — skip python scripts/validate_env.py (not recommended).
#   SKIP_COMPOSE_VERSION_CHECK=1 — skip warning when Compose is older than v2.20
#     (root compose.yaml uses include:).
#   SKIP_ALEMBIC_DEPLOY=1 — skip `alembic upgrade head` in the backend container.
#   ALEMBIC_WAIT_SECONDS — seconds to wait before alembic (default 15).
#   VERIFY_SLEEP_SECONDS — passed through when verify-stack.sh runs after this script (default 30 in verify).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=deploy/docker-cli.sh
source "$(dirname "${BASH_SOURCE[0]}")/docker-cli.sh"
# shellcheck source=deploy/sanitize-dotenv.sh
source "$(dirname "${BASH_SOURCE[0]}")/sanitize-dotenv.sh"
# shellcheck source=deploy/dotenv-perms.sh
source "$(dirname "${BASH_SOURCE[0]}")/dotenv-perms.sh"

# Non-login SSH sessions often use a minimal PATH; docker may be in /usr/local/bin or /snap/bin.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin${PATH:+:$PATH}"

echo "[deploy] ROOT=$ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "[deploy] Docker not available — repo updated only."
  echo "[deploy] Start the app with: uvicorn app.main:app --host 0.0.0.0 --port 8000"
  exit 0
fi

if ! setup_docker_cli "[deploy]"; then
  exit 1
fi

if ! "${DOCKER_CMD[@]}" buildx version >/dev/null 2>&1; then
  export DOCKER_BUILDKIT=0
fi

bootstrap_env_files() {
  if [[ ! -f .env ]] && [[ -f .env.example ]]; then
    cp -f .env.example .env
    echo "[deploy] Created .env from .env.example — replace secrets for production."
  fi
}

compose_env_args() {
  local merged filtered
  merged="$(mktemp "${TMPDIR:-/tmp}/aibackend.deploy.compose.XXXXXX.env")"
  filtered="$(mktemp "${TMPDIR:-/tmp}/aibackend.deploy.filtered.XXXXXX.env")"
  sanitize_dotenv_for_compose .env "$filtered"
  grep -v -E '^(POSTGRES|REDIS|OLLAMA|CHROMA)_PUBLISH_HOST=' "$filtered" >"$merged" 2>/dev/null || cp "$filtered" "$merged"
  rm -f "$filtered"
  if [[ ! -s "$merged" ]]; then
    echo "[deploy] ERROR: .env has no valid KEY=VALUE lines for Compose (check for paste corruption like [200~)."
    exit 1
  fi
  COMPOSE_MERGED_ENV="$merged"
  COMPOSE_ENV=(--env-file "$COMPOSE_MERGED_ENV")
}

cleanup_compose_merged_env() {
  [[ -n "${COMPOSE_MERGED_ENV:-}" ]] && rm -f "$COMPOSE_MERGED_ENV"
}

trap cleanup_compose_merged_env EXIT

if ! dc version >/dev/null 2>&1; then
  echo "[deploy] ERROR: 'docker compose' is not available (Compose v2 plugin missing)."
  echo "[deploy] Install: sudo apt-get update && sudo apt-get install -y docker-compose-plugin && sudo systemctl restart docker"
  exit 1
fi

compose_min_major=2
compose_min_minor=20
_check_compose_version() {
  if [[ "${SKIP_COMPOSE_VERSION_CHECK:-}" == "1" ]]; then
    return 0
  fi
  local short major minor rest
  short="$(dc version --short 2>/dev/null || true)"
  short="${short#v}"
  if [[ -z "$short" ]]; then
    echo "[deploy] WARNING: could not read docker compose version --short; need v${compose_min_major}.${compose_min_minor}+ for compose.yaml (include:)."
    return 0
  fi
  major="${short%%.*}"
  rest="${short#*.}"
  minor="${rest%%.*}"
  if ! [[ "$major" =~ ^[0-9]+$ && "$minor" =~ ^[0-9]+$ ]]; then
    echo "[deploy] WARNING: unexpected Compose version '${short}'; need v${compose_min_major}.${compose_min_minor}+ for compose.yaml (include:)."
    return 0
  fi
  if [[ "$major" -lt $compose_min_major ]] || { [[ "$major" -eq $compose_min_major ]] && [[ "$minor" -lt $compose_min_minor ]]; }; then
    echo "[deploy] WARNING: Docker Compose is ${short}; compose.yaml uses include: (needs v${compose_min_major}.${compose_min_minor}+)."
  fi
}
_check_compose_version

bootstrap_env_files

ensure_dotenv_readable .env || exit 1

if [[ ! -f .env ]] || [[ ! -s .env ]]; then
  echo "[deploy] ERROR: .env is missing or empty. Set ENV_FILE secret or add .env on the server."
  exit 1
fi

_run_host_validate_env() {
  local py="$1"
  if [[ -z "$py" ]]; then
    return 0
  fi
  if "$py" -c "import pydantic_settings" 2>/dev/null; then
    echo "[deploy] validate_env ($py, full)"
    "$py" scripts/validate_env.py --docker 1>&2 || true
    "$py" scripts/validate_env.py --strict || return 1
    return 0
  fi
  echo "[deploy] validate_env ($py, dotenv-only — full check runs in backend container)"
  "$py" scripts/validate_env.py --dotenv-only --docker --strict || return 1
}

if [[ "${SKIP_VALIDATE_DEPLOY:-}" != "1" ]]; then
  _py=""
  if [[ -x "$ROOT/venv/bin/python" ]]; then
    _py="$ROOT/venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    _py="python3"
  elif command -v python >/dev/null 2>&1; then
    _py="python"
  fi
  if [[ -n "$_py" ]]; then
    _run_host_validate_env "$_py" || exit 1
  else
    echo "[deploy] WARNING: python not on PATH — skipping validate_env (set SKIP_VALIDATE_DEPLOY=1)."
  fi
fi

compose_env_args

COMPOSE_FILE_ARGS=()
if [[ -f compose.yaml ]]; then
  COMPOSE_FILE_ARGS=(-f compose.yaml)
elif [[ -f docker/docker-compose.yml ]]; then
  COMPOSE_FILE_ARGS=(-f docker/docker-compose.yml)
else
  echo "[deploy] ERROR: No compose.yaml or docker/docker-compose.yml found under $ROOT"
  exit 1
fi

echo "[deploy] docker compose --env-file … ${COMPOSE_FILE_ARGS[*]} up -d --build"
dc "${COMPOSE_ENV[@]}" "${COMPOSE_FILE_ARGS[@]}" pull || true
set +e
dc "${COMPOSE_ENV[@]}" "${COMPOSE_FILE_ARGS[@]}" up -d --build
up_rc=$?
set -e
if [[ "$up_rc" -ne 0 ]]; then
  exit "$up_rc"
fi

if [[ "${SKIP_ALEMBIC_DEPLOY:-}" != "1" ]]; then
  echo "[deploy] waiting for backend before alembic upgrade head..."
  sleep "${ALEMBIC_WAIT_SECONDS:-15}"
  set +e
  dc "${COMPOSE_ENV[@]}" "${COMPOSE_FILE_ARGS[@]}" exec -T backend alembic upgrade head
  alembic_rc=$?
  set -e
  if [[ "$alembic_rc" -ne 0 ]]; then
    echo "[deploy] WARNING: alembic upgrade head exited $alembic_rc (set SKIP_ALEMBIC_DEPLOY=1 to skip)."
  fi
fi

if [[ "${SKIP_VALIDATE_DEPLOY:-}" != "1" ]]; then
  echo "[deploy] validate_env inside backend container"
  set +e
  dc "${COMPOSE_ENV[@]}" "${COMPOSE_FILE_ARGS[@]}" exec -T backend \
    python scripts/validate_env.py --strict
  container_validate_rc=$?
  set -e
  if [[ "$container_validate_rc" -ne 0 ]]; then
    echo "[deploy] WARNING: container validate_env exited $container_validate_rc (check .env / ENV_FILE secret)."
  fi
fi

exit 0
