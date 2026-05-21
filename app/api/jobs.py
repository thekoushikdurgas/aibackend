"""In-process async job store for long-running work (survives per-request scope)."""

from __future__ import annotations

import time
import uuid
from typing import Any, Literal, Optional

JobStatus = Literal["pending", "running", "done", "error"]

_jobs: dict[str, dict[str, Any]] = {}


def job_create() -> str:
    jid = str(uuid.uuid4())
    _jobs[jid] = {
        "status": "pending",
        "result": None,
        "error": None,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    return jid


def job_update(
    jid: str,
    status: JobStatus,
    *,
    result: Any = None,
    error: Optional[str] = None,
) -> None:
    row = _jobs.get(jid)
    if not row:
        return
    row["status"] = status
    row["updated_at"] = time.time()
    if result is not None:
        row["result"] = result
    if error is not None:
        row["error"] = error


def job_get(jid: str) -> dict[str, Any] | None:
    return _jobs.get(jid)


def job_cleanup(max_age_seconds: float = 3600) -> None:
    now = time.time()
    dead = [
        k
        for k, v in _jobs.items()
        if now - float(v.get("created_at", 0)) > max_age_seconds
    ]
    for k in dead:
        _jobs.pop(k, None)
