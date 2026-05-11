"""
Socket.IO server (async) for application-level realtime events.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import socketio

from app.config import settings

logger = logging.getLogger(__name__)

_sio: Optional[socketio.AsyncServer] = None
_sio_asgi: Optional[socketio.ASGIApp] = None


def get_socketio_server() -> socketio.AsyncServer:
    global _sio
    if _sio is None:
        _sio = socketio.AsyncServer(
            async_mode="asgi",
            cors_allowed_origins=settings.socketio_cors_origins_list,
        )

        @_sio.event
        async def connect(sid, environ, auth):  # type: ignore[no-untyped-def]
            logger.debug("socket.io connect sid=%s", sid)

        @_sio.event
        async def disconnect(sid):  # type: ignore[no-untyped-def]
            logger.debug("socket.io disconnect sid=%s", sid)

    return _sio


def get_socketio_asgi_app() -> socketio.ASGIApp:
    global _sio_asgi
    if _sio_asgi is None:
        _sio_asgi = socketio.ASGIApp(
            get_socketio_server(),
            socketio_path="socket.io",
        )
    return _sio_asgi


def mount_socketio(app: Any) -> None:
    """Mount Socket.IO under ``settings.socketio_mount_path``."""
    path = (settings.socketio_mount_path or "/ws").rstrip("/") or "/ws"
    app.mount(path, get_socketio_asgi_app())


async def emit_event(
    event: str, data: Dict[str, Any], room: Optional[str] = None
) -> None:
    sio = get_socketio_server()
    if room:
        await sio.emit(event, data, room=room)
    else:
        await sio.emit(event, data)
