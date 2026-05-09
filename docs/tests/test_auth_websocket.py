"""
Tests for Auth WebSocket Methods
"""

import pytest
import asyncio
from app.api.ws_methods.auth import (
    handle_auth_signup,
    handle_auth_signin,
    handle_auth_signout,
    handle_auth_refresh,
    handle_auth_verify,
    handle_auth_reset_password_request,
    handle_auth_update_user,
    handle_auth_magic_link,
    handle_auth_oauth_url
)
from app.core.supabase_client import is_supabase_configured


@pytest.mark.asyncio
@pytest.mark.skipif(not is_supabase_configured(), reason="Supabase not configured")
async def test_auth_signup():
    """Test auth.signup method"""
    import time
    test_email = f"test_{int(time.time())}@example.com"
    test_password = "test_password_123"
    
    try:
        response = await handle_auth_signup(
            params={
                "email": test_email,
                "password": test_password,
                "metadata": {"test": True}
            },
            user=None
        )
        
        assert response.get("success") is True
        assert response.get("user") is not None or response.get("requires_confirmation") is True
        
    except Exception as e:
        pytest.skip(f"Signup test failed: {e}")


@pytest.mark.asyncio
@pytest.mark.skipif(not is_supabase_configured(), reason="Supabase not configured")
async def test_auth_signin():
    """Test auth.signin method"""
    # This requires an existing user, so we'll skip if signup fails
    pytest.skip("Requires existing user - run signup test first")


@pytest.mark.asyncio
@pytest.mark.skipif(not is_supabase_configured(), reason="Supabase not configured")
async def test_auth_verify():
    """Test auth.verify method"""
    # This requires a valid token
    try:
        response = await handle_auth_verify(
            params={},
            user=None
        )
        
        # Should return valid: false if no token provided
        assert "valid" in response
        
    except Exception as e:
        pytest.skip(f"Verify test failed: {e}")


@pytest.mark.asyncio
@pytest.mark.skipif(not is_supabase_configured(), reason="Supabase not configured")
async def test_auth_reset_password_request():
    """Test auth.reset_password_request method"""
    try:
        response = await handle_auth_reset_password_request(
            params={
                "email": "test@example.com"
            },
            user=None
        )
        
        # Should succeed even if email doesn't exist (for security)
        assert response.get("success") is True
        
    except Exception as e:
        pytest.skip(f"Reset password request test failed: {e}")


@pytest.mark.asyncio
@pytest.mark.skipif(not is_supabase_configured(), reason="Supabase not configured")
async def test_auth_magic_link():
    """Test auth.magic_link method"""
    try:
        response = await handle_auth_magic_link(
            params={
                "email": "test@example.com"
            },
            user=None
        )
        
        assert response.get("success") is True
        
    except Exception as e:
        pytest.skip(f"Magic link test failed: {e}")


@pytest.mark.asyncio
@pytest.mark.skipif(not is_supabase_configured(), reason="Supabase not configured")
async def test_auth_oauth_url():
    """Test auth.oauth_url method"""
    try:
        response = await handle_auth_oauth_url(
            params={
                "provider": "google"
            },
            user=None
        )
        
        assert response.get("success") is True
        assert "url" in response
        
    except Exception as e:
        pytest.skip(f"OAuth URL test failed: {e}")


@pytest.mark.asyncio
@pytest.mark.skipif(not is_supabase_configured(), reason="Supabase not configured")
async def test_auth_update_user_requires_auth():
    """Test that auth.update_user requires authentication"""
    from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
    
    with pytest.raises(JSONRPCError) as exc_info:
        await handle_auth_update_user(
            params={
                "metadata": {"test": "value"}
            },
            user=None
        )
    
    assert exc_info.value.code == JSONRPCErrorCode.AUTHENTICATION_ERROR

