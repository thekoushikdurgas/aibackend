"""JSON-RPC streaming: system.notifications — server-push notification feed.

This handler subscribes the connected client to real-time OS-level push
notifications. The backend streams structured notification payloads whenever
significant events occur (job done, service degraded, RAG indexing complete,
workflow finished, etc.).

The client keeps this stream alive for the lifetime of the session.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, AsyncGenerator, Dict, Optional, Set

logger = logging.getLogger(__name__)

# Interval between keepalive heartbeat frames (seconds)
_HEARTBEAT_INTERVAL = 30

# Max session lifetime before client must reconnect (seconds) — prevents zombie sockets
_MAX_SESSION_SECONDS = 3600


_subscribers: Set[asyncio.Queue] = set()


async def handle_system_notifications(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream OS-level push notifications to the connected client.

    Each yielded frame is a structured notification dict:
      {
        "type":  "notification" | "heartbeat" | "done",
        "notification": {
          "id":        str,          # unique event id
          "title":     str,          # notification title
          "body":      str | None,   # optional detail message
          "level":     "info" | "success" | "warning" | "error",
          "source":    str,          # originating backend service
          "timestamp": int,          # unix ms
        }
      }
    """
    owner_id = (user or {}).get("sub") or "anonymous"
    session_start = time.time()

    logger.info(
        "system.notifications session started owner=%s conn=%s",
        owner_id,
        connection_id,
    )

    # Register client-specific queue
    queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
    _subscribers.add(queue)

    # ── Welcome notification ────────────────────────────────────────────────
    yield _make_notif(
        title="Connected",
        body="Real-time OS push notifications are now active.",
        level="info",
        source="os.shell",
    )

    try:
        while True:
            # Check session TTL
            if time.time() - session_start > _MAX_SESSION_SECONDS:
                yield {
                    "type": "done",
                    "reason": "session_ttl",
                }
                return

            try:
                # Wait for next notification or heartbeat timeout
                item = await asyncio.wait_for(queue.get(), timeout=_HEARTBEAT_INTERVAL)
                yield item
            except asyncio.TimeoutError:
                # Heartbeat keeps the WS alive through proxies
                elapsed = int(time.time() - session_start)
                yield {
                    "type": "heartbeat",
                    "ts": int(time.time() * 1000),
                    "uptime_s": elapsed,
                }

    except asyncio.CancelledError:
        logger.info(
            "system.notifications cancelled owner=%s conn=%s",
            owner_id,
            connection_id,
        )
        raise
    finally:
        _subscribers.remove(queue)


def push_notification(
    title: str,
    body: str | None = None,
    level: str = "info",
    source: str = "backend",
) -> Dict[str, Any]:
    """Helper to build a structured push-notification frame and queue it for all active streaming clients."""
    notif = _make_notif(title=title, body=body, level=level, source=source)
    for q in list(_subscribers):
        try:
            q.put_nowait(notif)
        except Exception as e:
            logger.warning("Failed to queue notification: %s", e)
    return notif


def _make_notif(
    title: str,
    body: str | None = None,
    level: str = "info",
    source: str = "backend",
) -> Dict[str, Any]:
    import uuid

    return {
        "type": "notification",
        "notification": {
            "id": str(uuid.uuid4()),
            "title": title,
            "body": body,
            "level": level,
            "source": source,
            "timestamp": int(time.time() * 1000),
        },
    }


def get_methods() -> Dict[str, Any]:
    """Return all methods from this module"""
    return {
        "system.notifications": handle_system_notifications,
    }
