"""
Authentication and authorization for DurgasAI Backend
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt

from app.config import settings
from app.core.supabase_client import get_supabase_client, is_supabase_configured

logger = logging.getLogger(__name__)

# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )

    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verify and decode a JWT token (legacy JWT or Supabase token)
    """
    # Try Supabase token first if configured
    if is_supabase_configured():
        supabase_user = verify_supabase_token(token)
        if supabase_user:
            return supabase_user

    # Fallback to legacy JWT verification
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_supabase_token(token: str) -> Optional[dict]:
    """
    Verify Supabase JWT token

    Args:
        token: Supabase JWT token

    Returns:
        User dict with Supabase user info, None if invalid
    """
    try:
        supabase = get_supabase_client()
        if not supabase:
            return None

        # Get user from token
        response = supabase.auth.get_user(token)
        if response and response.user:
            user = response.user
            return {
                "sub": user.id,
                "email": user.email,
                "type": "supabase",
                "user_metadata": user.user_metadata or {},
                "app_metadata": user.app_metadata or {},
            }
        return None
    except Exception as e:
        logger.debug(f"Supabase token verification failed: {e}")
        return None


async def get_current_supabase_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[dict]:
    """
    Get current Supabase user from token

    Returns:
        User dict if authenticated, None otherwise
    """
    if not is_supabase_configured():
        return None

    if not credentials:
        return None

    return verify_supabase_token(credentials.credentials)


def verify_api_key(api_key: str) -> bool:
    """
    Verify an API key
    """
    return api_key == settings.api_key


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
) -> dict:
    """
    Get current user from Supabase token, JWT token, or API key
    Priority: Supabase token > API key > Legacy JWT
    """
    # Try Supabase token first if configured
    if is_supabase_configured() and credentials:
        supabase_user = verify_supabase_token(credentials.credentials)
        if supabase_user:
            return supabase_user

    # Try API key (backward compatibility)
    if api_key:
        if verify_api_key(api_key):
            return {"sub": "api_key_user", "type": "api_key"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    # Try legacy JWT token
    if credentials:
        payload = verify_token(credentials.credentials)
        return payload

    # No authentication provided
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
) -> Optional[dict]:
    """
    Get current user if authenticated, otherwise return None
    """
    try:
        return await get_current_user(credentials, api_key)
    except HTTPException:
        return None


class AuthRequired:
    """
    Dependency class for requiring authentication
    """

    def __init__(self, required: bool = True):
        self.required = required

    async def __call__(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
        api_key: Optional[str] = Depends(api_key_header),
    ) -> Optional[dict]:
        if self.required:
            return await get_current_user(credentials, api_key)
        return await get_optional_user(credentials, api_key)
