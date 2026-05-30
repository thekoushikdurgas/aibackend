# shellcheck shell=bash
# Ensure .env is readable by the deploy user (mode 600, owned by current user).
# Root-owned .env from "sudo nano" / "sudo chmod 600 .env" breaks validate_env and Compose.

ensure_dotenv_readable() {
  local env_file="${1:-.env}"
  if [[ ! -f "$env_file" ]]; then
    return 0
  fi
  if [[ -r "$env_file" ]]; then
    chmod 600 "$env_file" 2>/dev/null || true
    return 0
  fi
  echo "[deploy] WARNING: $env_file not readable by $(whoami) (often root-owned after sudo nano/chmod)."
  if command -v sudo >/dev/null 2>&1; then
    sudo chown "$(id -u):$(id -g)" "$env_file" 2>/dev/null \
      || sudo chown "${USER:-ubuntu}:${USER:-ubuntu}" "$env_file" 2>/dev/null \
      || true
  fi
  chmod 600 "$env_file" 2>/dev/null || true
  if [[ ! -r "$env_file" ]]; then
    echo "[deploy] ERROR: cannot read $env_file."
    echo "[deploy] Fix: sudo chown $(whoami):$(whoami) $env_file && chmod 600 $env_file"
    echo "[deploy] Do not edit .env with sudo; use: nano $env_file"
    return 1
  fi
  echo "[deploy] Fixed ownership on $env_file for $(whoami)."
  return 0
}
