#!/usr/bin/env bash
# Optional: verify API reachable from outside the EC2 host (run from laptop or CI).
#
#   PUBLIC_API_URL=http://54.146.221.133:8000 bash deploy/verify-public.sh

set -euo pipefail

API_URL="${PUBLIC_API_URL:-http://54.146.221.133:8000}"
API_URL="${API_URL%/}"

echo "[verify-public] GET ${API_URL}/health"
curl -fsS --max-time 30 "${API_URL}/health" >/dev/null

echo "[verify-public] GraphQL systemHealth"
curl -fsS --max-time 30 -X POST "${API_URL}/graphql" \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ systemHealth }"}' >/dev/null

echo "[verify-public] OK — ${API_URL} is reachable."
