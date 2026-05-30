"""Persist performance events to a reserved logical VideoDB table per workspace."""

from __future__ import annotations

import base64
import csv
import json
import logging
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.storage import register_table, table_video_path
from app.video_storage import VideoDB
from app.video_storage.exceptions import VideoStorageError
from app.video_storage.schema import VideoSchema
from app.services.perf_event_log import PerfEvent

logger = logging.getLogger(__name__)

# Reserved logical table (own MKV under tables/__vsql_perf/)
PERF_TABLE_NAME = "__vsql_perf"
RESERVED_PREFIX = "__vsql_"
_SENTINEL_ID = "00000000-0000-0000-0000-000000000001"
_SENTINEL_OP = "_vsql_reserved"

_stats_lock = threading.Lock()
_last_flush_ts: Dict[str, float] = {}
_last_flush_error: Dict[str, str] = {}

_table_locks: Dict[str, threading.Lock] = {}
_table_locks_guard = threading.Lock()


def _table_lock(db_id: str) -> threading.Lock:
    with _table_locks_guard:
        if db_id not in _table_locks:
            _table_locks[db_id] = threading.Lock()
        return _table_locks[db_id]


def is_reserved_table_name(name: str) -> bool:
    return bool(name and name.strip().startswith(RESERVED_PREFIX))


def _perf_bootstrap_schema() -> VideoSchema:
    """Explicit types so bootstrap rows never infer e.g. ``table_name`` as numeric."""
    s = VideoSchema()
    for name, data_type in (
        ("id", "TEXT"),
        ("ts", "TEXT"),
        ("operation", "TEXT"),
        ("duration_ms", "REAL"),
        ("bytes_in", "INTEGER"),
        ("bytes_out", "INTEGER"),
        ("rows", "TEXT"),
        ("meta_json", "TEXT"),
        ("table_name", "TEXT"),
    ):
        s.add_column(name, data_type)
    return s


def perf_persist_stats() -> Dict[str, Any]:
    """Snapshot for GraphQL (pending rows across all DBs, last flush hints)."""
    from app.services.perf_event_log import pending_persist_count

    with _stats_lock:
        last_ts = max(_last_flush_ts.values()) if _last_flush_ts else None
        errs = list(_last_flush_error.values())[-1] if _last_flush_error else None
    return {
        "pending_count": pending_persist_count(),
        "last_flush_epoch": last_ts,
        "last_error": errs,
    }


def ensure_perf_log_table(db_id: str) -> Path:
    """Create empty perf log VideoDB + catalog entry if missing."""
    vpath = table_video_path(db_id, PERF_TABLE_NAME)
    if vpath.is_file():
        register_table(db_id, PERF_TABLE_NAME)
        return vpath

    vpath.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        suffix=".csv",
        delete=False,
    ) as tf:
        w = csv.writer(tf, lineterminator="\n")
        w.writerow(
            [
                "id",
                "ts",
                "operation",
                "duration_ms",
                "bytes_in",
                "bytes_out",
                "rows",
                "meta_json",
                "table_name",
            ]
        )
        w.writerow(
            [
                _SENTINEL_ID,
                "1970-01-01T00:00:00+00:00",
                _SENTINEL_OP,
                "0",
                "0",
                "0",
                "0",
                "{}",
                "",
            ]
        )
        tmp_path = Path(tf.name)
    try:
        with VideoDB(vpath, mode="rw") as vdb:
            vdb.create_from_csv(
                tmp_path,
                schema=_perf_bootstrap_schema(),
                compression=True,
                overwrite=True,
            )
        register_table(db_id, PERF_TABLE_NAME)
    finally:
        tmp_path.unlink(missing_ok=True)
    return vpath


