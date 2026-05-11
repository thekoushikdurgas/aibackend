"""
Authentication WebSocket Methods (local JWT + SQLAlchemy users).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, cast

from fastapi import HTTPException

from app.config import settings
from app.core.auth import (
    JWT_TYP_ACCESS,
    JWT_TYP_PASSWORD_RESET,
    JWT_TYP_REFRESH,
    hash_password,
    issue_access_token,
    issue_magic_login_token,
    issue_password_reset_token,
    issue_refresh_token,
    session_dict_from_user_row,
    try_decode_token,
    user_dict_from_claims_and_db,
    verify_password,
    verify_refresh_token,
    verify_token,
)
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.core.ws_auth import require_auth
from app.database.repositories.profile_repo import ProfileRepository
from app.database.repositories.user_repo import UserRepository
from app.database.sqlalchemy import AsyncSessionLocal

logger = logging.getLogger(__name__)


async def handle_auth_signup(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """auth.signup — email/password registration."""
    email = (params.get("email") or "").strip()
    password = params.get("password")
    metadata = params.get("metadata") or {}

    if not email or not password:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Email and password are required"
        )

    async with AsyncSessionLocal() as session:
        try:
            ur = UserRepository(session)
            if await ur.get_by_email(email):
                raise JSONRPCError(
                    JSONRPCErrorCode.VALIDATION_ERROR, "Email already registered"
                )
            hp = hash_password(password)
            u = await ur.create(
                email=email,
                hashed_password=hp,
                user_metadata=metadata if isinstance(metadata, dict) else {},
                is_verified=True,
            )
            pr = ProfileRepository(session)
            await pr.create_for_user(u.id)
            await session.commit()
            await session.refresh(u)

            access, exp_at = issue_access_token(u.id, u.email, u.token_version or 0)
            refresh = issue_refresh_token(u.id, u.token_version or 0)
            sess = session_dict_from_user_row(u.id, u.email, access, refresh, exp_at)
            return {
                "success": True,
                "user": user_dict_from_claims_and_db(
                    u.id, u.email, u.user_metadata, u.created_at
                ),
                "session": sess,
                "requires_confirmation": False,
            }
        except JSONRPCError:
            await session.rollback()
            raise
        except Exception as e:
            await session.rollback()
            logger.error("Signup error: %s", e, exc_info=True)
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, f"Signup failed: {str(e)}"
            ) from e


async def handle_auth_signin(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """auth.signin — email/password login."""
    email = (params.get("email") or "").strip()
    password = params.get("password")

    if not email or not password:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Email and password are required"
        )

    async with AsyncSessionLocal() as session:
        ur = UserRepository(session)
        u = await ur.get_by_email(email)
        if not u or not verify_password(password, u.hashed_password):
            raise JSONRPCError(
                JSONRPCErrorCode.AUTHENTICATION_ERROR, "Invalid email or password"
            )
        if not u.is_active:
            raise JSONRPCError(
                JSONRPCErrorCode.AUTHENTICATION_ERROR, "Account is disabled"
            )

        access, exp_at = issue_access_token(u.id, u.email, u.token_version or 0)
        refresh = issue_refresh_token(u.id, u.token_version or 0)
        sess = session_dict_from_user_row(u.id, u.email, access, refresh, exp_at)
        return {
            "success": True,
            "user": user_dict_from_claims_and_db(
                u.id, u.email, u.user_metadata, u.created_at
            ),
            "session": sess,
        }


async def handle_auth_signout(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """auth.signout — invalidate refresh tokens (token_version bump)."""
    uid: Optional[str] = None
    if user and user.get("sub"):
        uid = str(user["sub"])
    rt = params.get("refresh_token")
    if not uid and rt:
        p = try_decode_token(rt)
        if p and p.get("typ") == JWT_TYP_REFRESH:
            uid = str(p.get("sub", "") or "")

    if uid:
        async with AsyncSessionLocal() as session:
            ur = UserRepository(session)
            await ur.increment_token_version(uid)
            await session.commit()

    return {"success": True, "message": "Signed out successfully"}


async def handle_auth_refresh(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """auth.refresh — exchange refresh JWT for new session."""
    refresh_token = params.get("refresh_token")
    if not refresh_token:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "refresh_token is required")

    try:
        claims = verify_refresh_token(refresh_token)
    except HTTPException as e:
        raise JSONRPCError(
            JSONRPCErrorCode.AUTHENTICATION_ERROR,
            str(e.detail) if hasattr(e, "detail") else "Invalid refresh token",
        ) from e

    uid = str(claims.get("sub", ""))
    tv_claim = int(claims.get("tv", -1))

    async with AsyncSessionLocal() as session:
        ur = UserRepository(session)
        u = await ur.get_by_id(uid)
        if not u or not u.is_active:
            raise JSONRPCError(
                JSONRPCErrorCode.AUTHENTICATION_ERROR, "Invalid refresh token"
            )
        if int(u.token_version or 0) != tv_claim:
            raise JSONRPCError(
                JSONRPCErrorCode.AUTHENTICATION_ERROR, "Session has been revoked"
            )

        access, exp_at = issue_access_token(u.id, u.email, u.token_version or 0)
        new_refresh = issue_refresh_token(u.id, u.token_version or 0)
        sess = session_dict_from_user_row(u.id, u.email, access, new_refresh, exp_at)
        await session.commit()
        return {"success": True, "session": sess}


async def handle_auth_verify(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """auth.verify — validate access JWT and optionally load user."""
    token = params.get("token")

    try:
        if token:
            try:
                claims = verify_token(token)
            except HTTPException as e:
                return {"valid": False, "error": str(e.detail)}
        elif user and user.get("sub"):
            claims = cast(Dict[str, Any], user)
        else:
            return {"valid": False, "error": "No token provided"}

        uid = str(claims.get("sub", ""))
        async with AsyncSessionLocal() as session:
            ur = UserRepository(session)
            u = await ur.get_by_id(uid)
            if not u:
                return {"valid": False, "error": "User not found"}
            if claims.get("typ") == JWT_TYP_ACCESS:
                tv = int(claims.get("tv", -1))
                if int(u.token_version or 0) != tv:
                    return {"valid": False, "error": "Token revoked"}

            return {
                "valid": True,
                "user": {
                    "id": u.id,
                    "email": u.email,
                    "user_metadata": u.user_metadata or {},
                    "app_metadata": {},
                },
            }
    except Exception as e:
        logger.debug("Verify failed: %s", e)
        return {"valid": False, "error": str(e)}


async def handle_auth_reset_password_request(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """auth.reset_password_request — issue signed reset token (log in debug)."""
    email = (params.get("email") or "").strip()
    if not email:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Email is required")

    async with AsyncSessionLocal() as session:
        ur = UserRepository(session)
        u = await ur.get_by_email(email)
        if u:
            tok = issue_password_reset_token(u.id)
            if settings.debug:
                logger.info("[debug] password reset token for %s: %s", email, tok)
        await session.commit()

    return {
        "success": True,
        "message": "If that email exists, reset instructions were sent",
    }


async def handle_auth_reset_password(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """auth.reset_password — complete reset using signed JWT."""
    token = params.get("token")
    new_password = params.get("new_password")
    if not token or not new_password:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Token and new_password are required"
        )

    payload = try_decode_token(token)
    if not payload or payload.get("typ") != JWT_TYP_PASSWORD_RESET:
        raise JSONRPCError(
            JSONRPCErrorCode.AUTHENTICATION_ERROR, "Invalid or expired reset token"
        )

    uid = str(payload.get("sub", ""))
    async with AsyncSessionLocal() as session:
        ur = UserRepository(session)
        u = await ur.get_by_id(uid)
        if not u:
            raise JSONRPCError(
                JSONRPCErrorCode.AUTHENTICATION_ERROR, "Invalid or expired reset token"
            )
        await ur.update_password(uid, hash_password(new_password))
        await ur.increment_token_version(uid)
        await session.commit()

    return {
        "success": True,
        "message": "Password reset successfully",
        "user": {"id": uid},
    }


async def handle_auth_update_user(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """auth.update_user — metadata / email / password for current user."""
    user = await require_auth(user, "auth.update_user")
    uid = str(user.get("sub") or user.get("id") or "")

    async with AsyncSessionLocal() as session:
        ur = UserRepository(session)
        u = await ur.get_by_id(uid)
        if not u:
            raise JSONRPCError(JSONRPCErrorCode.AUTHENTICATION_ERROR, "User not found")

        if "metadata" in params and params["metadata"] is not None:
            meta = params["metadata"]
            if isinstance(meta, dict):
                u = await ur.merge_user_metadata(uid, meta)
        if "email" in params and params["email"]:
            await ur.update_email(uid, str(params["email"]))
        if "password" in params and params["password"]:
            await ur.update_password(uid, hash_password(str(params["password"])))

        await session.commit()
        u2 = await ur.get_by_id(uid)
        assert u2 is not None

        return {
            "success": True,
            "user": user_dict_from_claims_and_db(
                u2.id, u2.email, u2.user_metadata, u2.created_at
            ),
        }


async def handle_auth_magic_link(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """auth.magic_link — signed login token (returned only when debug=True)."""
    email = (params.get("email") or "").strip()
    if not email:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Email is required")

    tok = issue_magic_login_token(email)
    if settings.debug:
        logger.info("[debug] magic login token for %s: %s", email, tok)

    out: Dict[str, Any] = {
        "success": True,
        "message": "Magic link issued (configure email delivery in production)",
    }
    if settings.debug:
        out["magic_token"] = tok
    return out


async def handle_auth_oauth_url(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    raise JSONRPCError(
        JSONRPCErrorCode.INTERNAL_ERROR,
        "OAuth URL flow is not configured (Supabase removed). Use email/password or magic link.",
    )


async def handle_auth_oauth_callback(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    raise JSONRPCError(
        JSONRPCErrorCode.INTERNAL_ERROR,
        "OAuth callback is not configured (Supabase removed).",
    )


def get_methods() -> Dict[str, Any]:
    return {
        "auth.signup": handle_auth_signup,
        "auth.signin": handle_auth_signin,
        "auth.signout": handle_auth_signout,
        "auth.refresh": handle_auth_refresh,
        "auth.verify": handle_auth_verify,
        "auth.reset_password_request": handle_auth_reset_password_request,
        "auth.reset_password": handle_auth_reset_password,
        "auth.update_user": handle_auth_update_user,
        "auth.magic_link": handle_auth_magic_link,
        "auth.oauth_url": handle_auth_oauth_url,
        "auth.oauth_callback": handle_auth_oauth_callback,
    }
