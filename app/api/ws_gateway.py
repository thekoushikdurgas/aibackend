"""
WebSocket Gateway - Unified JSON-RPC 2.0 Gateway for All Operations
"""

import logging
import time
from collections import defaultdict, deque
from typing import Dict, Any, Optional, Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.jsonrpc import (
    parse_request,
    create_response,
    create_error_response,
    JSONRPCError,
    JSONRPCErrorCode,
    is_notification,
    is_streaming_result,
)
from app.core.ws_auth import authenticate_message
from app.core.connection_manager import connection_manager
from app.utils.helpers import generate_id, utc_now
from app.api.ws_methods.registry import WS_METHOD_MODULES
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


class WebSocketGateway:
    """Main WebSocket gateway with JSON-RPC 2.0 routing"""

    def __init__(self) -> None:
        self.methods: Dict[str, Callable] = {}
        self._rate_windows: Dict[str, deque] = defaultdict(deque)
        self.register_all_methods()

    def register_method(self, method_name: str, handler: Callable):
        """Register a method handler"""
        self.methods[method_name] = handler
        logger.debug(f"Registered method: {method_name}")

    def register_all_methods(self):
        """Auto-discover and register all method handlers"""
        for module_name in WS_METHOD_MODULES:
            try:
                module = __import__(
                    f"app.api.ws_methods.{module_name}", fromlist=[module_name]
                )
                if hasattr(module, "get_methods"):
                    methods = module.get_methods()
                    for method_name, handler in methods.items():
                        self.register_method(method_name, handler)
            except ImportError as e:
                logger.warning(f"Method module '{module_name}' not available: {e}")
            except Exception as e:
                logger.error(f"Error loading method module '{module_name}': {e}")

        logger.info(f"Registered {len(self.methods)} methods")

    async def handle_message(
        self, websocket: WebSocket, connection_id: str, message_data: str
    ):
        """Handle incoming JSON-RPC message"""
        try:
            # Parse request
            request = parse_request(message_data)
            method_name = request.get("method")
            request_id = request.get("id")
            params = request.get("params", {})
            auth_data = request.get("auth")

            # Get connection user
            connection_user = connection_manager.get_user(connection_id)

            # Authenticate
            user = await authenticate_message(auth_data, connection_user)

            # Handle special auth.connect method
            if method_name == "auth.connect":
                if user:
                    connection_manager.set_user(connection_id, user)
                    await connection_manager.update_heartbeat(connection_id)
                    await self._send_response(
                        websocket,
                        request_id,
                        {"status": "authenticated", "user": user.get("sub")},
                    )
                else:
                    await self._send_error(
                        websocket,
                        request_id,
                        JSONRPCErrorCode.AUTHENTICATION_ERROR,
                        "Authentication failed",
                    )
                return

            # Check if method exists
            if method_name not in self.methods:
                await self._send_error(
                    websocket,
                    request_id,
                    JSONRPCErrorCode.METHOD_NOT_FOUND,
                    f"Method '{method_name}' not found",
                )
                return

            # Get handler
            handler = self.methods[method_name]

            # Per-connection/per-user rate limiting for WebSocket traffic.
            rate_key = connection_id
            if user and user.get("sub"):
                rate_key = f"user:{user['sub']}"
            limit = settings.rate_limit_per_minute_anonymous
            if user:
                if user.get("type") == "api_key":
                    limit = settings.rate_limit_per_minute_api_key
                else:
                    limit = settings.rate_limit_per_minute_authenticated
            if not self._allow_request(rate_key, limit=limit):
                await self._send_error(
                    websocket,
                    request_id,
                    JSONRPCErrorCode.RATE_LIMIT_ERROR,
                    "Rate limit exceeded",
                )
                return

            # Execute handler
            try:
                result = await handler(params, user=user, connection_id=connection_id)
                await connection_manager.update_heartbeat(connection_id)

                # Handle streaming vs non-streaming
                if is_streaming_result(result):
                    # Stream multiple responses
                    async for chunk in result:
                        await self._send_response(websocket, request_id, chunk)
                else:
                    # Single response
                    await self._send_response(websocket, request_id, result)

            except JSONRPCError as e:
                await self._send_error(websocket, request_id, e.code, e.message, e.data)
            except Exception as e:
                logger.error(f"Handler error for {method_name}: {e}", exc_info=True)
                await self._send_error(
                    websocket,
                    request_id,
                    JSONRPCErrorCode.INTERNAL_ERROR,
                    f"Internal error: {str(e)}",
                )

        except JSONRPCError as e:
            # Parse/validation error - no request_id available
            await websocket.send_json(
                create_error_response(None, e.code, e.message, e.data)
            )
        except Exception as e:
            logger.error(f"Message handling error: {e}", exc_info=True)
            await websocket.send_json(
                create_error_response(
                    None, JSONRPCErrorCode.INTERNAL_ERROR, f"Internal error: {str(e)}"
                )
            )

    async def _send_response(
        self, websocket: WebSocket, request_id: Optional[Any], result: Any
    ):
        """Send JSON-RPC response"""
        if not is_notification({"id": request_id}):
            response = create_response(request_id, result)
            await websocket.send_json(response)

    async def _send_error(
        self,
        websocket: WebSocket,
        request_id: Optional[Any],
        code: int,
        message: str,
        data: Optional[Any] = None,
    ):
        """Send JSON-RPC error"""
        if not is_notification({"id": request_id}):
            response = create_error_response(request_id, code, message, data)
            await websocket.send_json(response)

    def _allow_request(self, key: str, *, limit: int) -> bool:
        now = time.time()
        one_minute_ago = now - 60
        window = self._rate_windows[key]
        while window and window[0] < one_minute_ago:
            window.popleft()
        if len(window) >= limit:
            return False
        window.append(now)
        return True


