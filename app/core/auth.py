"""
Authentication and authorization for DurgasAI Backend (JWT + API key).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_TYP_ACCESS = "access"
JWT_TYP_REFRESH = "refresh"
JWT_TYP_PASSWORD_RESET = "password_reset"
JWT_TYP_MAGIC_LOGIN = "magic_login"


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: Optional[str]) -> bool:
    if not hashed:
        return False
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT (used for access tokens or other signed payloads)."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.setdefault("exp", expire)

    return jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def issue_access_token(
    user_id: str, email: str, token_version: int
) -> tuple[str, datetime]:
    """Return (jwt, expiry datetime)."""
    expire = datetime.utcnow() + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": user_id,
        "email": email,
        "typ": JWT_TYP_ACCESS,
        "tv": token_version,
        "exp": expire,
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    ), expire


def issue_refresh_token(user_id: str, token_version: int) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "typ": JWT_TYP_REFRESH,
        "tv": token_version,
        "exp": expire,
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def issue_password_reset_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=1)
    payload = {
        "sub": user_id,
        "typ": JWT_TYP_PASSWORD_RESET,
        "exp": expire,
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def issue_magic_login_token(email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=15)
    payload = {
        "email": email.strip().lower(),
        "typ": JWT_TYP_MAGIC_LOGIN,
        "exp": expire,
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_token_payload(token: str) -> dict:
    """Decode and validate JWT; raises HTTPException if invalid."""
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def try_decode_token(token: Optional[str]) -> Optional[dict]:
    """Decode JWT without raising (GraphQL / optional auth)."""
    if not token:
        return None
    try:
        return jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError:
        return None


def verify_token(token: str) -> dict:
    """
    Verify access JWT (or legacy tokens without ``typ``).
    """
    payload = decode_token_payload(token)
    typ = payload.get("typ")
    if typ is not None and typ != JWT_TYP_ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def verify_refresh_token(token: str) -> dict:
    payload = decode_token_payload(token)
    if payload.get("typ") != JWT_TYP_REFRESH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def verify_api_key(api_key: str) -> bool:
    return api_key == settings.api_key


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
) -> dict:
    """
    API key first (extension), then Bearer JWT access token.
    """
    if api_key:
        if verify_api_key(api_key):
            return {"sub": "api_key_user", "type": "api_key"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    if credentials:
        return verify_token(credentials.credentials)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
) -> Optional[dict]:
    try:
        return await get_current_user(credentials, api_key)
    except HTTPException:
        return None


class AuthRequired:
    """Dependency class for requiring authentication."""

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


def user_claims_from_access_token(token: str) -> Optional[dict]:
    """Decode Bearer access token into user dict for GraphQL / WS helpers."""
    p = try_decode_token(token)
    if not p:
        return None
    typ = p.get("typ")
    if typ is not None and typ != JWT_TYP_ACCESS:
        return None
    sub = p.get("sub")
    if not sub:
        return None
    return {
        "sub": str(sub),
        "email": p.get("email"),
        "user_metadata": p.get("user_metadata") or {},
        "app_metadata": p.get("app_metadata") or {},
    }


def session_dict_from_user_row(
    user_id: str, email: str, access: str, refresh: str, expires_at: datetime
) -> Dict[str, Any]:
    expires_in = max(
        1, int((expires_at - datetime.utcnow()).total_seconds())
    )
    return {
        "access_token": access,
        "refresh_token": refresh,
        "expires_in": expires_in,
        "expires_at": int(expires_at.timestamp()),
        "token_type": "bearer",
    }


def user_dict_from_claims_and_db(
    user_id: str,
    email: str,
    user_metadata: Optional[Dict[str, Any]] = None,
    created_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    return {
        "id": user_id,
        "email": email,
        "user_metadata": user_metadata or {},
        "app_metadata": {},
        "created_at": created_at.isoformat() if created_at else None,
    }
