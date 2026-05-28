"""
Base HTTP client for fal.ai API
"""

import logging
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class FalClient:
    """
    Base HTTP client for interacting with fal.ai API.
    Handles authentication, request submission, and response retrieval.
    """

    def __init__(self, api_key: Optional[str] = None, timeout: Optional[float] = None):
        """
        Initialize fal.ai client.

        Args:
            api_key: fal.ai API key (defaults to settings.fal_api_key)
            timeout: Request timeout in seconds (defaults to settings.fal_default_timeout)
        """
        self.api_key = api_key or settings.fal_api_key
        self.base_url = settings.fal_base_url
        self.timeout = timeout or settings.fal_default_timeout

        if not self.api_key:
            logger.warning("fal.ai API key not configured")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Key {self.api_key}"
        return headers

    async def submit_job(
        self, model_id: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Submit an async job to fal.ai queue.

        Args:
            model_id: Model identifier (e.g., "flux-pro/v1.1-ultra", "yue", "veo2")
            payload: Request payload (prompt, lyrics, etc.)

        Returns:
            Job submission response with status_url, response_url, cancel_url

        Raises:
            httpx.HTTPError: If request fails
            ValueError: If API key is missing
        """
        if not self.api_key:
            raise ValueError("fal.ai API key not configured")

        url = f"{self.base_url}/{model_id}"
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"fal.ai API error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(f"fal.ai request error: {e}")
            raise

    async def get_status(self, status_url: str) -> Dict[str, Any]:
        """
        Get job status from status URL.

        Args:
            status_url: Status check URL from job submission

        Returns:
            Job status response

        Raises:
            httpx.HTTPError: If request fails
        """
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(status_url, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"fal.ai status check error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(f"fal.ai status request error: {e}")
            raise

    async def get_result(self, response_url: str) -> Dict[str, Any]:
        """
        Get completed job result from response URL.

        Args:
            response_url: Response URL from job submission or status check

        Returns:
            Job result (images, video, audio, etc.)

        Raises:
            httpx.HTTPError: If request fails
        """
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(response_url, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"fal.ai result retrieval error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(f"fal.ai result request error: {e}")
            raise

    async def cancel_job(self, cancel_url: str) -> Dict[str, Any]:
        """
        Cancel a queued or running job.

        Args:
            cancel_url: Cancel URL from job submission

        Returns:
            Cancellation response

        Raises:
            httpx.HTTPError: If request fails
        """
        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(cancel_url, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"fal.ai cancel error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(f"fal.ai cancel request error: {e}")
            raise
