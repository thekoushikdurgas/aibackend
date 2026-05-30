#!/usr/bin/env bash
# Optional: verify API reachable from outside the EC2 host (run from laptop or CI).
#
#   PUBLIC_API_URL=http://54.146.221.133:8000 bash deploy/verify-public.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=deploy/verify-http.sh
source "$ROOT/deploy/verify-http.sh"

API_URL="${PUBLIC_API_URL:-http://54.146.221.133:8000}"
API_URL="${API_URL%/}"
VERIFY_HTTP_TIMEOUT="${VERIFY_HTTP_TIMEOUT:-30}"

echo "[verify-public] GET ${API_URL}/health"
verify_curl_ok "${API_URL}/health" "GET ${API_URL}/health"

echo "[verify-public] GraphQL systemHealth"
verify_curl_post_json "${API_URL}/graphql" '{"query":"{ systemHealth }"}' "GraphQL systemHealth"

echo "[verify-public] OK — ${API_URL} is reachable."
