"""
NVIDIA Vision Service
Multimodal vision models for image and video analysis
"""

import base64
import logging
from typing import Any, Dict, List, Optional, Union

from app.config import settings
from .client import NVIDIAClient, BaseURLType
from .models import get_vision_models, get_model, validate_model

logger = logging.getLogger(__name__)


class NVIDIAVisionService:
    """
    NVIDIA vision service for multimodal analysis.

    Supports:
    - Image + text analysis
    - Multi-image analysis
    - Video frame analysis
    - Structured output (JSON mode)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        base_url: Optional[str] = None,
    ):
        """
        Initialize NVIDIA vision service.

        Args:
            api_key: NVIDIA API key
            model: Default vision model
            timeout: Request timeout in seconds
            base_url: Optional custom base URL
        """
        self.client = NVIDIAClient(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout or settings.nvidia_vision_timeout,
        )
        self.default_model = model or settings.nvidia_vision_model

        if not self.client.api_key:
            logger.warning("NVIDIA API key not configured")

    def _prepare_image_content(
        self, image: Union[str, bytes], image_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Prepare image content for API request.

        Args:
            image: Base64-encoded image string or bytes
            image_url: Optional image URL

        Returns:
            Image content dictionary
        """
        if image_url:
            return {"type": "image_url", "image_url": {"url": image_url}}

        # Handle base64 image
        if isinstance(image, bytes):
            image_b64 = base64.b64encode(image).decode("utf-8")
        elif isinstance(image, str):
            # Check if already data URI
            if image.startswith("data:image"):
                image_b64 = image.split(",", 1)[1] if "," in image else image
            else:
                image_b64 = image
        else:
            raise ValueError("Image must be base64 string, bytes, or URL")

        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
        }

    async def analyze(
        self,
        prompt: str,
        image: Optional[Union[str, bytes]] = None,
        image_url: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        response_format: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze an image with text prompt.

        Args:
            prompt: Text prompt/question about the image
            image: Base64-encoded image or bytes
            image_url: Optional image URL
            model: Vision model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            response_format: Response format ("json_object" for structured output)

        Returns:
            Analysis result with text and metadata
        """
        if not self.client.api_key:
            raise Exception("NVIDIA API key not configured")

        if not image and not image_url:
            raise ValueError("Either image or image_url must be provided")

        model = model or self.default_model

        # Validate model
        if not validate_model(model):
            logger.warning(f"Model {model} not in registry, proceeding anyway")

        # Prepare image content
        image_content = self._prepare_image_content(image, image_url)

        # Build messages
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}, image_content],
            }
        ]

        # Build request payload
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        if response_format:
            payload["response_format"] = {"type": response_format}

        try:
            response = await self.client.post(
                "chat/completions",
                url_type=BaseURLType.INTEGRATE,
                model_id=model,
                json=payload,
            )

            data = response.json()

            # Extract response
            text = ""
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                text = message.get("content", "")

            # Extract NVIDIA-specific headers
            nvidia_headers = self.client._extract_nvidia_headers(response)

            result = {
                "text": text,
                "model": model,
                "usage": data.get("usage", {}),
                "finish_reason": choices[0].get("finish_reason") if choices else None,
                **nvidia_headers,
            }

            return result

        except Exception as e:
            logger.error(f"NVIDIA vision analysis error: {e}")
            raise

    async def analyze_multimodal(
        self,
        prompt: str,
        images: List[Union[str, bytes]],
        image_urls: Optional[List[str]] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
    ) -> Dict[str, Any]:
        """
        Analyze multiple images with a text prompt.

        Args:
            prompt: Text prompt/question about the images
            images: List of base64-encoded images or bytes
            image_urls: Optional list of image URLs
            model: Vision model to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Analysis result with text and metadata
        """
        if not self.client.api_key:
            raise Exception("NVIDIA API key not configured")

        if not images and not image_urls:
            raise ValueError("Either images or image_urls must be provided")

        model = model or self.default_model

        # Validate model
        if not validate_model(model):
            logger.warning(f"Model {model} not in registry, proceeding anyway")

        # Build content array with text and all images
        content = [{"type": "text", "text": prompt}]

        # Add images
        if image_urls:
            for url in image_urls:
                content.append({"type": "image_url", "image_url": {"url": url}})

        if images:
            for image in images:
                image_content = self._prepare_image_content(image)
                content.append(image_content)

        # Build messages
        messages = [{"role": "user", "content": content}]

        # Build request payload
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            response = await self.client.post(
                "chat/completions",
                url_type=BaseURLType.INTEGRATE,
                model_id=model,
                json=payload,
            )

            data = response.json()

            # Extract response
            text = ""
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                text = message.get("content", "")

            # Extract NVIDIA-specific headers
            nvidia_headers = self.client._extract_nvidia_headers(response)

            result = {
                "text": text,
                "model": model,
                "usage": data.get("usage", {}),
                "finish_reason": choices[0].get("finish_reason") if choices else None,
                **nvidia_headers,
            }

            return result

        except Exception as e:
            logger.error(f"NVIDIA multimodal analysis error: {e}")
            raise

    async def analyze_video_frames(
        self,
        prompt: str,
        frames: List[Union[str, bytes]],
        frame_urls: Optional[List[str]] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Analyze video frames.

        Args:
            prompt: Text prompt about the video frames
            frames: List of frame images (base64 or bytes)
            frame_urls: Optional list of frame URLs
            model: Vision model to use
            max_tokens: Maximum tokens in response

        Returns:
            Analysis result
        """
        # Use multimodal analysis for video frames
        return await self.analyze_multimodal(
            prompt=prompt,
            images=frames,
            image_urls=frame_urls,
            model=model,
            max_tokens=max_tokens,
        )

    async def health_check(self) -> bool:
        """Check if NVIDIA vision API is available"""
        return await self.client.health_check(BaseURLType.INTEGRATE)

    async def list_models(self) -> List[str]:
        """List all available vision models"""
        return get_vision_models()

    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a vision model.

        Args:
            model_id: Model identifier

        Returns:
            Model metadata dictionary or None if not found
        """
        model = get_model(model_id)
        if not model or not model.vision:
            return None

        return {
            "id": model.id,
            "category": model.category.value,
            "provider": model.provider.value,
            "capabilities": list(model.capabilities),
            "context_length": model.context_length,
            "description": model.description,
        }
