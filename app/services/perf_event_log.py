"""In-process ring buffer of structured performance / ops events for the vSQL UI.

Events are capped (default 1000) and cleared on process restart. Thread-safe.
"""

from __future__ import annotations

import atexit
import threading
import time
import uuid
from collections import deque
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional

MAX_EVENTS = 1000

# Known operation names (for frontend filter dropdown)
OPERATIONS_KNOWN = (
    "video_decode",
    "video_decode_failed",
    "mkv_write",
    "csv_import",
    "csv_import_failed",
    "encode_video",
    "encode_video_failed",
    "parquet_index_build",
    "frame_preview",
    "perf_persist_failed",
)


@dataclass
class PerfEvent:
    id: str
    ts: str  # ISO UTC
    db_id: Optional[str]
    table_name: Optional[str]
    operation: str
    duration_ms: float
    bytes_in: int = 0
    bytes_out: int = 0
    rows: Optional[int] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_graphql_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


_lock = threading.Lock()
_events: deque[PerfEvent] = deque(maxlen=MAX_EVENTS)
_fp_lock = threading.Lock()
_fp_seq = 0
_last_frame_preview_bucket: Dict[tuple[str, Optional[str]], float] = {}

_pending_lock = threading.Lock()
_pending_by_db: Dict[str, List[PerfEvent]] = {}
_flush_thread_started = False
FLUSH_INTERVAL_S = 2.5
FLUSH_BATCH_MAX = 60


def pending_persist_count() -> int:
    with _pending_lock:
        return sum(len(v) for v in _pending_by_db.values())


def _queue_persist(ev: PerfEvent) -> None:
    if not ev.db_id:
        return
    if ev.operation == "perf_persist_failed":
        return
    with _pending_lock:
        _pending_by_db.setdefault(ev.db_id, []).append(ev)
    _ensure_flush_thread()


def _drain_pending_once() -> None:
    from app.services import perf_event_store as _store

    batches: Dict[str, List[PerfEvent]] = {}
    with _pending_lock:
        for db_id, lst in list(_pending_by_db.items()):
            if not lst:
                continue
            chunk = lst[:FLUSH_BATCH_MAX]
            _pending_by_db[db_id] = lst[FLUSH_BATCH_MAX:]
            batches[db_id] = chunk
    for db_id, evs in batches.items():
        try:
            _store.persist_batch(db_id, evs)
        except Exception as exc:
            with _pending_lock:
                _pending_by_db[db_id] = evs + _pending_by_db.get(db_id, [])
            append_event(
                "perf_persist_failed",
                0.0,
                db_id=db_id,
                meta={"error": str(exc)[:200], "count": len(evs)},
            )


def _flush_worker() -> None:
    while True:
        time.sleep(FLUSH_INTERVAL_S)
        _drain_pending_once()


def _ensure_flush_thread() -> None:
    global _flush_thread_started
    with _pending_lock:
        if _flush_thread_started:
            return
        _flush_thread_started = True
    threading.Thread(target=_flush_worker, name="perf_persist", daemon=True).start()


def _shutdown_flush() -> None:
    for _ in range(24):
        if pending_persist_count() == 0:
            break
        _drain_pending_once()


atexit.register(_shutdown_flush)


def db_id_from_video_path(path: Path) -> Optional[str]:
    """Extract workspace UUID from ``.../data/vsql/<uuid>/...`` if present."""
    try:
        parts = path.resolve().parts
        for i, p in enumerate(parts):
            if p == "vsql" and i + 1 < len(parts):
                return parts[i + 1]
    except (OSError, ValueError):
        pass
    return None


def append_event(
    operation: str,
    duration_ms: float,
    *,
    db_id: Optional[str] = None,
    table_name: Optional[str] = None,
    bytes_in: int = 0,
    bytes_out: int = 0,
    rows: Optional[int] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    """Append one perf event (newest retained when over cap)."""
    ev = PerfEvent(
        id=str(uuid.uuid4()),
        ts=datetime.now(timezone.utc).isoformat(),
        db_id=db_id,
        table_name=table_name,
        operation=operation,
        duration_ms=float(duration_ms),
        bytes_in=int(bytes_in),
        bytes_out=int(bytes_out),
        rows=rows,
        meta=dict(meta or {}),
    )
    with _lock:
        _events.append(ev)
    _queue_persist(ev)


@contextmanager
def timed_operation(
    operation: str,
    *,
    db_id: Optional[str] = None,
    table_name: Optional[str] = None,
    bytes_in: int = 0,
    bytes_out: int = 0,
    rows: Optional[int] = None,
    meta_factory: Optional[Callable[[], Dict[str, Any]]] = None,
) -> Iterator[Dict[str, Any]]:
    """Context manager: records duration; merge ``meta_factory()`` result on success."""
    t0 = time.perf_counter()
    err: Optional[BaseException] = None
    extra: Dict[str, Any] = {}
    try:
        yield extra
    except BaseException as e:
        err = e
        raise
    finally:
        dt = (time.perf_counter() - t0) * 1000.0
        meta: Dict[str, Any] = {}
        if meta_factory:
            try:
                meta.update(meta_factory())
            except Exception:
                pass
        meta.update(extra)
        if err is not None:
            meta["error"] = str(err)[:400]
            op = f"{operation}_failed"
        else:
            op = operation
        append_event(
            op,
            dt,
            db_id=db_id,
            table_name=table_name,
            bytes_in=bytes_in,
            bytes_out=bytes_out,
            rows=rows,
            meta=meta,
        )


def list_events(
    *,
    db_id: Optional[str] = None,
    operation: Optional[str] = None,
    limit: int = 100,
) -> List[PerfEvent]:
    """Newest-first filtered slice."""
    lim = max(1, min(int(limit), MAX_EVENTS))
    with _lock:
        items = list(_events)
    items.reverse()
    out: List[PerfEvent] = []
    for ev in items:
        if db_id and ev.db_id != db_id:
            continue
        if operation and ev.operation != operation:
            continue
        out.append(ev)
        if len(out) >= lim:
            break
    return out


def maybe_log_frame_preview(
    db_id: str,
    table_name: Optional[str],
    frame_index: int,
    duration_ms: float,
    bytes_out: int,
) -> None:
    """Rate-limit frame_preview events (scrubbing can be very chatty)."""
    key = (db_id, table_name)
    now = time.monotonic()
    with _fp_lock:
        global _fp_seq
        _fp_seq += 1
        n = _fp_seq % 10
    with _lock:
        last = _last_frame_preview_bucket.get(key, 0.0)
    # Log every 10th invocation, or if > 80ms, or if > 2s since last log for this key
    if n != 0 and duration_ms < 80.0 and (now - last) < 2.0:
        return
    with _lock:
        _last_frame_preview_bucket[key] = now
    append_event(
        "frame_preview",
        duration_ms,
        db_id=db_id,
        table_name=table_name,
        bytes_out=bytes_out,
        meta={"frame_index": int(frame_index)},
    )
