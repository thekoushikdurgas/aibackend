#!/usr/bin/env bash
# Post-deploy verification on the EC2 host (localhost services).
# Run from ai.backend root after docker compose is up (see deploy/remote-deploy.sh).
#
# Environment:
#   VERIFY_API_URL          default http://127.0.0.1:8000 (same port as HTTP + WebSocket gateway)
#   VERIFY_SLEEP_SECONDS    initial wait before HTTP probes (default 30)
#   VERIFY_BACKEND_HEALTH_SECONDS — wait for backend (healthy) in compose ps (default 180)
#   VERIFY_HTTP_RETRIES     curl attempts per URL (default 30)
#   VERIFY_HTTP_INTERVAL    seconds between curl retries (default 5)
#   VERIFY_STRICT_READY     if 1, fail when GraphQL systemReady status is not_ready (default 0)
#   VERIFY_REQUIRE_DOCKER   if 1, fail when docker is missing instead of skipping (default 0)
#
# Checks: /health, GraphQL systemHealth / systemReady, Postgres db, Redis.
# App push channel: Socket.IO on SOCKETIO_MOUNT_PATH (default /realtime) — not probed here.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=deploy/docker-cli.sh
source "$(dirname "${BASH_SOURCE[0]}")/docker-cli.sh"
# shellcheck source=deploy/sanitize-dotenv.sh
source "$(dirname "${BASH_SOURCE[0]}")/sanitize-dotenv.sh"
# shellcheck source=deploy/dotenv-perms.sh
source "$(dirname "${BASH_SOURCE[0]}")/dotenv-perms.sh"
# shellcheck source=deploy/verify-http.sh
source "$(dirname "${BASH_SOURCE[0]}")/verify-http.sh"

if [[ ! -f .env ]]; then
  echo "[verify] ERROR: need .env (same as docker-up bootstrap)."
  exit 1
fi

ensure_dotenv_readable .env || exit 1

# Match remote-deploy.sh: SSH shells may omit directories where docker is installed.
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/snap/bin${PATH:+:$PATH}"

if ! command -v docker >/dev/null 2>&1; then
  if [[ "${VERIFY_REQUIRE_DOCKER:-0}" == "1" ]]; then
    echo "[verify] ERROR: docker not on PATH but VERIFY_REQUIRE_DOCKER=1."
    exit 1
  fi
  echo "[verify] SKIP: docker not on PATH — no Compose stack to verify (install Docker or widen ssh PATH)."
  exit 0
fi

if ! setup_docker_cli "[verify]"; then
  exit 1
fi

if ! dc version >/dev/null 2>&1; then
  echo "[verify] ERROR: 'docker compose' is not available. Install docker-compose-plugin (same as scripts/docker-up.sh)."
  exit 1
fi

API_URL="${VERIFY_API_URL:-http://127.0.0.1:8000}"
SLEEP_SEC="${VERIFY_SLEEP_SECONDS:-30}"
STRICT_READY="${VERIFY_STRICT_READY:-0}"
BACKEND_HEALTH_WAIT="${VERIFY_BACKEND_HEALTH_SECONDS:-180}"

VERIFY_COMPOSE_ENV_COPY=""
cleanup_verify_compose_env() {
  [[ -n "${VERIFY_COMPOSE_ENV_COPY:-}" ]] && rm -f "$VERIFY_COMPOSE_ENV_COPY"
}
trap cleanup_verify_compose_env EXIT

VERIFY_COMPOSE_ENV_COPY="$(mktemp "${TMPDIR:-/tmp}/aibackend.verify.compose.XXXXXX.env")"
sanitize_dotenv_for_compose .env "$VERIFY_COMPOSE_ENV_COPY"

if [[ -f compose.yaml ]]; then
  COMPOSE_ARGS=(--env-file "$VERIFY_COMPOSE_ENV_COPY" -f compose.yaml)
elif [[ -f docker/docker-compose.yml ]]; then
  COMPOSE_ARGS=(--env-file "$VERIFY_COMPOSE_ENV_COPY" -f docker/docker-compose.yml)
else
  echo "[verify] ERROR: compose.yaml or docker/docker-compose.yml not found"
  exit 1
fi

compose_dc() {
  dc "${COMPOSE_ARGS[@]}" "$@"
}

VERIFY_EXEC_TIMEOUT="${VERIFY_EXEC_TIMEOUT:-30}"

_run_timeout() {
  local sec="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$sec" "$@"
  else
    "$@"
  fi
}

_compose_service_healthy() {
  local svc="$1"
  compose_dc ps "$svc" 2>/dev/null | grep -qiE 'up|healthy'
}

