"""
Hyperbolic API Base Client
HTTP client wrapper for all Hyperbolic API endpoints
"""

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class HyperbolicClient:
    """
    Base HTTP client for Hyperbolic APIs.
    Handles authentication, retry logic, and error handling.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize Hyperbolic client.

        Args:
            api_key: Hyperbolic API key
            base_url: Base URL (defaults to settings)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for transient failures
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.api_key = api_key or settings.hyperbolic_api_key
        self.base_url = base_url or settings.hyperbolic_base_url
        self.timeout = timeout or settings.hyperbolic_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        if not self.api_key:
            logger.warning("Hyperbolic API key not configured")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authorization"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _handle_response(
        self, response: httpx.Response, retry_count: int = 0
    ) -> Optional[Dict[str, Any]]:
        """
        Handle HTTP response with error handling.

        Args:
            response: HTTP response
            retry_count: Current retry attempt

        Returns:
            Response data as dictionary, or None when the caller should retry

        Raises:
            httpx.HTTPStatusError: For HTTP errors
        """
        # Handle rate limiting and transient errors
        if response.status_code == 429:
            retry_after = int(
                response.headers.get("Retry-After", self.retry_delay * (2**retry_count))
            )
            if retry_count < self.max_retries:
                logger.warning(
                    f"Rate limited, waiting {retry_after}s (attempt {retry_count + 1}/{self.max_retries})"
                )
                await asyncio.sleep(retry_after)
                return None  # Signal to retry

        if response.status_code == 503:
            if retry_count < self.max_retries:
                wait_time = self.retry_delay * (2**retry_count)
                logger.info(
                    f"Service unavailable, waiting {wait_time:.1f}s (attempt {retry_count + 1}/{self.max_retries})"
                )
                await asyncio.sleep(wait_time)
                return None  # Signal to retry

        # Raise for other HTTP errors
        response.raise_for_status()

        # Parse JSON response
        try:
            return response.json()
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            raise

    async def post(
        self, endpoint: str, data: Dict[str, Any], timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Send POST request to Hyperbolic API.

        Args:
            endpoint: API endpoint path (e.g., "/chat/completions")
            data: Request payload
            timeout: Optional timeout override

        Returns:
            Response data as dictionary
        """
        url = f"{self.base_url}{endpoint}"
        timeout_val = timeout or self.timeout

        async with httpx.AsyncClient(timeout=timeout_val) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.post(
                        url, json=data, headers=self._get_headers()
                    )

                    result = await self._handle_response(response, attempt)
                    if result is not None:
                        return result

                    # If result is None, it means we should retry
                    if attempt < self.max_retries:
                        continue
                    else:
                        raise httpx.HTTPStatusError(
                            f"Request failed after {self.max_retries} retries",
                            request=response.request,
                            response=response,
                        )

                except httpx.HTTPError as e:
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay * (2**attempt)
                        logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                        continue
                    raise

        raise RuntimeError("HyperbolicClient.post: retry loop exited without result")

    async def post_stream(
        self, endpoint: str, data: Dict[str, Any], timeout: Optional[float] = None
    ) -> httpx.Response:
        """
        Send streaming POST request to Hyperbolic API.

        Args:
            endpoint: API endpoint path
            data: Request payload
            timeout: Optional timeout override

        Returns:
            Streaming HTTP response
        """
        url = f"{self.base_url}{endpoint}"
        timeout_val = timeout or self.timeout

        async with httpx.AsyncClient(timeout=timeout_val) as client:
            response = await client.post(url, json=data, headers=self._get_headers())
            response.raise_for_status()
            return response

    async def health_check(self) -> bool:
        """
        Check if the API is accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try a simple chat completion request with minimal tokens
            test_data = {
                "messages": [{"role": "user", "content": "test"}],
                "model": "meta-llama/Meta-Llama-3.1-70B-Instruct",
                "max_tokens": 1,
                "stream": False,
            }
            await self.post("/chat/completions", test_data)
            return True
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
