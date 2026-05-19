"""Resolve authenticated user for GraphQL (parity with FastAPI ``get_current_user``)."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException
from graphql import GraphQLError
from strawberry.types import Info

from app.core.auth import (
    access_payload_if_valid,
    verify_api_key,
    verify_token,
)
from app.core.session_cookies import ACCESS_TOKEN_COOKIE
from app.graphql.context import GraphQLContext


def _bearer_from_request(request: Any) -> str | None:
    raw = request.headers.get("authorization") or ""
    if raw.lower().startswith("bearer "):
        return raw[7:].strip() or None
    return None


def require_auth_user_dict(info: Info) -> Dict[str, Any]:
    """Raise GraphQLError if the caller is not authenticated (Bearer, cookie, or API key)."""
    ctx = info.context
    if not isinstance(ctx, GraphQLContext):
        raise GraphQLError("Invalid context", extensions={"code": "INTERNAL"})
    request = ctx.request

    api_key = (request.headers.get("x-api-key") or "").strip()
    if api_key:
        if verify_api_key(api_key):
            return {"sub": "api_key_user", "type": "api_key"}
        raise GraphQLError("Invalid API key", extensions={"code": "UNAUTHENTICATED"})

    bearer_t = _bearer_from_request(request)
    cookie_t = (request.cookies.get(ACCESS_TOKEN_COOKIE) or "").strip() or None

    bp = access_payload_if_valid(bearer_t)
    cp = access_payload_if_valid(cookie_t)
    if bp:
        return bp
    if cp:
        return cp
    if bearer_t:
        try:
            return verify_token(bearer_t)
        except HTTPException:
            pass
    if cookie_t:
        try:
            return verify_token(cookie_t)
        except HTTPException:
            pass

    raise GraphQLError(
        "Authentication required",
        extensions={"code": "UNAUTHENTICATED"},
    )
