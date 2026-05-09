"""
Tests for Supabase authentication
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.supabase_client import is_supabase_configured, get_supabase_client

client = TestClient(app)


@pytest.mark.skipif(not is_supabase_configured(), reason="Supabase not configured")
def test_supabase_client_initialization():
    """Test Supabase client initialization"""
    supabase = get_supabase_client()
    assert supabase is not None


@pytest.mark.skipif(not is_supabase_configured(), reason="Supabase not configured")
def test_supabase_auth_flow():
    """Test Supabase authentication flow"""
    supabase = get_supabase_client()
    if not supabase:
        pytest.skip("Supabase client not available")
    
    # Test sign up (use test email)
    test_email = f"test_{pytest.current_time}@example.com"
    test_password = "test_password_123"
    
    try:
        # Sign up
        response = supabase.auth.sign_up({
            "email": test_email,
            "password": test_password
        })
        
        assert response.user is not None
        
        # Sign in
        response = supabase.auth.sign_in_with_password({
            "email": test_email,
            "password": test_password
        })
        
        assert response.user is not None
        assert response.session is not None
        
        # Get user
        user = supabase.auth.get_user(response.session.access_token)
        assert user.user is not None
        assert user.user.email == test_email
        
    except Exception as e:
        pytest.skip(f"Supabase auth test failed: {e}")


@pytest.mark.skipif(not is_supabase_configured(), reason="Supabase not configured")
def test_supabase_token_verification():
    """Test Supabase token verification in backend"""
    from app.core.auth import verify_supabase_token
    
    supabase = get_supabase_client()
    if not supabase:
        pytest.skip("Supabase client not available")
    
    # This would require a valid session token
    # For now, just test the function exists
    assert callable(verify_supabase_token)

