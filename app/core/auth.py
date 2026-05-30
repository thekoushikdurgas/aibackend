"""
Authentication and authorization for DurgasAI Backend (JWT + API key).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader

import jwt
from jwt.exceptions import PyJWTError
from starlette.requests import Request

from app.config import settings
from app.core.session_cookies import ACCESS_TOKEN_COOKIE
from app.utils.helpers import utc_now

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# bcrypt rejects secrets longer than 72 bytes (UTF-8); align with prior passlib/bcrypt behavior.
_BCRYPT_MAX_PASSWORD_BYTES = 72

JWT_TYP_ACCESS = "access"
JWT_TYP_REFRESH = "refresh"
JWT_TYP_PASSWORD_RESET = "password_reset"
JWT_TYP_MAGIC_LOGIN = "magic_login"


def hash_password(plain: str) -> str:
    raw = plain.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password is too long (max {_BCRYPT_MAX_PASSWORD_BYTES} bytes in UTF-8)."
        )
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode("ascii")


def verify_password(plain: str, hashed: Optional[str]) -> bool:
    if not hashed:
        return False
    raw = plain.encode("utf-8")
    # Legacy bcrypt (and older passlib) truncated at 72 bytes; match that on verify.
    if len(raw) > _BCRYPT_MAX_PASSWORD_BYTES:
        raw = raw[:_BCRYPT_MAX_PASSWORD_BYTES]
    try:
        return bcrypt.checkpw(
            raw,
            hashed.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT (used for access tokens or other signed payloads)."""
    to_encode = data.copy()

    if expires_delta:
        expire = utc_now() + expires_delta
    else:
        expire = utc_now() + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode.setdefault("exp", expire)

    return jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def issue_access_token(
    user_id: str, email: str, token_version: int
) -> tuple[str, datetime]:
    """Return (jwt, expiry datetime)."""
    expire = utc_now() + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "email": email,
        "typ": JWT_TYP_ACCESS,
        "tv": token_version,
        "exp": expire,
    }
    return (
        jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm),
        expire,
    )


def issue_refresh_token(user_id: str, token_version: int) -> str:
    expire = utc_now() + timedelta(days=settings.jwt_refresh_token_expire_days)
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
    expire = utc_now() + timedelta(hours=1)
    payload = {
        "sub": user_id,
        "typ": JWT_TYP_PASSWORD_RESET,
        "exp": expire,
    }
    return jwt.encode(
        payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def issue_magic_login_token(email: str) -> str:
    expire = utc_now() + timedelta(minutes=15)
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
    except PyJWTError as e:
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
    except PyJWTError:
        return None


def access_payload_if_valid(token: Optional[str]) -> Optional[dict]:
    """Return access-token payload if JWT is valid and typ is access (or legacy typ omitted)."""
    if not token or not token.strip():
        return None
    p = try_decode_token(token.strip())
    if not p:
        return None
    typ = p.get("typ")
    if typ is not None and typ != JWT_TYP_ACCESS:
        return None
    return p


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
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
) -> dict:
    """
    API key first (extension), then JWT access token from Bearer or httpOnly cookie.

    Cookie fallback matches GraphQL context behavior when Apollo uses credentials-only
    and localStorage Bearer is stale.
    """
    if api_key:
        if verify_api_key(api_key):
            return {"sub": "api_key_user", "type": "api_key"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key"
        )

    bearer_t = (
        credentials.credentials.strip()
        if credentials and credentials.credentials
        else None
    )
    cookie_t = (request.cookies.get(ACCESS_TOKEN_COOKIE) or "").strip() or None

    bp = access_payload_if_valid(bearer_t)
    cp = access_payload_if_valid(cookie_t)

    if bp:
        return bp
    if cp:
        return cp
    if bearer_t:
        return verify_token(bearer_t)
    if cookie_t:
        return verify_token(cookie_t)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key: Optional[str] = Depends(api_key_header),
) -> Optional[dict]:
    try:
        return await get_current_user(request, credentials, api_key)
    except HTTPException:
        return None


class AuthRequired:
    """Dependency class for requiring authentication."""

    def __init__(self, required: bool = True):
        self.required = required

    async def __call__(
        self,
        request: Request,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
        api_key: Optional[str] = Depends(api_key_header),
    ) -> Optional[dict]:
        if self.required:
            return await get_current_user(request, credentials, api_key)
        return await get_optional_user(request, credentials, api_key)


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
    expires_in = max(1, int((expires_at - utc_now()).total_seconds()))
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
