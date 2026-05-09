"""
Optional S3 storage adapter.

The current production storage implementation is Supabase Storage
(`StorageService` in `storage_service.py`). This adapter provides
AWS S3 access using boto3 with blocking I/O offloaded via `asyncio.to_thread`
when the async API is used.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings

logger = logging.getLogger(__name__)


def _boto3_client():
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        raise RuntimeError(
            "AWS credentials not configured (aws_access_key_id / aws_secret_access_key)"
        )
    return boto3.client(
        "s3",
        region_name=settings.aws_region or "us-east-1",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        config=Config(retries={"max_attempts": 3, "mode": "adaptive"}),
    )


def _s3_url(bucket: str, key: str) -> str:
    return f"s3://{bucket}/{key}"


class S3StorageAdapter:
    """
    S3 bucket adapter. Bucket name is taken from constructor or `settings.aws_s3_bucket`.
    """

    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = (bucket_name or settings.aws_s3_bucket or "").strip()
        if not self.bucket_name:
            raise ValueError(
                "S3 bucket name is required (constructor or settings.aws_s3_bucket)"
            )

    def _put_object(
        self, key: str, data: bytes, content_type: Optional[str] = None
    ) -> str:
        client = _boto3_client()
        extra: dict = {}
        if content_type:
            extra["ContentType"] = content_type
        client.put_object(Bucket=self.bucket_name, Key=key, Body=data, **extra)
        return _s3_url(self.bucket_name, key)

    def _get_object(self, key: str) -> bytes:
        client = _boto3_client()
        resp = client.get_object(Bucket=self.bucket_name, Key=key)
        return resp["Body"].read()

    def _delete_object(self, key: str) -> bool:
        client = _boto3_client()
        try:
            client.delete_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404", "NotFound"):
                return False
            raise

    # --- async API (uses asyncio.to_thread) ---

    async def upload_file(
        self, key: str, data: bytes, content_type: Optional[str] = None
    ) -> str:
        return await asyncio.to_thread(self._put_object, key, data, content_type)

    async def download_file(self, key: str) -> bytes:
        return await asyncio.to_thread(self._get_object, key)

    async def delete_file(self, key: str) -> bool:
        return await asyncio.to_thread(self._delete_object, key)

    # --- sync API (for non-async call sites) ---

    def upload_file_sync(
        self, key: str, data: bytes, content_type: Optional[str] = None
    ) -> str:
        try:
            return self._put_object(key, data, content_type)
        except (BotoCoreError, ClientError) as e:
            logger.error("S3 upload failed: %s", e)
            raise

    def download_file_sync(self, key: str) -> bytes:
        try:
            return self._get_object(key)
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                raise FileNotFoundError(key) from e
            raise

    def delete_file_sync(self, key: str) -> bool:
        try:
            return self._delete_object(key)
        except (BotoCoreError, ClientError) as e:
            logger.error("S3 delete failed: %s", e)
            raise
