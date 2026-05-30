"""HMAC-signed GET reads for local filesystem storage (``storage_url_prefix``)."""

from __future__ import annotations

import logging
import mimetypes
import shutil
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from app.api.ws_methods.storage import _sanitize_relative_upload_path
from app.config import settings
from app.core.auth import get_current_user
from app.services.local_storage_service import (
    resolve_signed_storage_file,
    verify_signed_token,
)
from app.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)

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


# --- Chunked Upload REST API ---


class InitUploadRequest(BaseModel):
    file_path: str
    total_size: int
    content_type: str = "application/octet-stream"


class FinalizeUploadRequest(BaseModel):
    upload_id: str
    file_path: str
    content_type: str = "application/octet-stream"


@router.post("/upload/init")
async def init_chunked_upload(
    req: InitUploadRequest,
    user: dict = Depends(get_current_user),
):
    """Initialize a chunked file upload session."""
    user_id = user.get("sub") or user.get("id")
    try:
        sanitized_rel_path = _sanitize_relative_upload_path(req.file_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    final_file_path = (
        f"{user_id}/{sanitized_rel_path}" if user_id else sanitized_rel_path
    )

    upload_id = str(uuid.uuid4())
    temp_dir = Path(settings.storage_root) / "temp_uploads" / upload_id
    temp_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Initialized chunked upload {upload_id} for path {final_file_path}")
    return {
        "success": True,
        "upload_id": upload_id,
        "file_path": final_file_path,
        "chunk_size": 5 * 1024 * 1024,  # 5 MB
    }


@router.post("/upload/chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Receive a single chunk and save it to the temp session directory."""
    temp_dir = Path(settings.storage_root) / "temp_uploads" / upload_id
    if not temp_dir.is_dir():
        raise HTTPException(status_code=400, detail="Invalid upload_id session")

    chunk_file = temp_dir / f"chunk_{chunk_index}"
    try:
        with open(chunk_file, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        logger.error(
            f"Failed to write chunk {chunk_index} for session {upload_id}: {e}"
        )
        raise HTTPException(status_code=500, detail="Failed to write chunk")

    return {"success": True, "chunk_index": chunk_index}


@router.post("/upload/finalize")
async def finalize_upload(
    req: FinalizeUploadRequest,
    user: dict = Depends(get_current_user),
):
    """Merge all uploaded chunks and place the final file in user storage."""
    upload_id = req.upload_id
    temp_dir = Path(settings.storage_root) / "temp_uploads" / upload_id
    if not temp_dir.is_dir():
        raise HTTPException(status_code=400, detail="Invalid or expired upload session")

    bucket_name = settings.storage_bucket_uploads
    if not bucket_name:
        raise HTTPException(status_code=500, detail="Upload bucket not configured")

    base_dir = Path(settings.storage_root) / bucket_name
    final_dest = (base_dir / req.file_path).resolve()

    # Ensure safe path prefix
    if not str(final_dest).startswith(str(base_dir.resolve())):
        raise HTTPException(status_code=403, detail="Access denied")

    final_dest.parent.mkdir(parents=True, exist_ok=True)

    chunks = sorted(
        list(temp_dir.glob("chunk_*")), key=lambda p: int(p.name.split("_")[1])
    )
    if not chunks:
        raise HTTPException(status_code=400, detail="No chunks uploaded")

    logger.info(
        f"Finalizing upload {upload_id} to {final_dest} with {len(chunks)} chunks"
    )
    try:
        with open(final_dest, "wb") as dest_f:
            for chunk_path in chunks:
                with open(chunk_path, "rb") as src_f:
                    shutil.copyfileobj(src_f, dest_f)
    except Exception as e:
        logger.error(f"Failed to merge chunks for session {upload_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to merge chunks")
    finally:
        # Clean up temp folder
        from app.utils.filesystem import safe_rmtree

        safe_rmtree(temp_dir)

    # Generate thumbnail if it's an image
    from app.services.local_storage_service import _HAS_PIL

    if _HAS_PIL and req.content_type.startswith("image/"):
        try:
            from PIL import Image

            thumb = final_dest.with_name(final_dest.name + ".thumb.jpg")
            with Image.open(final_dest) as im:
                im.thumbnail((256, 256))
                im.convert("RGB").save(thumb, format="JPEG", quality=85)
        except Exception as te:
            logger.debug("thumbnail skip: %s", te)

    storage_service = get_storage_service(use_admin=False)
    public_url = storage_service.get_public_url("uploads", req.file_path)
    signed_url = storage_service.create_signed_url(
        "uploads", req.file_path, expires_in=3600
    )

    return {
        "success": True,
        "path": req.file_path,
        "public_url": public_url,
        "signed_url": signed_url,
        "bucket_type": "uploads",
    }