# Global gateway instance
gateway = WebSocketGateway()


@router.websocket("/ws/gateway")
async def websocket_gateway(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    api_key: Optional[str] = Query(None),
):
    """
    Main WebSocket gateway endpoint using JSON-RPC 2.0

    Connect with:
    - ws://host/ws/gateway?token=<jwt_token>
    - ws://host/ws/gateway?api_key=<api_key>

    All operations use JSON-RPC 2.0 protocol:
    {
        "jsonrpc": "2.0",
        "id": "req-123",
        "method": "chat.completions",
        "params": {...},
        "auth": {"type": "jwt", "token": "..."}
    }
    """
    # Authenticate connection if credentials provided
    user = None
    if token:
        try:
            from app.core.auth import verify_token
            from fastapi import HTTPException

            try:
                user = verify_token(token)
            except HTTPException:
                pass
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
    elif api_key:
        from app.core.auth import verify_api_key

        if verify_api_key(api_key):
            user = {"sub": "api_key_user", "type": "api_key"}

    # Generate connection ID
    connection_id = generate_id("ws")

    # Accept connection using enhanced ConnectionManager
    await connection_manager.connect(websocket, connection_id, {"user": user})

    try:
        # Send connection confirmation
        await websocket.send_json(
            {
                "jsonrpc": "2.0",
                "id": None,
                "result": {
                    "type": "connected",
                    "connection_id": connection_id,
                    "timestamp": utc_now().isoformat(),
                    "authenticated": user is not None,
                },
            }
        )

        # Handle messages
        while True:
            # Receive message
            data = await websocket.receive_text()

            # Handle ping/pong for keepalive
            if data.strip() == "ping":
                await connection_manager.update_heartbeat(connection_id)
                await websocket.send_text("pong")
                continue

            # Handle JSON-RPC messages
            await gateway.handle_message(websocket, connection_id, data)

    except WebSocketDisconnect:
        connection_manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        connection_manager.disconnect(connection_id)


# Export router
websocket_gateway_router = router
