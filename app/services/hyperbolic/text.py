"""
Hyperbolic Text Generation Service
Handles text completion requests
"""

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from .client import HyperbolicClient
from .models import TEXT_MODELS

logger = logging.getLogger(__name__)


class HyperbolicTextService:
    """Service for text generation using Hyperbolic API"""

    def __init__(self, client: Optional[HyperbolicClient] = None):
        """
        Initialize text service.

        Args:
            client: Optional HyperbolicClient instance
        """
        self.client = client or HyperbolicClient()

    async def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 0.9,
        presence_penalty: float = 0.0,
        stream: bool = False,
        stop: Optional[List[str]] = None,
        **kwargs,
    ) -> Union[Dict[str, Any], AsyncIterator[str]]:
        """
        Send chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model identifier
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            presence_penalty: Presence penalty (-2.0 to 2.0)
            stream: Whether to stream the response
            stop: Stop sequences
            **kwargs: Additional parameters

        Returns:
            Response dict or streaming iterator
        """
        if model not in TEXT_MODELS:
            logger.warning(f"Model {model} not in known text models, proceeding anyway")

        payload = {
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "presence_penalty": presence_penalty,
            "stream": stream,
            **kwargs,
        }

        if stop:
            payload["stop"] = stop

        if stream:
            return self._stream_completion(payload)
        else:
            return await self.client.post("/chat/completions", payload)

    async def _stream_completion(self, payload: Dict[str, Any]) -> AsyncIterator[str]:
        """
        Stream completion response.

        Args:
            payload: Request payload

        Yields:
            Text chunks as they arrive
        """
        response = await self.client.post_stream("/chat/completions", payload)

        buffer = ""
        async for chunk in response.aiter_text():
            buffer += chunk

            # Process Server-Sent Events (SSE) format
            lines = buffer.split("\n")
            buffer = lines[-1]  # Keep incomplete line in buffer

            for line in lines[:-1]:
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue

                # Extract JSON data
                data_str = line[6:]  # Remove "data: " prefix

                # Check for [DONE] marker
                if data_str == "[DONE]":
                    return

                try:
                    data = json.loads(data_str)
                    choices = data.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse SSE data: {data_str}")
                    continue
