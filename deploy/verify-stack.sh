#!/usr/bin/env bash
# Post-deploy verification on the EC2 host (localhost services).
# Run from ai.backend root after docker compose is up (see deploy/remote-deploy.sh).
#
# Environment:
#   VERIFY_API_URL          default http://127.0.0.1:8000 (same port as HTTP + WebSocket gateway)
#   VERIFY_SLEEP_SECONDS    wait before checks (default 15)
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

if [[ ! -f .env ]]; then
  echo "[verify] ERROR: need .env (same as docker-up bootstrap)."
  exit 1
fi

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
SLEEP_SEC="${VERIFY_SLEEP_SECONDS:-15}"
STRICT_READY="${VERIFY_STRICT_READY:-0}"

VERIFY_COMPOSE_ENV_COPY=""
cleanup_verify_compose_env() {
  [[ -n "${VERIFY_COMPOSE_ENV_COPY:-}" ]] && rm -f "$VERIFY_COMPOSE_ENV_COPY"
}
trap cleanup_verify_compose_env EXIT

VERIFY_COMPOSE_ENV_COPY="$(mktemp "${TMPDIR:-/tmp}/aibackend.verify.compose.XXXXXX.env")"
cat .env >"$VERIFY_COMPOSE_ENV_COPY"
chmod 600 "$VERIFY_COMPOSE_ENV_COPY" 2>/dev/null || true

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

if [[ "${SLEEP_SEC}" != "0" ]]; then
  echo "[verify] Waiting ${SLEEP_SEC}s for containers to become healthy..."
  sleep "${SLEEP_SEC}"
fi

echo "[verify] docker compose ps"
compose_dc ps

echo "[verify] FastAPI GET ${API_URL}/health"
curl -fsS "${API_URL}/health" >/dev/null

echo "[verify] GraphQL systemHealth"
hq=$(curl -fsS -X POST "${API_URL}/graphql" \
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
rq=$(curl -fsS -X POST "${API_URL}/graphql" \
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
if ! compose_dc exec -T db pg_isready -U postgres >/dev/null 2>&1; then
  echo "[verify] ERROR: Postgres not ready (is service name still 'db'?)"
  exit 1
fi

echo "[verify] Redis (docker compose exec redis redis-cli ping)"
out=$(compose_dc exec -T redis redis-cli ping 2>/dev/null || true)
if [[ "$out" != "PONG" ]]; then
  echo "[verify] ERROR: expected PONG from redis, got: ${out:-<empty>}"
  exit 1
fi

echo "[verify] OK — FastAPI, GraphQL, Postgres, Redis checks passed."
