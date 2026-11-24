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

# Prefer production entry (EC2 Docker — not Lambda); fall back to compose.yaml / docker/.
COMPOSE_FILE_ARGS=()
if [[ -f compose.prod.yaml ]]; then
  COMPOSE_FILE_ARGS=(-f compose.prod.yaml)
elif [[ -f compose.yaml ]]; then
  COMPOSE_FILE_ARGS=(-f compose.yaml)
elif [[ -f docker/docker-compose.yml ]]; then
  COMPOSE_FILE_ARGS=(-f docker/docker-compose.yml)
else
  echo "[deploy] ERROR: No compose.prod.yaml, compose.yaml, or docker/docker-compose.yml under $ROOT"
  exit 1
fi

compose_dc() {
  dc "${COMPOSE_ENV[@]}" "${COMPOSE_FILE_ARGS[@]}" "$@"
}
# shellcheck source=deploy/compose-diagnostics.sh
source "$(dirname "${BASH_SOURCE[0]}")/compose-diagnostics.sh"

# minio is optional (compose.prod.yaml profile); Docker Hub often denies pulls.
DEPLOY_DEPS=(db redis chromadb kafka ollama)

_wait_dep_healthy() {
  local svc="$1"
  local max_sec="${2:-180}"
  local elapsed=0
  # chromadb / ollama may lack a healthcheck — "running" is enough.
  while [[ "$elapsed" -lt "$max_sec" ]]; do
    if compose_dc ps "$svc" 2>/dev/null | grep -qiE '\(healthy\)'; then
      echo "[deploy] dependency $svc is healthy"
      return 0
    fi
    if compose_dc ps "$svc" 2>/dev/null | grep -qiE 'Up '; then
      if [[ "$svc" == "chromadb" || "$svc" == "ollama" ]]; then
        echo "[deploy] dependency $svc is up (no healthcheck required)"
        return 0
      fi
    fi
    if compose_dc ps "$svc" 2>/dev/null | grep -qiE 'Restarting|Exited \(1\)|dead'; then
      echo "[deploy] ERROR: dependency $svc is crash-looping"
      compose_dc logs "$svc" --tail 50 2>&1 || true
      return 1
    fi
    sleep 5
    elapsed=$((elapsed + 5))
  done
  if compose_dc ps "$svc" 2>/dev/null | grep -qiE 'Up |healthy'; then
    echo "[deploy] WARNING: dependency $svc not healthy within ${max_sec}s but appears up — continuing"
    return 0
  fi
  echo "[deploy] ERROR: dependency $svc not ready within ${max_sec}s"
  compose_dc ps "$svc" 2>&1 || true
  compose_dc logs "$svc" --tail 50 2>&1 || true
  return 1
}

echo "[deploy] docker compose --env-file … ${COMPOSE_FILE_ARGS[*]} pull (deps)"
dc "${COMPOSE_ENV[@]}" "${COMPOSE_FILE_ARGS[@]}" pull "${DEPLOY_DEPS[@]}" || true

echo "[deploy] docker compose up -d ${DEPLOY_DEPS[*]}"
set +e
dc "${COMPOSE_ENV[@]}" "${COMPOSE_FILE_ARGS[@]}" up -d "${DEPLOY_DEPS[@]}"
deps_up_rc=$?
set -e
if [[ "$deps_up_rc" -ne 0 ]]; then
  echo "[deploy] ERROR: failed to start dependency services (exit $deps_up_rc)"
  exit "$deps_up_rc"
fi

for _dep in "${DEPLOY_DEPS[@]}"; do
  _wait_dep_healthy "$_dep" "${DEPLOY_DEP_WAIT_SECONDS:-180}" || exit 1
done

echo "[deploy] docker compose --env-file … ${COMPOSE_FILE_ARGS[*]} build backend"
dc "${COMPOSE_ENV[@]}" "${COMPOSE_FILE_ARGS[@]}" build backend

if [[ "${SKIP_VALIDATE_DEPLOY:-}" != "1" ]]; then
  echo "[deploy] validate_env --import-app (one-off before uvicorn starts)"
  dc "${COMPOSE_ENV[@]}" "${COMPOSE_FILE_ARGS[@]}" run --rm --no-deps -T backend \
    python scripts/validate_env.py --strict --import-app || {
    echo "[deploy] ERROR: validate_env --import-app failed (missing pip dep or OOM exit 137)."
    exit 1
  }
fi

echo "[deploy] docker compose up -d --force-recreate backend"
set +e
dc "${COMPOSE_ENV[@]}" "${COMPOSE_FILE_ARGS[@]}" up -d --force-recreate backend
up_rc=$?
set -e
if [[ "$up_rc" -ne 0 ]]; then
  exit "$up_rc"
fi

echo "[deploy] waiting for backend container to stay up..."
_backend_wait=0
while [[ "$_backend_wait" -lt 90 ]]; do
  if compose_backend_is_crash_looping; then
    compose_fail_if_backend_crash_looping "[deploy]" || exit 1
  fi
  if compose_backend_is_healthy || compose_backend_is_up; then
    break
  fi
  sleep 3
  _backend_wait=$((_backend_wait + 3))
done
compose_fail_if_backend_crash_looping "[deploy]" || exit 1

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
  echo "[deploy] validate_env --strict (running backend)"
  set +e
  dc "${COMPOSE_ENV[@]}" "${COMPOSE_FILE_ARGS[@]}" exec -T backend \
    python scripts/validate_env.py --strict
  container_validate_rc=$?
  set -e
  if [[ "$container_validate_rc" -ne 0 ]]; then
    echo "[deploy] WARNING: container validate_env exited $container_validate_rc."
  fi
fi

compose_fail_if_backend_crash_looping "[deploy]" || exit 1

exit 0
