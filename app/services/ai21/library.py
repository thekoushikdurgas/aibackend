"""
AI21 Labs Library Service
Provides RAG/Library management functionality for document storage and search
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AI21LibraryService:
    """Service for AI21 Labs Library/RAG features"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize AI21 Library service.

        Args:
            api_key: AI21 API key
            base_url: Base URL for AI21 API
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.ai21_api_key
        self.base_url = base_url or settings.ai21_base_url
        self.timeout = timeout

        if not self.api_key:
            logger.warning("AI21 API key not configured")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def upload_file(
        self, file_content: bytes, file_name: str, labels: Optional[List[str]] = None
    ) -> Dict:
        """
        Upload a file to AI21 Library.

        Args:
            file_content: File content as bytes
            file_name: Name of the file
            labels: Optional list of labels for the file

        Returns:
            Dictionary with file ID and metadata
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/library/files"

        # Prepare multipart form data
        files = {"file": (file_name, file_content)}

        data = {}
        if labels:
            data["labels"] = ",".join(labels)

        headers = {
            "Authorization": f"Bearer {self.api_key}"
            # Note: Don't set Content-Type for multipart/form-data, httpx will set it automatically
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, files=files, data=data, headers=headers
                )
                response.raise_for_status()
                result = response.json()

                return {
                    "fileId": result.get("fileId") or result.get("id"),
                    "name": result.get("name", file_name),
                    "labels": result.get("labels", labels or []),
                    "publicUrl": result.get("publicUrl"),
                }
        except httpx.HTTPError as e:
            logger.error(f"AI21 file upload error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 file upload error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 file upload error: {str(e)}")

    async def search(self, query: str, file_ids: Optional[List[str]] = None) -> Dict:
        """
        Search documents in the library.

        Args:
            query: Search query
            file_ids: Optional list of file IDs to search within

        Returns:
            Dictionary with matching documents and relevance scores
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/library/search"
        payload: dict[str, Any] = {"query": query}

        if file_ids:
            payload["fileIds"] = file_ids

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "results": data.get("results", []),
                    "id": data.get("id"),
                    "query": query,
                }
        except httpx.HTTPError as e:
            logger.error(f"AI21 library search error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 library search error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 library search error: {str(e)}")

    async def list_files(self) -> List[Dict]:
        """
        List all files in the library.

        Returns:
            List of file metadata dictionaries
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/library/files"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()

                return data if isinstance(data, list) else data.get("files", [])
        except httpx.HTTPError as e:
            logger.error(f"AI21 list files error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 list files error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 list files error: {str(e)}")

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from the library.

        Args:
            file_id: ID of the file to delete

        Returns:
            True if successful
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/library/files/{file_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(url, headers=self._get_headers())
                response.raise_for_status()
                return True
        except httpx.HTTPError as e:
            logger.error(f"AI21 delete file error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 delete file error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 delete file error: {str(e)}")
