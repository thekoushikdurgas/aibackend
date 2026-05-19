"""HttpOnly session probe for the OS shell (browser calls same-origin path; Next rewrites here)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.session_cookies import ACCESS_TOKEN_COOKIE

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.get("/session")
async def get_auth_session(request: Request) -> JSONResponse:
    raw = (request.cookies.get(ACCESS_TOKEN_COOKIE) or "").strip()
    return JSONResponse({"authenticated": bool(raw)})