def _row_to_event(row: Dict[str, Any], db_id: str) -> Optional[PerfEvent]:
    if str(row.get("operation", "")) == _SENTINEL_OP:
        return None
    try:
        meta_raw = row.get("meta_json") or ""
        if isinstance(meta_raw, str) and meta_raw.startswith("{"):
            meta = json.loads(meta_raw)
        elif isinstance(meta_raw, str) and meta_raw:
            raw = base64.urlsafe_b64decode(meta_raw.encode("ascii"))
            meta = json.loads(raw.decode("utf-8"))
        else:
            meta = {}
    except (json.JSONDecodeError, TypeError, ValueError, OSError):
        meta = {}
    rows_val = row.get("rows")
    ri: Optional[int] = None
    if rows_val is not None and str(rows_val).strip() != "":
        try:
            ri = int(rows_val)
        except (TypeError, ValueError):
            ri = None
    return PerfEvent(
        id=str(row.get("id", "")),
        ts=str(row.get("ts", "")),
        db_id=db_id,
        table_name=str(row.get("table_name") or "") or None,
        operation=str(row.get("operation", "")),
        duration_ms=float(row.get("duration_ms") or 0),
        bytes_in=int(row.get("bytes_in") or 0),
        bytes_out=int(row.get("bytes_out") or 0),
        rows=ri,
        meta=meta,
    )


def load_disk_events(db_id: str, *, limit: int = 500) -> List[PerfEvent]:
    """Load persisted events newest-first (approx via full scan + sort)."""
    vpath = table_video_path(db_id, PERF_TABLE_NAME)
    if not vpath.is_file():
        return []
    out: List[PerfEvent] = []
    try:
        with _table_lock(db_id):
            with VideoDB(vpath, mode="r") as vdb:
                for row in vdb.crud.select_all():
                    ev = _row_to_event(row, db_id)
                    if ev:
                        out.append(ev)
    except (VideoStorageError, OSError, ValueError) as e:
        logger.warning("perf disk read failed: %s", e)
        return []
    out.sort(key=lambda e: e.ts, reverse=True)
    return out[: max(1, limit)]


def persist_batch(db_id: str, events: List[PerfEvent]) -> None:
    """Insert a batch of events into the perf VideoDB (one re-encode)."""
    if not events:
        return
    rows_data: List[Dict[str, Any]] = []
    for ev in events:
        meta_b64 = base64.urlsafe_b64encode(
            json.dumps(ev.meta, separators=(",", ":")).encode("utf-8")
        ).decode("ascii")
        rows_data.append(
            {
                "id": ev.id,
                "ts": ev.ts,
                "operation": ev.operation,
                "duration_ms": str(ev.duration_ms),
                "bytes_in": str(ev.bytes_in),
                "bytes_out": str(ev.bytes_out),
                "rows": "" if ev.rows is None else str(ev.rows),
                "meta_json": meta_b64,
                "table_name": ev.table_name or "",
            }
        )
    try:
        with _table_lock(db_id):
            ensure_perf_log_table(db_id)
            vpath = table_video_path(db_id, PERF_TABLE_NAME)
            with VideoDB(vpath, mode="rw") as vdb:
                vdb.crud.insert_rows(rows_data)

        with _stats_lock:
            _last_flush_ts[db_id] = time.time()
            _last_flush_error.pop(db_id, None)
    except (VideoStorageError, OSError, ValueError) as e:
        with _stats_lock:
            _last_flush_error[db_id] = str(e)[:400]
        logger.warning("perf persist batch failed for %s: %s", db_id, e)
        raise


def list_merged_events(
    db_id: str,
    operation: Optional[str],
    limit: int,
) -> List[PerfEvent]:
    """Ring buffer + on-disk perf table, newest first, deduped by id (ring wins)."""
    from app.services.perf_event_log import list_events

    lim = max(1, min(int(limit), 500))
    ring = list_events(db_id=db_id, operation=operation, limit=max(lim * 2, 100))
    disk = load_disk_events(db_id, limit=max(lim * 4, 400))
    if operation:
        disk = [e for e in disk if e.operation == operation]
    by_id: Dict[str, PerfEvent] = {}
    for e in disk:
        by_id[e.id] = e
    for e in ring:
        by_id[e.id] = e
    merged = sorted(by_id.values(), key=lambda x: x.ts, reverse=True)
    return merged[:lim]
