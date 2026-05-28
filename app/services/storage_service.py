"""
File storage service (local filesystem backend).
"""

import logging
from typing import Any, Dict, List, Optional
from pathlib import Path

from app.services.local_storage_service import get_local_file_storage

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file storage (local disk)."""

    def __init__(self, use_admin: bool = False):
        self.use_admin = use_admin
        self._backend = get_local_file_storage(use_admin=use_admin)

    def upload_file(
        self,
        bucket_type: str,
        file_path: str,
        file_data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        return self._backend.upload_file(
            bucket_type, file_path, file_data, content_type, metadata
        )

    def upload_file_from_path(
        self,
        bucket_type: str,
        local_file_path: str,
        storage_file_path: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        try:
            local_path = Path(local_file_path)
            if not local_path.exists():
                logger.error(f"Local file not found: {local_file_path}")
                return None
            if not storage_file_path:
                storage_file_path = local_path.name
            with open(local_path, "rb") as f:
                file_data = f.read()
            if not content_type:
                import mimetypes

                content_type, _ = mimetypes.guess_type(str(local_path))
            return self.upload_file(
                bucket_type=bucket_type,
                file_path=storage_file_path,
                file_data=file_data,
                content_type=content_type,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Error uploading file from path {local_file_path}: {e}")
            return None

    def download_file(self, bucket_type: str, file_path: str) -> Optional[bytes]:
        return self._backend.download_file(bucket_type, file_path)

    def get_public_url(self, bucket_type: str, file_path: str) -> Optional[str]:
        return self._backend.get_public_url(bucket_type, file_path)

    def create_signed_url(
        self, bucket_type: str, file_path: str, expires_in: int = 3600
    ) -> Optional[str]:
        return self._backend.create_signed_url(bucket_type, file_path, expires_in)

    def delete_file(self, bucket_type: str, file_path: str) -> bool:
        return self._backend.delete_file(bucket_type, file_path)

    def list_files(
        self,
        bucket_type: str,
        folder_path: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        return self._backend.list_files(bucket_type, folder_path, limit, offset)

    def move_file(self, bucket_type: str, from_path: str, to_path: str) -> bool:
        return self._backend.move_file(bucket_type, from_path, to_path)

    def list_buckets(self) -> List[Dict[str, Any]]:
        return self._backend.list_buckets()

    def create_bucket(self, bucket_name: str, is_public: bool = False) -> None:
        self._backend.create_bucket(bucket_name, is_public)

    def delete_bucket(self, bucket_name: str) -> None:
        self._backend.delete_bucket(bucket_name)


def get_storage_service(use_admin: bool = False) -> StorageService:
    return StorageService(use_admin=use_admin)
