"""
Hyperbolic Vision Service
Handles multimodal vision completion requests
"""

import logging
from typing import Any, Dict, List, Optional

from .client import HyperbolicClient
from .models import VISION_MODELS

logger = logging.getLogger(__name__)


class HyperbolicVisionService:
    """Service for vision/multimodal completion using Hyperbolic API"""

    def __init__(self, client: Optional[HyperbolicClient] = None):
        """
        Initialize vision service.

        Args:
            client: Optional HyperbolicClient instance
        """
        self.client = client or HyperbolicClient()

    async def vision_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Send vision completion request with multimodal content.

        Args:
            messages: List of message dicts with multimodal content
                     Content can be a list with text and image_url items
            model: Vision model identifier
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            **kwargs: Additional parameters

        Returns:
            Response dict with completion
        """
        if model not in VISION_MODELS:
            logger.warning(
                f"Model {model} not in known vision models, proceeding anyway"
            )

        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": False,
            **kwargs,
        }

        return await self.client.post("/chat/completions", payload)

    def prepare_multimodal_message(
        self, text: str, image_urls: List[str]
    ) -> Dict[str, Any]:
        """
        Prepare a multimodal message with text and images.

        Args:
            text: Text content
            image_urls: List of image URLs

        Returns:
            Message dict with multimodal content
        """
        content = [{"type": "text", "text": text}]

        for image_url in image_urls:
            content.append({"type": "image_url", "image_url": {"url": image_url}})

        return {"role": "user", "content": content}
