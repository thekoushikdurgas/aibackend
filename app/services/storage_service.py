"""
Supabase Storage service for file operations
"""

import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from app.core.supabase_client import get_supabase_client, get_supabase_admin_client
from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Service for managing file storage in Supabase Storage"""

    def __init__(self, use_admin: bool = False):
        """
        Initialize storage service

        Args:
            use_admin: Use admin client (bypasses RLS)
        """
        self.use_admin = use_admin
        self.client = (
            get_supabase_admin_client() if use_admin else get_supabase_client()
        )
        self.buckets = {
            "uploads": settings.supabase_bucket_uploads,
            "avatars": settings.supabase_bucket_avatars,
            "documents": settings.supabase_bucket_documents,
        }

    def _get_bucket(self, bucket_type: str):
        """Get storage bucket reference"""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")

        bucket_name = self.buckets.get(bucket_type)
        if not bucket_name:
            raise ValueError(f"Unknown bucket type: {bucket_type}")

        return self.client.storage.from_(bucket_name)

    def upload_file(
        self,
        bucket_type: str,
        file_path: str,
        file_data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Upload file to Supabase Storage

        Args:
            bucket_type: Type of bucket (uploads, avatars, documents)
            file_path: Path within bucket (e.g., "user_id/filename.pdf")
            file_data: File content as bytes
            content_type: MIME type (e.g., "application/pdf")
            metadata: Optional file metadata

        Returns:
            Public URL or storage path if successful, None otherwise
        """
        try:
            bucket = self._get_bucket(bucket_type)

            options = {}
            if content_type:
                options["content-type"] = content_type
            if metadata:
                options["metadata"] = metadata

            response = bucket.upload(
                path=file_path, file=file_data, file_options=options
            )

            if response:
                logger.info(f"File uploaded successfully: {file_path}")
                return file_path
            return None
        except Exception as e:
            logger.error(f"Error uploading file {file_path}: {e}")
            return None

    def upload_file_from_path(
        self,
        bucket_type: str,
        local_file_path: str,
        storage_file_path: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Upload file from local filesystem

        Args:
            bucket_type: Type of bucket
            local_file_path: Path to local file
            storage_file_path: Path in storage (defaults to filename)
            content_type: MIME type
            metadata: Optional metadata

        Returns:
            Storage path if successful, None otherwise
        """
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
        """
        Download file from Supabase Storage

        Args:
            bucket_type: Type of bucket
            file_path: Path within bucket

        Returns:
            File content as bytes, None if not found
        """
        try:
            bucket = self._get_bucket(bucket_type)
            response = bucket.download(file_path)
            return response
        except Exception as e:
            logger.error(f"Error downloading file {file_path}: {e}")
            return None

    def get_public_url(self, bucket_type: str, file_path: str) -> Optional[str]:
        """
        Get public URL for a file (for public buckets)

        Args:
            bucket_type: Type of bucket
            file_path: Path within bucket

        Returns:
            Public URL if available
        """
        try:
            bucket = self._get_bucket(bucket_type)
            response = bucket.get_public_url(file_path)
            return response
        except Exception as e:
            logger.error(f"Error getting public URL for {file_path}: {e}")
            return None

    def create_signed_url(
        self, bucket_type: str, file_path: str, expires_in: int = 3600
    ) -> Optional[str]:
        """
        Create signed URL for private file access

        Args:
            bucket_type: Type of bucket
            file_path: Path within bucket
            expires_in: Expiration time in seconds (default 1 hour)

        Returns:
            Signed URL if successful, None otherwise
        """
        try:
            bucket = self._get_bucket(bucket_type)
            response = bucket.create_signed_url(path=file_path, expires_in=expires_in)
            return response.get("signedURL") if response else None
        except Exception as e:
            logger.error(f"Error creating signed URL for {file_path}: {e}")
            return None

    def delete_file(self, bucket_type: str, file_path: str) -> bool:
        """
        Delete file from Supabase Storage

        Args:
            bucket_type: Type of bucket
            file_path: Path within bucket

        Returns:
            True if successful, False otherwise
        """
        try:
            bucket = self._get_bucket(bucket_type)
            response = bucket.remove([file_path])
            return len(response) > 0
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False

    def list_files(
        self,
        bucket_type: str,
        folder_path: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        List files in a bucket

        Args:
            bucket_type: Type of bucket
            folder_path: Optional folder path to list
            limit: Maximum number of files
            offset: Offset for pagination

        Returns:
            List of file metadata
        """
        try:
            bucket = self._get_bucket(bucket_type)
            response = bucket.list(path=folder_path or "", limit=limit, offset=offset)
            return response if response else []
        except Exception as e:
            logger.error(f"Error listing files in {bucket_type}: {e}")
            return []

    def move_file(self, bucket_type: str, from_path: str, to_path: str) -> bool:
        """
        Move/rename file in storage

        Args:
            bucket_type: Type of bucket
            from_path: Current file path
            to_path: New file path

        Returns:
            True if successful, False otherwise
        """
        try:
            self._get_bucket(bucket_type)
            # Supabase Storage doesn't have a direct move, so we copy and delete
            file_data = self.download_file(bucket_type, from_path)
            if not file_data:
                return False

            if self.upload_file(bucket_type, to_path, file_data):
                return self.delete_file(bucket_type, from_path)
            return False
        except Exception as e:
            logger.error(f"Error moving file from {from_path} to {to_path}: {e}")
            return False


# Convenience function
def get_storage_service(use_admin: bool = False) -> StorageService:
    """Get storage service instance"""
    return StorageService(use_admin=use_admin)
