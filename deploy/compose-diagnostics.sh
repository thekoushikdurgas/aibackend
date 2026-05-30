# shellcheck shell=bash
# Shared Docker Compose diagnostics for deploy/verify scripts.

compose_backend_status_line() {
  compose_dc ps backend 2>/dev/null | tail -n +2 | head -1
}

compose_backend_is_crash_looping() {
  local line
  line="$(compose_backend_status_line)"
  [[ -n "$line" ]] && echo "$line" | grep -qE 'Restarting|Exited \(1\)|dead'
}

compose_backend_is_up() {
  local line
  line="$(compose_backend_status_line)"
  [[ -n "$line" ]] && echo "$line" | grep -qiE 'Up '
}

compose_backend_is_healthy() {
  compose_dc ps backend 2>/dev/null | grep -qE '\(healthy\)'
}

compose_print_backend_logs() {
  local tail="${1:-80}"
  local prefix="${2:-[deploy]}"
  echo "${prefix} --- backend logs (last ${tail} lines) ---"
  compose_dc logs backend --tail "$tail" 2>&1 || true
}

compose_fail_if_backend_crash_looping() {
  local prefix="${1:-[deploy]}"
  if compose_backend_is_crash_looping; then
    echo "${prefix} ERROR: backend container is crash-looping (exit 1 / Restarting)."
    compose_backend_status_line | sed "s/^/${prefix}   /"
    compose_print_backend_logs 100 "$prefix"
    echo "${prefix} Fix hints:"
    echo "${prefix}   - git pull && bash deploy/remote-deploy.sh  (uses 1 uvicorn worker + Ollama embeddings)"
    echo "${prefix}   - Set EMBEDDING_PROVIDER=ollama in .env for small EC2 (avoid loading torch locally)"
    echo "${prefix}   - docker compose … up -d --build --force-recreate backend"
    return 1
  fi
  return 0
}
