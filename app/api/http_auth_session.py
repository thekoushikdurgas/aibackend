"""HTTP session persistence for durgasos (replaces Next.js /api/auth/session)."""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.core.session_cookies import ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE

router = APIRouter(prefix="/api/auth", tags=["auth-session"])

_SAMESITE = Literal["lax", "strict", "none"]


class SessionBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    expires_in: Optional[int] = Field(default=None, alias="expiresIn")


def _samesite() -> _SAMESITE:
    raw = (settings.session_cookie_samesite or "lax").strip().lower()
    if raw in ("lax", "strict", "none"):
        return raw  # type: ignore[return-value]
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


def _attach_session_cookies(
    resp: JSONResponse,
    access_token: str,
    refresh_token: str,
    access_max_age: int,
) -> None:
    domain = _cookie_domain()
    secure = _secure()
    same_site = _samesite()
    resp.set_cookie(
        ACCESS_TOKEN_COOKIE,
        access_token,
        max_age=access_max_age,
        httponly=True,
        secure=secure,
        samesite=same_site,
        path="/",
        domain=domain,
    )
    resp.set_cookie(
        REFRESH_TOKEN_COOKIE,
        refresh_token,
        max_age=60 * 60 * 24 * 30,
        httponly=True,
        secure=secure,
        samesite=same_site,
        path="/",
        domain=domain,
    )


def _clear_session_cookies(resp: JSONResponse) -> None:
    domain = _cookie_domain()
    secure = _secure()
    same_site = _samesite()
    for name in (ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE):
        resp.delete_cookie(
            name,
            path="/",
            domain=domain,
            secure=secure,
            httponly=True,
            samesite=same_site,
        )


@router.post("/session")
async def post_session(request: Request) -> JSONResponse:
    try:
        raw = await request.body()
        data: Any = json.loads(raw.decode("utf-8") or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JSONResponse(
            {"ok": False, "error": "Invalid JSON"},
            status_code=400,
        )

    try:
        body = SessionBody.model_validate(data)
    except Exception:
        return JSONResponse(
            {"ok": False, "error": "accessToken and refreshToken required"},
            status_code=400,
        )

    if not body.access_token.strip() or not body.refresh_token.strip():
        return JSONResponse(
            {"ok": False, "error": "accessToken and refreshToken required"},
            status_code=400,
        )

    max_age = max(60, int(body.expires_in or 3600))
    resp = JSONResponse({"ok": True})
    _attach_session_cookies(resp, body.access_token, body.refresh_token, max_age)
    return resp


@router.delete("/session")
async def delete_session() -> JSONResponse:
    resp = JSONResponse({"ok": True})
    _clear_session_cookies(resp)
    return resp