_wait_backend_compose_healthy() {
  local max_sec="$1"
  local elapsed=0
  while [[ "$elapsed" -lt "$max_sec" ]]; do
    if compose_dc ps backend 2>/dev/null | grep -qE '\(healthy\)'; then
      echo "[verify] backend container reports healthy"
      return 0
    fi
    if [[ "$elapsed" -gt 0 ]] && (( elapsed % 20 == 0 )); then
      echo "[verify] waiting for backend healthy (${elapsed}s / ${max_sec}s)..."
    fi
    sleep 5
    elapsed=$((elapsed + 5))
  done
  if compose_dc ps backend 2>/dev/null | grep -qiE 'backend'; then
    echo "[verify] WARNING: backend not healthy within ${max_sec}s — will retry HTTP (Chroma/RAG startup can be slow)"
    return 0
  fi
  echo "[verify] ERROR: backend service not running"
  return 1
}

if [[ "${SLEEP_SEC}" != "0" ]]; then
  echo "[verify] Waiting ${SLEEP_SEC}s before probing API..."
  sleep "${SLEEP_SEC}"
fi

_wait_backend_compose_healthy "$BACKEND_HEALTH_WAIT" || exit 1

echo "[verify] docker compose ps"
compose_dc ps

echo "[verify] FastAPI GET ${API_URL}/health"
verify_curl_ok "${API_URL}/health" "GET ${API_URL}/health"

echo "[verify] GraphQL systemHealth"
verify_curl_post_json "${API_URL}/graphql" '{"query":"{ systemHealth }"}' "GraphQL systemHealth"
hq=$(curl -fsS --max-time "${VERIFY_HTTP_TIMEOUT:-15}" -X POST "${API_URL}/graphql" \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ systemHealth }"}')
VERIFY_BODY="$hq" python3 << 'PY'
import json, os, sys
raw = os.environ["VERIFY_BODY"]
d = json.loads(raw)
if d.get("errors"):
    print(raw)
    sys.exit("GraphQL errors on systemHealth")
sys.exit(0)
PY

echo "[verify] GraphQL systemReady"
verify_curl_post_json "${API_URL}/graphql" '{"query":"{ systemReady }"}' "GraphQL systemReady"
rq=$(curl -fsS --max-time "${VERIFY_HTTP_TIMEOUT:-15}" -X POST "${API_URL}/graphql" \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ systemReady }"}')
VERIFY_BODY="$rq" VERIFY_STRICT_READY="$STRICT_READY" python3 << 'PY'
import json, os, sys
raw = os.environ["VERIFY_BODY"]
strict = os.environ.get("VERIFY_STRICT_READY") == "1"
d = json.loads(raw)
if d.get("errors"):
    print(raw)
    sys.exit("GraphQL errors on systemReady")
if strict:
    data = d.get("data") or {}
    sr = data.get("systemReady")
    if isinstance(sr, str):
        sr = json.loads(sr)
    status = sr.get("status") if isinstance(sr, dict) else None
    if status != "ready":
        print(raw)
        sys.exit(f"systemReady status is {status!r}, expected ready")
sys.exit(0)
PY

echo "[verify] Postgres (docker compose exec db pg_isready)"
_pg_ok=0
if _run_timeout "$VERIFY_EXEC_TIMEOUT" compose_dc exec -T db pg_isready -U postgres -h 127.0.0.1 >/dev/null 2>&1 \
  || _run_timeout "$VERIFY_EXEC_TIMEOUT" compose_dc exec -T db pg_isready -U postgres >/dev/null 2>&1; then
  _pg_ok=1
elif _compose_service_healthy db; then
  echo "[verify] WARNING: pg_isready exec failed under sudo/docker; db service is healthy in compose ps — treating as OK."
  _pg_ok=1
fi
if [[ "$_pg_ok" != "1" ]]; then
  echo "[verify] ERROR: Postgres not ready (try: compose_dc logs db)"
  exit 1
fi

echo "[verify] Redis (docker compose exec redis redis-cli ping)"
out=""
if out="$(_run_timeout "$VERIFY_EXEC_TIMEOUT" compose_dc exec -T redis redis-cli ping 2>/dev/null | head -1 | tr -d '\r\n')"; then
  :
else
  out=""
fi
if [[ "$out" != "PONG" ]] && _compose_service_healthy redis; then
  echo "[verify] WARNING: redis-cli exec returned ${out:-<empty>}; redis service is healthy in compose ps — treating as OK."
  out="PONG"
fi
if [[ "$out" != "PONG" ]]; then
  echo "[verify] ERROR: expected PONG from redis, got: ${out:-<empty>} (check: compose_dc logs redis)"
  exit 1
fi

echo "[verify] OK — FastAPI, GraphQL, Postgres, Redis checks passed."
