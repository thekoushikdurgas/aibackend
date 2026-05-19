"""HMAC-signed GET reads for local filesystem storage (``storage_url_prefix``)."""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from app.services.local_storage_service import (
    resolve_signed_storage_file,
    verify_signed_token,
)

router = APIRouter(tags=["Storage"])


def _effective_media_type(resolved: Path, guessed: str | None) -> str:
    """Avoid ``application/octet-stream`` for web assets (Chromium may refuse to execute JS)."""
    ext = resolved.suffix.lower()
    if ext in (".js", ".cjs"):
        if not guessed or guessed == "application/octet-stream":
            return "text/javascript"
    if ext == ".mjs":
        return "text/javascript"
    if ext == ".css":
        if not guessed or guessed == "application/octet-stream":
            return "text/css"
    return guessed or "application/octet-stream"


def _verify_and_resolve(bucket_name: str, file_path: str, token: str) -> Path:
    payload = verify_signed_token(token)
    if not payload:
        raise HTTPException(status_code=403, detail="Invalid or expired token")
    b = payload.get("b")
    p = payload.get("p")
    if not isinstance(b, str) or not isinstance(p, str):
        raise HTTPException(status_code=403, detail="Invalid token payload")
    if b != bucket_name or p != file_path:
        raise HTTPException(status_code=403, detail="Token does not match path")

    resolved = resolve_signed_storage_file(bucket_name, file_path)
    if resolved is None:
        raise HTTPException(status_code=404, detail="Not found")
    return resolved


@router.head("/{bucket_name}/{file_path:path}")
async def head_signed_storage_file(
    bucket_name: str,
    file_path: str,
    token: str = Query(
        ..., description="HMAC-signed payload from storageSignedHttpUrl"
    ),
) -> Response:
    resolved = _verify_and_resolve(bucket_name, file_path, token)
    guessed, _ = mimetypes.guess_type(str(resolved))
    media_type = _effective_media_type(resolved, guessed)
    try:
        size = resolved.stat().st_size
    except OSError:
        size = 0
    return Response(
        status_code=200,
        headers={
            "Content-Type": media_type,
            "Content-Length": str(size),
        },
    )


@router.get("/{bucket_name}/{file_path:path}")
async def get_signed_storage_file(
    bucket_name: str,
    file_path: str,
    token: str = Query(
        ..., description="HMAC-signed payload from storageSignedHttpUrl"
    ),
) -> FileResponse:
    resolved = _verify_and_resolve(bucket_name, file_path, token)
    guessed, _ = mimetypes.guess_type(str(resolved))
    media_type = _effective_media_type(resolved, guessed)
    return FileResponse(
        path=str(resolved),
        media_type=media_type,
        filename=resolved.name,
    )
