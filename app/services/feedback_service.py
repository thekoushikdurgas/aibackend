"""Video-backed user feedback (Overview + Feedback tab)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..video_storage import VideoDB
from .video_service import _resolve_video_file, list_video_tables, query_video_database

FEEDBACK_TABLE = "user_experience"


def ensure_feedback_table(db_id: str) -> None:
    """Create the feedback table if it does not exist."""
    if FEEDBACK_TABLE in list_video_tables(db_id):
        return
    q = (
        f'CREATE TABLE "{FEEDBACK_TABLE}" '
        "(session_id TEXT, message TEXT, rating INTEGER, created_at TEXT)"
    )
    result = query_video_database(db_id, q)
    if result.get("error"):
        raise ValueError(str(result["error"]))


def submit_feedback(
    db_id: str,
    session_id: str,
    message: str,
    rating: Optional[int],
) -> Dict[str, Any]:
    """Append one feedback row using CRUD (handles commas in message safely)."""
    ensure_feedback_table(db_id)
    video_file = _resolve_video_file(db_id, FEEDBACK_TABLE)
    ts = datetime.now(timezone.utc).isoformat()
    row = {
        "session_id": session_id.strip() or "anonymous",
        "message": message.strip(),
        "rating": -1 if rating is None else int(rating),
        "created_at": ts,
    }
    with VideoDB(video_file, mode="rw") as vdb:
        rid = vdb.crud.insert_row(row)
        return {"success": True, "row_id": rid}


def list_feedback(db_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Return recent feedback rows (newest first, by created_at)."""
    if FEEDBACK_TABLE not in list_video_tables(db_id):
        return []
    lim = max(1, min(int(limit), 500))
    q = (
        f'SELECT session_id, message, rating, created_at FROM "{FEEDBACK_TABLE}" '
        f"LIMIT {lim * 4}"
    )
    result = query_video_database(db_id, q)
    if result.get("error"):
        return []
    cols = result.get("columns") or []
    rows_out: List[Dict[str, Any]] = []
    for row in result.get("rows") or []:
        item = dict(zip(cols, row))
        r = item.get("rating")
        item["rating"] = None if r in (-1, "-1", "", None) else int(r)  # type: ignore[arg-type]
        rows_out.append(item)
    rows_out.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    return rows_out[:lim]
