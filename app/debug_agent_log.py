"""Session debug NDJSON (agent). Do not log secrets."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_LOG_PATH = Path(__file__).resolve().parents[2] / "debug-e3e98b.log"
_SESSION = "e3e98b"


def agent_ndjson(
    hypothesis_id: str,
    location: str,
    message: str,
    data: dict[str, Any],
    run_id: str = "pre-fix",
) -> None:
    # #region agent log
    try:
        line = {
            "sessionId": _SESSION,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        }
        with _LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(line, default=str) + "\n")
    except Exception:
        pass
    # #endregion
