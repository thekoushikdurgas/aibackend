"""
Gemini Batch Processing Service
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class GeminiBatchService:
    """
    Service for batch processing with Gemini API.
    Allows submitting multiple requests for asynchronous processing.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0,
    ):
        """
        Initialize Gemini batch service.

        Args:
            api_key: Gemini API key
            model: Model to use for batch processing
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.timeout = timeout
        self.base_url = settings.gemini_base_url

        if not self.api_key:
            logger.warning("Gemini API key not configured")

    async def create_batch(
        self, requests: List[Dict[str, Any]], display_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a batch processing job.

        Args:
            requests: List of request objects with 'request' and optional 'metadata'
            display_name: Optional display name for the batch

        Returns:
            Batch creation response with batch name
        """
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        # Use batchGenerateContent endpoint
        url = f"{self.base_url}/models/{self.model}:batchGenerateContent"
        headers = {"x-goog-api-key": self.api_key}

        payload = {
            "batch": {
                "display_name": display_name or f"batch-{self.model}",
                "input_config": {"requests": {"requests": requests}},
            }
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Gemini batch creation error: {e}")
            raise Exception(f"Gemini batch creation error: {str(e)}")

    async def get_batch(self, batch_name: str) -> Dict[str, Any]:
        """
        Get batch status and results.

        Args:
            batch_name: Name of the batch (e.g., "batches/...")

        Returns:
            Batch status and results
        """
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        url = f"{self.base_url}/{batch_name}"
        headers = {"x-goog-api-key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Gemini batch get error: {e}")
            raise Exception(f"Gemini batch get error: {str(e)}")

    async def list_batches(
        self, page_size: int = 20, page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List all batches.

        Args:
            page_size: Number of batches per page
            page_token: Token for pagination

        Returns:
            List of batches
        """
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        url = f"{self.base_url}/batches"
        headers = {"x-goog-api-key": self.api_key}
        params = {"page_size": page_size}
        if page_token:
            params["page_token"] = page_token

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Gemini batch list error: {e}")
            raise Exception(f"Gemini batch list error: {str(e)}")

    async def cancel_batch(self, batch_name: str) -> Dict[str, Any]:
        """
        Cancel a batch job.

        Args:
            batch_name: Name of the batch to cancel

        Returns:
            Cancellation response
        """
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        url = f"{self.base_url}/{batch_name}:cancel"
        headers = {"x-goog-api-key": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers)
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Gemini batch cancel error: {e}")
            raise Exception(f"Gemini batch cancel error: {str(e)}")
