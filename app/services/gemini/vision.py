"""
Gemini Vision/Multimodal Service
"""

import base64
import logging
from typing import Any, Dict, List, Optional, Union

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class GeminiVisionService:
    """
    Service for vision/multimodal analysis using Gemini API.
    Supports image understanding with text prompts.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize Gemini vision service.

        Args:
            api_key: Gemini API key
            model: Vision model to use
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_vision_model
        self.timeout = timeout
        self.base_url = settings.gemini_base_url

        if not self.api_key:
            logger.warning("Gemini API key not configured")

    def _prepare_image_part(self, image: Union[str, bytes]) -> Dict[str, Any]:
        """
        Prepare image part for Gemini API.

        Args:
            image: Image URL, base64 string, or bytes

        Returns:
            Image part dictionary
        """
        if isinstance(image, bytes):
            # Convert bytes to base64
            image_b64 = base64.b64encode(image).decode("utf-8")
            return {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}}
        elif image.startswith("data:image"):
            # Base64 data URL
            parts = image.split(",", 1)
            mime_type = parts[0].split(":")[1].split(";")[0]
            data = parts[1]
            return {"inline_data": {"mime_type": mime_type, "data": data}}
        elif image.startswith("http://") or image.startswith("https://"):
            # Image URL
            return {"file_data": {"file_uri": image, "mime_type": "image/jpeg"}}
        else:
            # Assume base64 string
            return {"inline_data": {"mime_type": "image/jpeg", "data": image}}

    async def analyze_image(
        self,
        image: Union[str, bytes],
        prompt: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze an image with a text prompt.

        Args:
            image: Image URL, base64 string, or bytes
            prompt: Text prompt/question about the image
            config: Optional generation config

        Returns:
            Analysis response with text and metadata
        """
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

        # Prepare image part
        image_part = self._prepare_image_part(image)

        # Build contents
        contents = [{"role": "user", "parts": [image_part, {"text": prompt}]}]

        payload = {"contents": contents, "generationConfig": config or {}}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                # Extract text from response
                text = ""
                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")

                return {
                    "text": text,
                    "model": self.model,
                    "usage": data.get("usageMetadata", {}),
                    "raw_response": data,
                }

        except httpx.HTTPError as e:
            logger.error(f"Gemini vision API error: {e}")
            raise Exception(f"Gemini vision API error: {str(e)}")

    async def analyze_images(
        self,
        images: List[Union[str, bytes]],
        prompt: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze multiple images with a text prompt.

        Args:
            images: List of images (URLs, base64 strings, or bytes)
            prompt: Text prompt/question about the images
            config: Optional generation config

        Returns:
            Analysis response
        """
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"

        # Prepare image parts
        parts = []
        for image in images:
            parts.append(self._prepare_image_part(image))
        parts.append({"text": prompt})

        # Build contents
        contents = [{"role": "user", "parts": parts}]

        payload = {"contents": contents, "generationConfig": config or {}}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                # Extract text from response
                text = ""
                candidates = data.get("candidates", [])
                if candidates:
                    content = candidates[0].get("content", {})
                    parts = content.get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")

                return {
                    "text": text,
                    "model": self.model,
                    "usage": data.get("usageMetadata", {}),
                    "raw_response": data,
                }

        except httpx.HTTPError as e:
            logger.error(f"Gemini vision API error: {e}")
            raise Exception(f"Gemini vision API error: {str(e)}")
