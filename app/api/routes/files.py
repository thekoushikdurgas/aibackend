"""HTTP route to serve locally stored files (optional signed token)."""

from __future__ import annotations

import mimetypes

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.services.local_storage_service import _bucket_dir, verify_signed_token

router = APIRouter(tags=["files"])


@router.get("/{bucket}/{file_path:path}")
async def serve_storage_file(
    bucket: str,
    file_path: str,
    token: Optional[str] = Query(default=None),
):
    """Serve a file from ``storage_root``. Requires valid signed token if ``token`` is used."""
    base = _bucket_dir(bucket)
    target = (base / file_path).resolve()
    if not str(target).startswith(str(base.resolve())):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    if token:
        payload = verify_signed_token(token)
        if not payload or payload.get("b") != bucket or payload.get("p") != file_path:
            raise HTTPException(status_code=403, detail="Invalid or expired token")
    else:
        # Without token, only allow if you intentionally expose public reads later.
        raise HTTPException(status_code=403, detail="Signed URL required")

    media, _ = mimetypes.guess_type(str(target))
    return FileResponse(
        path=str(target),
        media_type=media or "application/octet-stream",
        filename=target.name,
    )
