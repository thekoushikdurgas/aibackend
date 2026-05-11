#!/usr/bin/env bash
# Debug-only: append NDJSON lines for Kong / Compose investigation (session 40dd89).
# Writes to ai.backend/debug-40dd89.log — no secrets in log lines (redacted).

set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${AGENT_DEBUG_LOG:-$ROOT/debug-40dd89.log}"
COMPOSE_RC="${1:-}"
RUN_ID="${AGENT_RUN_ID:-pre-fix}"

#region agent log
_append() {
  python3 - "$LOG_FILE" <<'PY' || true
import json, os, subprocess, sys, time, re

log_path = sys.argv[1]

def redact(s: str) -> str:
    if not s:
        return s
    s = re.sub(r"eyJ[A-Za-z0-9_=-]+\.[A-Za-z0-9_=-]+\.[A-Za-z0-9_=-]+", "<jwt>", s)
    s = re.sub(r"(?i)(password|secret|token|apikey|authorization)\s*[:=]\s*\S+", r"\1=<redacted>", s)
    return s[:12000]

def sh(args):
    try:
        out = subprocess.check_output(args, text=True, stderr=subprocess.STDOUT, timeout=60)
        return redact(out)
    except Exception as e:
        return redact(str(e))

def line(hypothesis_id: str, message: str, data: dict):
    rec = {
        "sessionId": "40dd89",
        "runId": os.environ.get("AGENT_RUN_ID", "pre-fix"),
        "hypothesisId": hypothesis_id,
        "location": "scripts/agent-kong-debug.sh",
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

compose_rc = os.environ.get("AGENT_COMPOSE_RC", "")
line("H0", "agent_kong_debug_invoked", {"composeExitCode": compose_rc, "logFile": log_path})

# H3: container state / health structure (no env in State)
ins = sh(["docker", "inspect", "supabase-kong", "--format", "{{json .State}}"])
line("H3", "docker_inspect_State", {"stateJson": ins[:8000]})

# H2: kong health CLI inside container
kh = sh(["docker", "exec", "supabase-kong", "kong", "health"])
line("H2", "docker_exec_kong_health", {"output": kh[:4000]})

# H1: recent logs (redacted) — config parse / nginx errors
logs = sh(["docker", "logs", "--tail", "80", "supabase-kong"])
line("H1", "docker_logs_tail", {"logs": logs[:8000]})

# H4: proxy port inside container (ss or kong config subset)
ss_out = sh(["docker", "exec", "supabase-kong", "sh", "-c", "ss -lntp 2>/dev/null || netstat -lntp 2>/dev/null || true"])
line("H4", "listening_ports_in_container", {"ss": ss_out[:4000]})

# H5: generated declarative file size + first line only (no secrets)
sz = sh(
    [
        "docker",
        "exec",
        "supabase-kong",
        "sh",
        "-c",
        "wc -c /usr/local/kong/kong.yml 2>/dev/null; grep -E '^_format_version|^_transform' /usr/local/kong/kong.yml 2>/dev/null | head -n 5",
    ]
)
line("H5", "kong_yml_head_and_size", {"snippet": sz[:2000]})
PY
}
#endregion

export AGENT_COMPOSE_RC="${COMPOSE_RC}"
export AGENT_RUN_ID="${RUN_ID}"
_append

unset AGENT_COMPOSE_RC
