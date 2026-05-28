"""
WebSocket Authentication and Authorization
"""

import logging
from typing import Optional, Dict, Any

from app.core.auth import verify_token, verify_api_key
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


async def authenticate_message(
    auth_data: Optional[Dict[str, Any]],
    connection_user: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Authenticate a WebSocket message

    Supports two strategies:
    1. Connection-level auth: Use user from connection metadata
    2. Per-message auth: Verify auth data in message

    Args:
        auth_data: Authentication data from message (optional)
        connection_user: User from connection metadata (optional)

    Returns:
        Authenticated user dictionary or None if no auth required

    Raises:
        JSONRPCError: If authentication fails
    """
    # Strategy 1: Use connection-level auth if available
    if connection_user:
        return connection_user

    # Strategy 2: Per-message auth
    if auth_data:
        auth_type = auth_data.get("type", "jwt")

        if auth_type == "jwt":
            token = auth_data.get("token")
            if not token:
                raise JSONRPCError(
                    JSONRPCErrorCode.AUTHENTICATION_ERROR,
                    "Missing JWT token in auth data",
                )

            try:
                # verify_token raises HTTPException, we need to catch it
                from fastapi import HTTPException

                try:
                    user = verify_token(token)
                    return user
                except HTTPException as e:
                    raise JSONRPCError(
                        JSONRPCErrorCode.AUTHENTICATION_ERROR,
                        f"Invalid token: {e.detail}",
                    )
            except Exception as e:
                raise JSONRPCError(
                    JSONRPCErrorCode.AUTHENTICATION_ERROR,
                    f"Token verification failed: {str(e)}",
                )

        elif auth_type == "api_key":
            api_key = auth_data.get("api_key")
            if not api_key:
                raise JSONRPCError(
                    JSONRPCErrorCode.AUTHENTICATION_ERROR,
                    "Missing API key in auth data",
                )

            if not verify_api_key(api_key):
                raise JSONRPCError(
                    JSONRPCErrorCode.AUTHENTICATION_ERROR, "Invalid API key"
                )

            return {"sub": "api_key_user", "type": "api_key"}

        else:
            raise JSONRPCError(
                JSONRPCErrorCode.AUTHENTICATION_ERROR,
                f"Unsupported auth type: {auth_type}",
            )

    # No authentication provided - return None (some methods may allow anonymous)
    return None


async def require_auth(
    user: Optional[Dict[str, Any]], method_name: str
) -> Dict[str, Any]:
    """
    Require authentication for a method

    Args:
        user: Authenticated user or None
        method_name: Method name for error messages

    Returns:
        Authenticated user dictionary

    Raises:
        JSONRPCError: If user is not authenticated
    """
    if user is None:
        raise JSONRPCError(
            JSONRPCErrorCode.AUTHENTICATION_ERROR,
            f"Authentication required for method '{method_name}'",
        )

    return user


def check_permissions(
    user: Dict[str, Any], required_permission: Optional[str] = None
) -> bool:
    """
    Check if user has required permissions

    Args:
        user: Authenticated user dictionary
        required_permission: Required permission (optional)

    Returns:
        True if user has permission
    """
    if required_permission is None:
        return True

    user_permissions = user.get("permissions", []) or []
    role = user.get("role")
    user_roles = set(user.get("roles", []) or [])
    if role:
        user_roles.add(role)

    if "admin" in user_roles:
        return True

    permission_role_map = {
        "storage.buckets.create": {"admin"},
        "storage.buckets.delete": {"admin"},
        "storage.files.delete": {"admin", "editor"},
        "auth.update_user": {"admin", "user"},
        "benchmark.run": {"admin", "developer"},
    }
    required_roles = permission_role_map.get(required_permission)
    if required_roles is not None and user_roles.intersection(required_roles):
        return True

    return required_permission in user_permissions
