"""
Enhanced WebSocket Connection Manager with Session State
"""

import asyncio
import logging
from typing import Dict, Optional, Any, AsyncGenerator
from fastapi import WebSocket

from app.config import settings
from app.utils.helpers import utc_now

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections with state tracking, message routing,
    and health monitoring. Compatible with JSON-RPC 2.0 architecture.
    """

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Register new WebSocket connection with session state.

        Args:
            websocket: FastAPI WebSocket instance
            connection_id: Unique connection identifier
            metadata: Initial connection metadata (user, auth info, etc.)
        """
        await websocket.accept()

        async with self.lock:
            self.active_connections[connection_id] = websocket
            self.connection_metadata[connection_id] = {
                "websocket": websocket,
                "connected_at": utc_now(),
                "last_heartbeat": utc_now(),
                "last_activity": utc_now(),
                "message_count": 0,
                "state": {},
                **(metadata or {}),
            }
            self.message_queues[connection_id] = asyncio.Queue()

        logger.info(
            f"✅ WebSocket connected: {connection_id} (Total: {len(self.active_connections)})"
        )

        # Start cleanup task if not running
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    def disconnect(self, connection_id: str) -> None:
        """
        Remove disconnected client and cleanup resources.

        Args:
            connection_id: Connection identifier to remove
        """

        async def _disconnect():
            async with self.lock:
                if connection_id in self.active_connections:
                    del self.active_connections[connection_id]
                if connection_id in self.connection_metadata:
                    del self.connection_metadata[connection_id]
                if connection_id in self.message_queues:
                    queue = self.message_queues.pop(connection_id)
                    # Clear queue
                    while not queue.empty():
                        try:
                            queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break

        # Run cleanup
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_disconnect())
            else:
                loop.run_until_complete(_disconnect())
        except Exception as e:
            logger.error(f"Error during disconnect cleanup: {e}")

        logger.info(
            f"❌ WebSocket disconnected: {connection_id} (Total: {len(self.active_connections)})"
        )

    async def send_json(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """
        Send JSON message to specific connection.

        Args:
            connection_id: Target connection ID
            message: JSON-serializable message dict

        Returns:
            True if sent successfully, False otherwise
        """
        if connection_id not in self.active_connections:
            logger.warning(f"Connection {connection_id} not found for send_json")
            return False

        websocket = self.active_connections[connection_id]

        try:
            await websocket.send_json(message)

            # Update activity tracking
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["last_activity"] = utc_now()
                self.connection_metadata[connection_id]["message_count"] += 1

            return True
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            # Mark connection as potentially dead
            self.disconnect(connection_id)
            return False

    async def send_personal(
        self, websocket: WebSocket, message: Dict[str, Any]
    ) -> bool:
        """
        Send message directly to a WebSocket instance.

        Args:
            websocket: WebSocket instance
            message: JSON-serializable message dict

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            return False

    async def broadcast(
        self, message: Dict[str, Any], exclude_connection: Optional[str] = None
    ) -> int:
        """
        Broadcast message to all connected clients.

        Args:
            message: JSON-serializable message dict
            exclude_connection: Connection ID to exclude from broadcast

        Returns:
            Number of successful sends
        """
        disconnected = []
        sent_count = 0

        async with self.lock:
            connections = list(self.active_connections.items())

        for connection_id, websocket in connections:
            if exclude_connection and connection_id == exclude_connection:
                continue

            if await self.send_personal(websocket, message):
                sent_count += 1
            else:
                disconnected.append(connection_id)

        # Clean up dead connections
        for connection_id in disconnected:
            self.disconnect(connection_id)

        return sent_count

    async def stream_to_client(
        self,
        connection_id: str,
        stream_generator: AsyncGenerator[str, None],
        message_type: str = "stream_chunk",
        format_jsonrpc: bool = True,
    ) -> None:
        """
        Stream content to specific client with JSON-RPC 2.0 compatibility.

        Args:
            connection_id: Target connection ID
            stream_generator: Async generator yielding text chunks
            message_type: Type identifier for stream messages
            format_jsonrpc: Whether to format as JSON-RPC 2.0 responses
        """
        try:
            full_content = ""
            chunk_index = 0

            async for chunk in stream_generator:
                full_content += chunk
                chunk_index += 1

                message: Dict[str, Any]
                if format_jsonrpc:
                    # Format as JSON-RPC 2.0 streaming response
                    message = {
                        "jsonrpc": "2.0",
                        "id": None,  # Notification for streaming chunks
                        "result": {
                            "type": message_type,
                            "chunk": chunk,
                            "index": chunk_index,
                            "full_content": full_content,
                            "timestamp": utc_now().isoformat(),
                        },
                    }
                else:
                    message = {
                        "type": message_type,
                        "chunk": chunk,
                        "index": chunk_index,
                        "full_content": full_content,
                        "timestamp": utc_now().isoformat(),
                    }

                await self.send_json(connection_id, message)

            # Send completion signal
            completion_message: Dict[str, Any]
            if format_jsonrpc:
                completion_message = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "result": {
                        "type": f"{message_type}_complete",
                        "full_content": full_content,
                        "total_chunks": chunk_index,
                        "timestamp": utc_now().isoformat(),
                    },
                }
            else:
                completion_message = {
                    "type": f"{message_type}_complete",
                    "full_content": full_content,
                    "total_chunks": chunk_index,
                    "timestamp": utc_now().isoformat(),
                }

            await self.send_json(connection_id, completion_message)

        except Exception as e:
            logger.error(f"Error streaming to client {connection_id}: {e}")
            error_message = (
                {
                    "jsonrpc": "2.0" if format_jsonrpc else None,
                    "id": None,
                    "error": {"code": -32000, "message": f"Streaming error: {str(e)}"},
                }
                if format_jsonrpc
                else {"type": "error", "message": str(e)}
            )
            await self.send_json(connection_id, error_message)

    async def update_client_state(
        self, connection_id: str, state: Dict[str, Any], merge: bool = True
    ) -> None:
        """
        Update client session state.

        Args:
            connection_id: Connection identifier
            state: State updates (dict)
            merge: If True, merge with existing state; if False, replace
        """
        if connection_id in self.connection_metadata:
            if merge:
                self.connection_metadata[connection_id]["state"].update(state)
            else:
                self.connection_metadata[connection_id]["state"] = state

    def get_client_state(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get client session state.

        Args:
            connection_id: Connection identifier

        Returns:
            State dict or None if connection not found
        """
        if connection_id in self.connection_metadata:
            return self.connection_metadata[connection_id]["state"].copy()
        return None

    def get_user(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get authenticated user for connection (compatibility with existing code).

        Args:
            connection_id: Connection identifier

        Returns:
            User dict or None
        """
        metadata = self.connection_metadata.get(connection_id, {})
        return metadata.get("user")

    def set_user(self, connection_id: str, user: Dict[str, Any]) -> None:
        """
        Set authenticated user for connection (compatibility with existing code).

        Args:
            connection_id: Connection identifier
            user: User information dict
        """
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["user"] = user

    async def update_heartbeat(self, connection_id: str) -> None:
        """
        Update client heartbeat timestamp.

        Args:
            connection_id: Connection identifier
        """
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["last_heartbeat"] = utc_now()
            self.connection_metadata[connection_id]["last_activity"] = utc_now()

    def get_connection_count(self) -> int:
        """
        Get total number of active connections.

        Returns:
            Number of active connections
        """
        return len(self.active_connections)

    def get_client_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        Get client information and metadata.

        Args:
            connection_id: Connection identifier

        Returns:
            Client info dict or None
        """
        if connection_id not in self.connection_metadata:
            return None

        data = self.connection_metadata[connection_id].copy()
        # Remove websocket object (not JSON serializable)
        data.pop("websocket", None)
        return data

    async def cleanup_stale_connections(
        self, timeout_seconds: Optional[int] = None
    ) -> int:
        """
        Remove stale connections based on heartbeat timeout.

        Args:
            timeout_seconds: Heartbeat timeout (uses config default if None)

        Returns:
            Number of connections removed
        """
        timeout = timeout_seconds or getattr(
            settings, "ws_heartbeat_timeout", 300  # Default 5 minutes
        )

        now = utc_now()
        stale_connections = []

        async with self.lock:
            for connection_id, metadata in self.connection_metadata.items():
                last_heartbeat = metadata.get(
                    "last_heartbeat", metadata.get("connected_at")
                )
                if last_heartbeat is None:
                    continue
                elapsed = (now - last_heartbeat).total_seconds()

                if elapsed > timeout:
                    stale_connections.append(connection_id)

        for connection_id in stale_connections:
            self.disconnect(connection_id)
            logger.warning(
                f"Removed stale connection: {connection_id} (timeout: {timeout}s)"
            )

        return len(stale_connections)

    async def _periodic_cleanup(self) -> None:
        """
        Periodic task to clean up stale connections.
        Runs every 60 seconds.
        """
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                removed = await self.cleanup_stale_connections()
                if removed > 0:
                    logger.info(f"Periodic cleanup removed {removed} stale connections")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")


# Global connection manager instance
connection_manager = ConnectionManager()
