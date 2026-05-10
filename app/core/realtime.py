"""
Supabase Realtime (async): WebSocket connection and optional postgres_changes hooks.

Uses supabase-py AsyncClient + Realtime. Enabled when ``settings.supabase_enable_realtime``
and Supabase URL/anon key are configured (including self-hosted Docker stack).
"""

from __future__ import annotations

import logging
import socket
from typing import Any, Callable, List, Optional
from urllib.parse import urlparse

from realtime.types import PostgresChangesPayload, RealtimePostgresChangesListenEvent

from app.config import settings
from app.core.supabase_client import (
    close_async_supabase_client,
    get_async_supabase_client,
    is_supabase_configured,
)

logger = logging.getLogger(__name__)

_subscribed_channels: List[Any] = []


def _supabase_realtime_host_resolves(url: str) -> bool:
    """Return True if the Supabase URL hostname resolves (avoids noisy library retries)."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        if not host:
            return False
        if parsed.port is not None:
            port = parsed.port
        elif parsed.scheme in ("https", "wss"):
            port = 443
        else:
            port = 80
        socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        return True
    except OSError as e:
        logger.debug("Supabase Realtime host resolve check failed: %s", e)
        return False


async def init_realtime() -> None:
    """Connect Realtime WebSocket; optionally register lightweight postgres_changes listeners."""
    if (
        not is_supabase_configured()
        or not settings.supabase_enable_realtime
        or not settings.supabase_url
    ):
        logger.debug("Supabase Realtime skipped (not configured or disabled)")
        return

    client = await get_async_supabase_client()
    if not client:
        return

    if not _supabase_realtime_host_resolves(settings.supabase_url):
        logger.warning(
            "Supabase Realtime skipped: hostname does not resolve (%s)",
            urlparse(settings.supabase_url).hostname or settings.supabase_url,
        )
        return

    try:
        await client.realtime.connect()
        logger.info("Supabase Realtime connected (%s)", settings.supabase_url)

        # Observability: log conversation inserts at DEBUG (tables must be in realtime publication)
        def _on_conv(payload: PostgresChangesPayload) -> None:
            logger.debug(
                "Realtime conversations change: %s", getattr(payload, "data", payload)
            )

        try:
            chan = client.channel("public-conversations")
            chan.on_postgres_changes(
                RealtimePostgresChangesListenEvent.All,
                _on_conv,
                schema="public",
                table="conversations",
            )
            await chan.subscribe()
            _subscribed_channels.append(chan)
        except Exception as e:
            logger.warning(
                "Could not subscribe to postgres_changes (check publication): %s", e
            )
    except Exception as e:
        logger.warning(f"Supabase Realtime init skipped: {e}")


async def shutdown_realtime() -> None:
    """Unsubscribe channels and close async Realtime connection."""
    global _subscribed_channels

    client = await get_async_supabase_client()
    if client:
        for ch in list(_subscribed_channels):
            try:
                await client.remove_channel(ch)
            except Exception:
                pass
        _subscribed_channels.clear()
        try:
            await client.remove_all_channels()
        except Exception:
            pass

    await close_async_supabase_client()


async def subscribe_to_table(
    event: str,
    schema: str,
    table: str,
    callback: Callable[[PostgresChangesPayload], None],
) -> Optional[Any]:
    """
    Subscribe to postgres_changes for a single table. Returns channel handle or None.

    ``event`` should be ``INSERT``, ``UPDATE``, ``DELETE``, or ``*`` (all).
    """
    if not settings.supabase_enable_realtime:
        return None
    client = await get_async_supabase_client()
    if not client:
        return None

    raw = event.strip().upper()
    ev_map = {
        "*": RealtimePostgresChangesListenEvent.All,
        "ALL": RealtimePostgresChangesListenEvent.All,
        "INSERT": RealtimePostgresChangesListenEvent.Insert,
        "UPDATE": RealtimePostgresChangesListenEvent.Update,
        "DELETE": RealtimePostgresChangesListenEvent.Delete,
    }
    ev = ev_map.get(raw, RealtimePostgresChangesListenEvent.All)

    chan = client.channel(f"{schema}-{table}-changes")
    chan.on_postgres_changes(ev, callback, schema=schema, table=table)
    await chan.subscribe()
    _subscribed_channels.append(chan)
    return chan


async def unsubscribe_all() -> None:
    """Remove channels registered here and close Realtime (same as shutdown_realtime)."""
    await shutdown_realtime()
