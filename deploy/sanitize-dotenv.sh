# shellcheck shell=bash
# Filter .env for Docker Compose --env-file (KEY=VALUE only; no bracketed-paste junk).
# Usage: sanitize_dotenv_for_compose INPUT_PATH OUTPUT_PATH

sanitize_dotenv_for_compose() {
  local src="$1" dst="$2"
  : >"$dst"
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line//$'\r'/}"
    # Terminal bracketed-paste / corrupted nano line (e.g. [200~# comment)
    if [[ "$line" =~ ^\[200~ ]] || [[ "$line" =~ ^\[[0-9]+~ ]]; then
      continue
    fi
    # Skip blank and comment-only lines (Compose ignores # in modern versions; safe to omit)
    local trimmed="${line#"${line%%[![:space:]]*}"}"
    trimmed="${trimmed%"${trimmed##*[![:space:]]}"}"
    [[ -z "$trimmed" ]] && continue
    [[ "$trimmed" =~ ^# ]] && continue
    # Require VAR=VALUE (Compose interpolation)
    if [[ "$trimmed" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; then
      printf '%s\n' "$trimmed" >>"$dst"
    fi
  done <"$src"
  chmod 600 "$dst" 2>/dev/null || true
}
