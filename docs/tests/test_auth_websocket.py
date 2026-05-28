"""
Tests for Auth WebSocket Methods
"""

import time

import pytest

from app.api.ws_methods.auth import (
    handle_auth_magic_link,
    handle_auth_oauth_url,
    handle_auth_reset_password_request,
    handle_auth_signup,
    handle_auth_update_user,
    handle_auth_verify,
)
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode


@pytest.mark.asyncio
async def test_auth_signup():
    """Test auth.signup method"""
    test_email = f"test_{int(time.time())}@example.com"
    test_password = "test_password_123"

    response = await handle_auth_signup(
        params={
            "email": test_email,
            "password": test_password,
            "metadata": {"test": True},
        },
        user=None,
    )

    assert response.get("success") is True
    assert response.get("user") is not None


@pytest.mark.asyncio
async def test_auth_verify():
    """Test auth.verify method"""
    response = await handle_auth_verify(
        params={},
        user=None,
    )

    assert "valid" in response


@pytest.mark.asyncio
async def test_auth_reset_password_request():
    """Test auth.reset_password_request method"""
    response = await handle_auth_reset_password_request(
        params={
            "email": "test@example.com",
        },
        user=None,
    )

    assert response.get("success") is True


@pytest.mark.asyncio
async def test_auth_magic_link():
    """Test auth.magic_link method"""
    response = await handle_auth_magic_link(
        params={
            "email": "test@example.com",
        },
        user=None,
    )

    assert response.get("success") is True


@pytest.mark.asyncio
async def test_auth_oauth_url_not_configured():
    """OAuth URL is not available without external IdP."""
    with pytest.raises(JSONRPCError) as exc_info:
        await handle_auth_oauth_url(
            params={
                "provider": "google",
            },
            user=None,
        )

    assert exc_info.value.code == JSONRPCErrorCode.INTERNAL_ERROR


@pytest.mark.asyncio
async def test_auth_update_user_requires_auth():
    """Test that auth.update_user requires authentication"""
    with pytest.raises(JSONRPCError) as exc_info:
        await handle_auth_update_user(
            params={
                "metadata": {"test": "value"},
            },
            user=None,
        )

    assert exc_info.value.code == JSONRPCErrorCode.AUTHENTICATION_ERROR
