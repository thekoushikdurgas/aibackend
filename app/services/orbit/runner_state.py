import asyncio
from typing import Any, Dict, Optional

# Map run_id -> asyncio.Queue for streaming logs/events
_run_queues: Dict[str, asyncio.Queue] = {}

# Map run_id -> asyncio.Event for pause/resume control
_pause_events: Dict[str, asyncio.Event] = {}


def get_queue(run_id: str) -> Optional[asyncio.Queue[dict[str, Any]]]:
    return _run_queues.get(run_id)


def get_pause_event(run_id: str) -> asyncio.Event:
    if run_id not in _pause_events:
        # Create an event that is set (running) by default
        event = asyncio.Event()
        event.set()
        _pause_events[run_id] = event
    return _pause_events[run_id]


def register_run(run_id: str) -> asyncio.Queue[dict[str, Any]]:
    q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    _run_queues[run_id] = q
    # Ensure pause event exists
    get_pause_event(run_id)
    return q


def unregister_run(run_id: str):
    _run_queues.pop(run_id, None)
    _pause_events.pop(run_id, None)
