"""MinIO object storage service — S3-compatible blob layer for DurgasOS.

Kernel analogy: Block device driver / filesystem for large binary objects.
Small metadata stays in PostgreSQL; raw bytes live here.
"""

from __future__ import annotations

import asyncio
import logging
import mimetypes
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# Default buckets (mirroring storage_service names for compatibility)
BUCKET_UPLOADS = "user-uploads"
BUCKET_AVATARS = "user-avatars"
BUCKET_DOCUMENTS = "rag-documents"
BUCKET_ARTIFACTS = "artifacts"

_executor = ThreadPoolExecutor(max_workers=4)
_minio_client = None


def _get_client():
    """Synchronously get or create the Minio client."""
    global _minio_client
    if _minio_client is not None:
        return _minio_client
    endpoint = getattr(settings, "minio_endpoint", None)
    if not endpoint:
        return None
    try:
        from minio import Minio

        client = Minio(
            endpoint=endpoint,
            access_key=getattr(settings, "minio_access_key", "minioadmin"),
            secret_key=getattr(settings, "minio_secret_key", "minioadmin"),
            secure=getattr(settings, "minio_secure", False),
        )
        # Verify connectivity
        client.list_buckets()
        _minio_client = client
        logger.info("MinIO client connected to %s", endpoint)
    except ImportError:
        logger.warning("minio package not installed — MinIO service unavailable")
        _minio_client = None
    except Exception as exc:
        logger.warning("MinIO connection failed (%s) — service unavailable", exc)
        _minio_client = None
    return _minio_client


def _ensure_bucket(client, bucket: str) -> None:
    """Create bucket if it does not exist."""
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        logger.info("Created MinIO bucket: %s", bucket)


async def _run_sync(fn, *args, **kwargs):
    """Run a synchronous Minio call in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, lambda: fn(*args, **kwargs))


async def upload_bytes(
    data: bytes,
    filename: str,
    bucket: str = BUCKET_UPLOADS,
    user_id: Optional[str] = None,
    content_type: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Upload raw bytes to MinIO. Returns storage metadata or None on failure."""
    client = _get_client()
    if client is None:
        return None

    if content_type is None:
        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"

    # Build object key: user-scoped path
    prefix = f"{user_id}/" if user_id else ""
    ext = Path(filename).suffix
    object_key = f"{prefix}{uuid.uuid4().hex}{ext}"

    try:
        import io

        def _upload():
            _ensure_bucket(client, bucket)
            client.put_object(
                bucket_name=bucket,
                object_name=object_key,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )

        await _run_sync(_upload)
        logger.info("MinIO upload OK: %s/%s (%d bytes)", bucket, object_key, len(data))
        return {
            "bucket": bucket,
            "key": object_key,
            "filename": filename,
            "size_bytes": len(data),
            "content_type": content_type,
        }
    except Exception as exc:
        logger.error("MinIO upload failed: %s", exc)
        return None


async def presigned_upload_url(
    filename: str,
    bucket: str = BUCKET_UPLOADS,
    expires_seconds: int = 3600,
) -> Optional[str]:
    """Generate a presigned PUT URL so the frontend can upload directly."""
    client = _get_client()
    if client is None:
        return None
    ext = Path(filename).suffix
    object_key = f"presigned/{uuid.uuid4().hex}{ext}"
    try:

        def _get_url():
            _ensure_bucket(client, bucket)
            return client.presigned_put_object(
                bucket_name=bucket,
                object_name=object_key,
                expires=timedelta(seconds=expires_seconds),
            )

        url = await _run_sync(_get_url)
        return url
    except Exception as exc:
        logger.error("MinIO presigned URL failed: %s", exc)
        return None


async def presigned_download_url(
    bucket: str,
    key: str,
    expires_seconds: int = 3600,
) -> Optional[str]:
    """Generate a presigned GET URL for a stored object."""
    client = _get_client()
    if client is None:
        return None
    try:

        def _get_url():
            return client.presigned_get_object(
                bucket_name=bucket,
                object_name=key,
                expires=timedelta(seconds=expires_seconds),
            )

        return await _run_sync(_get_url)
    except Exception as exc:
        logger.error("MinIO download URL failed: %s", exc)
        return None


async def download_bytes(bucket: str, key: str) -> Optional[bytes]:
    """Download an object from MinIO and return as bytes."""
    client = _get_client()
    if client is None:
        return None
    try:

        def _download():
            response = client.get_object(bucket_name=bucket, object_name=key)
            data = response.read()
            response.close()
            return data

        return await _run_sync(_download)
    except Exception as exc:
        logger.error("MinIO download failed: %s", exc)
        return None


async def delete_object(bucket: str, key: str) -> bool:
    """Delete an object from MinIO."""
    client = _get_client()
    if client is None:
        return False
    try:
        await _run_sync(client.remove_object, bucket, key)
        return True
    except Exception as exc:
        logger.error("MinIO delete failed: %s", exc)
        return False
