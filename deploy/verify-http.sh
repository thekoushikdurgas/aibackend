# shellcheck shell=bash
# HTTP retry helpers for deploy/verify-stack.sh and deploy/verify-public.sh

verify_http_retry_env() {
  VERIFY_HTTP_RETRIES="${VERIFY_HTTP_RETRIES:-30}"
  VERIFY_HTTP_INTERVAL="${VERIFY_HTTP_INTERVAL:-5}"
  VERIFY_HTTP_TIMEOUT="${VERIFY_HTTP_TIMEOUT:-15}"
}

verify_curl_ok() {
  local url="$1"
  local label="${2:-GET $url}"
  verify_http_retry_env
  local attempt=1
  local err=""
  while [[ "$attempt" -le "$VERIFY_HTTP_RETRIES" ]]; do
    if curl -fsS --max-time "$VERIFY_HTTP_TIMEOUT" "$url" >/dev/null 2>&1; then
      return 0
    fi
    err="$(curl -fsS --max-time "$VERIFY_HTTP_TIMEOUT" "$url" 2>&1 | head -c 200 || true)"
    if [[ "$attempt" -eq "$VERIFY_HTTP_RETRIES" ]]; then
      break
    fi
    echo "[verify] ${label} not ready (${attempt}/${VERIFY_HTTP_RETRIES}), retry in ${VERIFY_HTTP_INTERVAL}s..."
    sleep "$VERIFY_HTTP_INTERVAL"
    attempt=$((attempt + 1))
  done
  echo "[verify] ERROR: ${label} failed after ${VERIFY_HTTP_RETRIES} attempts."
  [[ -n "$err" ]] && echo "[verify]   last curl: ${err}"
  return 1
}

verify_curl_post_json() {
  local url="$1"
  local data="$2"
  local label="${3:-POST $url}"
  verify_http_retry_env
  local attempt=1
  local err=""
  while [[ "$attempt" -le "$VERIFY_HTTP_RETRIES" ]]; do
    if curl -fsS --max-time "$VERIFY_HTTP_TIMEOUT" -X POST "$url" \
      -H 'Content-Type: application/json' \
      -d "$data" >/dev/null 2>&1; then
      return 0
    fi
    err="$(curl -fsS --max-time "$VERIFY_HTTP_TIMEOUT" -X POST "$url" \
      -H 'Content-Type: application/json' \
      -d "$data" 2>&1 | head -c 200 || true)"
    if [[ "$attempt" -eq "$VERIFY_HTTP_RETRIES" ]]; then
      break
    fi
    echo "[verify] ${label} not ready (${attempt}/${VERIFY_HTTP_RETRIES}), retry in ${VERIFY_HTTP_INTERVAL}s..."
    sleep "$VERIFY_HTTP_INTERVAL"
    attempt=$((attempt + 1))
  done
  echo "[verify] ERROR: ${label} failed after ${VERIFY_HTTP_RETRIES} attempts."
  [[ -n "$err" ]] && echo "[verify]   last curl: ${err}"
  return 1
}
