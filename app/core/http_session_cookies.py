"""HttpOnly session cookies (shared by GraphQL mutations and legacy HTTP routes)."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional, cast

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import Response

from app.config import settings
from app.core.session_cookies import ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE

_SAMESITE = Literal["lax", "strict", "none"]


class SessionBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    expires_in: Optional[int] = Field(default=None, alias="expiresIn")


def _samesite() -> _SAMESITE:
    raw = (settings.session_cookie_samesite or "lax").strip().lower()
    if raw in ("lax", "strict", "none"):
        return cast(_SAMESITE, raw)
    return "lax"


def _secure() -> bool:
    if settings.session_cookie_secure:
        return True
    return settings.is_production


def _cookie_domain() -> Optional[str]:
    d = settings.session_cookie_domain
    if d is None:
        return None
    s = str(d).strip()
    return s or None


def attach_session_cookies_to_response(
    response: Response,
    access_token: str,
    refresh_token: str,
    access_max_age: int,
) -> None:
    domain = _cookie_domain()
    secure = _secure()
    same_site = _samesite()
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        access_token,
        max_age=access_max_age,
        httponly=True,
        secure=secure,
        samesite=same_site,
        path="/",
        domain=domain,
    )
    response.set_cookie(
        REFRESH_TOKEN_COOKIE,
        refresh_token,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        secure=secure,
        samesite=same_site,
        path="/",
        domain=domain,
    )


def clear_session_cookies_on_response(response: Response) -> None:
    domain = _cookie_domain()
    secure = _secure()
    same_site = _samesite()
    for name in (ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE):
        response.delete_cookie(
            name,
            path="/",
            domain=domain,
            secure=secure,
            httponly=True,
            samesite=same_site,
        )


def parse_session_json_body(raw: bytes) -> tuple[Optional[SessionBody], Optional[str]]:
    try:
        data: Any = json.loads(raw.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, "Invalid JSON"
    try:
        body = SessionBody.model_validate(data)
    except Exception:
        return None, "accessToken and refreshToken required"
    if not body.access_token.strip() or not body.refresh_token.strip():
        return None, "accessToken and refreshToken required"
    return body, None


def json_response_with_session_cookies(body: SessionBody) -> JSONResponse:
    max_age = max(60, body.expires_in or 3600)
    resp = JSONResponse({"ok": True})
    attach_session_cookies_to_response(
        resp, body.access_token, body.refresh_token, max_age
    )
    return resp


def json_response_clear_session_cookies() -> JSONResponse:
    resp = JSONResponse({"ok": True})
    clear_session_cookies_on_response(resp)
    return resp
