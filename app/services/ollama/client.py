"""
Ollama Unified Client
Base client for all Ollama API interactions with localhost and cloud support
"""

import logging
from typing import Dict, Optional
from enum import Enum

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaMode(str, Enum):
    """Ollama deployment modes"""

    LOCALHOST = "localhost"  # http://localhost:11434/api
    CLOUD = "cloud"  # https://ollama.com/api


class OllamaClient:
    """
    Unified client for Ollama API interactions.

    Handles:
    - Localhost and cloud mode switching
    - Authentication header management (cloud mode)
    - Base URL selection
    - Error handling with Ollama-specific messages
    - Async HTTP client pooling
    """

    # Default base URLs
    LOCALHOST_BASE = "http://localhost:11434/api"
    CLOUD_BASE = "https://ollama.com/api"

    def __init__(
        self,
        base_url: Optional[str] = None,
        cloud_url: Optional[str] = None,
        api_key: Optional[str] = None,
        mode: Optional[OllamaMode] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize Ollama client.

        Args:
            base_url: Base URL for localhost mode (defaults to settings)
            cloud_url: Base URL for cloud mode (defaults to settings)
            api_key: API key for cloud mode (optional)
            mode: Deployment mode (localhost or cloud)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url or settings.ollama_base_url
        self.cloud_url = cloud_url or getattr(
            settings, "ollama_cloud_url", self.CLOUD_BASE
        )
        self.api_key = api_key or getattr(settings, "ollama_api_key", None)
        self.timeout = timeout

        # Determine mode
        mode_str = mode or getattr(settings, "ollama_mode", "localhost")
        self.mode = (
            OllamaMode(mode_str.lower())
            if isinstance(mode_str, str)
            else mode or OllamaMode.LOCALHOST
        )

        if self.mode == OllamaMode.CLOUD and not self.api_key:
            logger.warning("Ollama cloud mode requires API key")

    def get_base_url(self) -> str:
        """
        Get the appropriate base URL based on mode.

        Returns:
            Base URL string
        """
        if self.mode == OllamaMode.CLOUD:
            return self.cloud_url
        else:
            return self.base_url

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication if needed"""
        headers = {"Content-Type": "application/json"}

        # Add API key for cloud mode
        if self.mode == OllamaMode.CLOUD and self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    async def _make_request(
        self, method: str, endpoint: str, **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request to Ollama API.

        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx request

        Returns:
            httpx.Response object
        """
        base_url = self.get_base_url()
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        headers = self._get_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        timeout = kwargs.pop("timeout", self.timeout)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(method, url, headers=headers, **kwargs)
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as e:
            error_msg = self._extract_error_message(e)
            logger.error(f"Ollama API error ({e.response.status_code}): {error_msg}")
            raise Exception(f"Ollama API error: {error_msg}")
        except httpx.RequestError as e:
            logger.error(f"Ollama API request error: {e}")
            raise Exception(f"Ollama API request error: {str(e)}")

    def _extract_error_message(self, error: httpx.HTTPStatusError) -> str:
        """Extract error message from HTTP error response"""
        if hasattr(error, "response") and error.response is not None:
            try:
                error_data = error.response.json()
                if isinstance(error_data, dict):
                    error_msg = error_data.get("error", str(error))
                    return str(error_msg)
                return str(error_data)
            except (ValueError, AttributeError, KeyError):
                return error.response.text or str(error)
        return str(error)

    async def post(self, endpoint: str, **kwargs) -> httpx.Response:
        """Make a POST request"""
        return await self._make_request("POST", endpoint, **kwargs)

    async def get(self, endpoint: str, **kwargs) -> httpx.Response:
        """Make a GET request"""
        return await self._make_request("GET", endpoint, **kwargs)

    async def delete(self, endpoint: str, **kwargs) -> httpx.Response:
        """Make a DELETE request"""
        return await self._make_request("DELETE", endpoint, **kwargs)

    async def stream(self, endpoint: str, **kwargs) -> httpx.AsyncClient:
        """
        Create a streaming request context.

        Returns:
            httpx.AsyncClient context manager for streaming
        """
        base_url = self.get_base_url()
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        headers = self._get_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        timeout = kwargs.pop("timeout", self.timeout)

        client = httpx.AsyncClient(timeout=timeout)
        return client.stream("POST", url, headers=headers, **kwargs)

    async def health_check(self) -> bool:
        """
        Check if Ollama API is available.

        Returns:
            True if API is available, False otherwise
        """
        try:
            response = await self.get("tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
