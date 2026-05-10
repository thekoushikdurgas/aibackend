"""
NVIDIA AI Unified Client
Base client for all NVIDIA API interactions with authentication, error handling, and base URL management
"""

import logging
from contextlib import AbstractAsyncContextManager
from enum import Enum
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from .models import get_base_url_type

logger = logging.getLogger(__name__)


class BaseURLType(str, Enum):
    """Base URL types for NVIDIA APIs"""

    INTEGRATE = "integrate"  # https://integrate.api.nvidia.com/v1
    GENAI = "genai"  # https://ai.api.nvidia.com/v1
    NIM = "nim"  # Custom NIM deployment URL


class NVIDIAClient:
    """
    Unified client for NVIDIA AI API interactions.

    Handles:
    - Authentication header management
    - Base URL selection (integrate vs genai vs nim)
    - Error handling with NVIDIA-specific headers
    - Rate limiting awareness
    - Async HTTP client pooling
    """

    # Default base URLs
    INTEGRATE_BASE = "https://integrate.api.nvidia.com/v1"
    GENAI_BASE = "https://ai.api.nvidia.com/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        genai_base_url: Optional[str] = None,
        nim_base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize NVIDIA client.

        Args:
            api_key: NVIDIA API key
            base_url: Base URL for integrate API (defaults to settings)
            genai_base_url: Base URL for GenAI API (defaults to settings)
            nim_base_url: Base URL for NIM deployment (optional)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.nvidia_api_key
        self.base_url = base_url or settings.nvidia_base_url
        self.genai_base_url = genai_base_url or settings.nvidia_genai_base_url
        self.nim_base_url = nim_base_url or getattr(settings, "nvidia_nim_base_url", "")
        self.timeout = timeout

        if not self.api_key:
            logger.warning("NVIDIA API key not configured")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def get_base_url(
        self,
        url_type: BaseURLType = BaseURLType.INTEGRATE,
        model_id: Optional[str] = None,
    ) -> str:
        """
        Get the appropriate base URL for a request.

        Args:
            url_type: Type of base URL (integrate, genai, nim)
            model_id: Optional model ID to auto-detect URL type

        Returns:
            Base URL string
        """
        # Auto-detect from model if not specified
        if model_id and url_type == BaseURLType.INTEGRATE:
            detected_type = get_base_url_type(model_id)
            if detected_type == "genai":
                url_type = BaseURLType.GENAI

        if url_type == BaseURLType.GENAI:
            return self.genai_base_url
        elif url_type == BaseURLType.NIM:
            if not self.nim_base_url:
                raise ValueError("NIM base URL not configured")
            return self.nim_base_url
        else:
            return self.base_url

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        url_type: BaseURLType = BaseURLType.INTEGRATE,
        model_id: Optional[str] = None,
        **kwargs,
    ) -> httpx.Response:
        """
        Make an HTTP request to NVIDIA API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            url_type: Base URL type
            model_id: Optional model ID for auto-detection
            **kwargs: Additional arguments for httpx request

        Returns:
            httpx.Response object
        """
        if not self.api_key:
            raise ValueError("NVIDIA API key not configured")

        base_url = self.get_base_url(url_type, model_id)
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
            # Extract NVIDIA-specific error information
            error_msg = self._extract_error_message(e)
            logger.error(f"NVIDIA API error ({e.response.status_code}): {error_msg}")
            raise Exception(f"NVIDIA API error: {error_msg}")
        except httpx.RequestError as e:
            logger.error(f"NVIDIA API request error: {e}")
            raise Exception(f"NVIDIA API request error: {str(e)}")

    def _extract_error_message(self, error: httpx.HTTPStatusError) -> str:
        """Extract error message from HTTP error response"""
        if hasattr(error, "response") and error.response is not None:
            try:
                error_data = error.response.json()
                if isinstance(error_data, dict):
                    error_obj = error_data.get("error", {})
                    if isinstance(error_obj, dict):
                        return error_obj.get("message", str(error))
                    return str(error_obj)
                return str(error_data)
            except (ValueError, AttributeError, KeyError):
                return error.response.text or str(error)
        return str(error)

    def _extract_nvidia_headers(self, response: httpx.Response) -> Dict[str, Any]:
        """
        Extract NVIDIA-specific headers from response.

        Returns:
            Dictionary with NVIDIA headers (nvcf_reqid, nvcf_status, etc.)
        """
        nvidia_headers = {}

        if hasattr(response, "headers"):
            nvcf_reqid = response.headers.get("Nvcf-Reqid")
            nvcf_status = response.headers.get("Nvcf-Status")
            nvcf_percent_complete = response.headers.get("Nvcf-Percent-Complete")

            if nvcf_reqid:
                nvidia_headers["nvcf_reqid"] = nvcf_reqid
            if nvcf_status:
                nvidia_headers["nvcf_status"] = nvcf_status
            if nvcf_percent_complete:
                nvidia_headers["nvcf_percent_complete"] = nvcf_percent_complete

        return nvidia_headers

    async def post(
        self,
        endpoint: str,
        url_type: BaseURLType = BaseURLType.INTEGRATE,
        model_id: Optional[str] = None,
        **kwargs,
    ) -> httpx.Response:
        """Make a POST request"""
        return await self._make_request("POST", endpoint, url_type, model_id, **kwargs)

    async def get(
        self,
        endpoint: str,
        url_type: BaseURLType = BaseURLType.INTEGRATE,
        model_id: Optional[str] = None,
        **kwargs,
    ) -> httpx.Response:
        """Make a GET request"""
        return await self._make_request("GET", endpoint, url_type, model_id, **kwargs)

    def stream(
        self,
        endpoint: str,
        url_type: BaseURLType = BaseURLType.INTEGRATE,
        model_id: Optional[str] = None,
        **kwargs,
    ) -> AbstractAsyncContextManager[httpx.Response]:
        """
        Create a streaming request context (async context manager yielding Response).
        """
        if not self.api_key:
            raise ValueError("NVIDIA API key not configured")

        base_url = self.get_base_url(url_type, model_id)
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        headers = self._get_headers()
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        timeout = kwargs.pop("timeout", self.timeout)

        client = httpx.AsyncClient(timeout=timeout)
        return client.stream("POST", url, headers=headers, **kwargs)

    async def health_check(self, url_type: BaseURLType = BaseURLType.INTEGRATE) -> bool:
        """
        Check if NVIDIA API is available.

        Args:
            url_type: Base URL type to check

        Returns:
            True if API is available, False otherwise
        """
        if not self.api_key:
            return False

        try:
            # Try a simple request (models endpoint if available)
            response = await self.get("models", url_type=url_type)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"NVIDIA health check failed: {e}")
            return False
