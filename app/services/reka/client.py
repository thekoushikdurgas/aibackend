"""
Reka AI Service Client
Standalone service for Reka AI API interactions
"""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.config import settings
from .model_registry import RekaModelRegistry

logger = logging.getLogger(__name__)


class RekaService:
    """
    Standalone service for Reka AI API interactions.
    Provides direct access to Reka AI endpoints.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize Reka service.

        Args:
            api_key: Reka AI API key
            base_url: Reka AI API base URL
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.reka_api_key
        self.base_url = base_url or settings.reka_base_url
        self.timeout = timeout
        self.model_registry = RekaModelRegistry(api_key=api_key, base_url=base_url)

        if not self.api_key:
            logger.warning("Reka AI API key not configured")

    def _build_headers(self) -> Dict[str, str]:
        """Build request headers"""
        headers = {"X-Api-Key": self.api_key, "Content-Type": "application/json"}
        return headers

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "reka-flash-3",
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send a chat completion request.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model identifier (default: reka-flash-3)
            stream: Whether to stream the response
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Response dictionary with id, model, usage, and responses
        """
        if not self.api_key:
            raise ValueError("Reka AI API key not configured")

        url = f"{self.base_url}/chat"
        headers = self._build_headers()

        payload = {"messages": messages, "model": model, "stream": stream}

        # Add optional parameters
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Reka AI API error: {e.response.status_code} - {e.response.text}"
            )
            raise
        except Exception as e:
            logger.error(f"Reka AI request error: {e}")
            raise

    async def stream_chat(
        self, messages: List[Dict[str, str]], model: str = "reka-flash-3", **kwargs
    ) -> AsyncIterator[str]:
        """
        Stream a chat completion response.

        Args:
            messages: List of message dictionaries
            model: Model identifier
            **kwargs: Additional parameters

        Yields:
            Text chunks as they arrive
        """
        if not self.api_key:
            raise ValueError("Reka AI API key not configured")

        url = f"{self.base_url}/chat"
        headers = self._build_headers()

        payload = {"messages": messages, "model": model, "stream": True}

        # Add optional parameters
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            payload["max_tokens"] = kwargs["max_tokens"]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", url, headers=headers, json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            # Parse SSE format if applicable
                            if line.startswith("data: "):
                                data = line[6:]
                                if data == "[DONE]":
                                    break
                                try:
                                    import json

                                    chunk = json.loads(data)
                                    # Extract content from response
                                    if "responses" in chunk and chunk["responses"]:
                                        content = (
                                            chunk["responses"][0]
                                            .get("message", {})
                                            .get("content", "")
                                        )
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue
                            else:
                                yield line
        except Exception as e:
            logger.error(f"Reka AI stream error: {e}")
            raise

    async def list_models(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        List all available models.

        Args:
            force_refresh: Force refresh of model cache

        Returns:
            List of model dictionaries
        """
        return await self.model_registry.fetch_models(force_refresh=force_refresh)

    async def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific model.

        Args:
            model_id: Model identifier

        Returns:
            Model dictionary or None if not found
        """
        return await self.model_registry.get_model(model_id)

    async def health_check(self) -> bool:
        """
        Check if the service is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            models = await self.list_models()
            return len(models) > 0
        except Exception as e:
            logger.error(f"Reka AI health check failed: {e}")
            return False
