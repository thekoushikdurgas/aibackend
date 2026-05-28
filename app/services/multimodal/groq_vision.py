"""
Groq Vision Service
Uses Groq's vision models for image analysis and multimodal chat
"""

import base64
import logging
from io import BytesIO
from typing import Any, Dict, List, Optional, Union


from app.config import settings
from app.services.llm.groq import GroqProvider

logger = logging.getLogger(__name__)


class GroqVisionService:
    """Service for vision analysis using Groq's vision models"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize Groq vision service.

        Args:
            api_key: Groq API key
            default_model: Default vision model (defaults to llama-3.2-11b-vision-preview)
            base_url: Optional custom base URL
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.groq_api_key
        self.default_model = default_model or settings.groq_vision_model
        self.base_url = base_url or settings.groq_base_url
        self.timeout = timeout

        # Initialize Groq provider for API calls
        self.groq_provider = GroqProvider(
            api_key=self.api_key,
            model=self.default_model,
            base_url=self.base_url,
            timeout=self.timeout,
        )

        if not self.api_key:
            logger.warning("Groq API key not configured")

    def _prepare_image(self, image: Union[str, bytes, BytesIO]) -> str:
        """
        Prepare image for API - convert to base64 data URL if needed.

        Args:
            image: Image URL, bytes, BytesIO, or base64 string

        Returns:
            Image URL or base64 data URL
        """
        if isinstance(image, bytes):
            image_b64 = base64.b64encode(image).decode("utf-8")
            return f"data:image/jpeg;base64,{image_b64}"
        elif isinstance(image, BytesIO):
            image_bytes = image.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            return f"data:image/jpeg;base64,{image_b64}"
        elif isinstance(image, str):
            if image.startswith("http://") or image.startswith("https://"):
                # URL - return as is
                return image
            elif image.startswith("data:image"):
                # Already a data URL
                return image
            else:
                # Assume base64 string
                return f"data:image/jpeg;base64,{image}"
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

    async def analyze_image(
        self,
        image: Union[str, bytes, BytesIO],
        prompt: str = "What's in this image?",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """
        Analyze a single image with a text prompt.

        Args:
            image: Image URL, bytes, BytesIO, or base64 string
            prompt: Text prompt describing what to analyze
            model: Vision model to use (defaults to llama-3.2-11b-vision-preview)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Dictionary with analysis text, model, and usage info
        """
        if not self.api_key:
            raise Exception("Groq API key not configured")

        model = model or self.default_model

        # Prepare image
        image_url = self._prepare_image(image)

        # Use GroqProvider's vision method
        from app.services.llm.base import LLMConfig

        config = LLMConfig(model=model, temperature=temperature, max_tokens=max_tokens)

        response = await self.groq_provider.generate_with_vision(
            prompt=prompt, images=[image_url], config=config
        )

        return {
            "text": response.text,
            "model": response.model,
            "usage": response.usage,
            "finish_reason": response.finish_reason,
            "raw_response": response.raw_response,
        }

    async def analyze_multiple_images(
        self,
        images: List[Union[str, bytes, BytesIO]],
        prompt: str = "What's in these images?",
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """
        Analyze multiple images with a single prompt.

        Args:
            images: List of image URLs, bytes, BytesIO, or base64 strings
            prompt: Text prompt describing what to analyze
            model: Vision model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Dictionary with analysis text, model, and usage info
        """
        if not self.api_key:
            raise Exception("Groq API key not configured")

        model = model or self.default_model

        # Prepare all images
        image_urls = [self._prepare_image(img) for img in images]

        from app.services.llm.base import LLMConfig

        config = LLMConfig(model=model, temperature=temperature, max_tokens=max_tokens)

        response = await self.groq_provider.generate_with_vision(
            prompt=prompt, images=image_urls, config=config
        )

        return {
            "text": response.text,
            "model": response.model,
            "usage": response.usage,
            "finish_reason": response.finish_reason,
            "image_count": len(images),
            "raw_response": response.raw_response,
        }

    async def extract_image_info(
        self, image: Union[str, bytes, BytesIO], extract_type: str = "description"
    ) -> Dict[str, Any]:
        """
        Extract specific information from an image.

        Args:
            image: Image URL, bytes, BytesIO, or base64 string
            extract_type: Type of extraction - "description", "objects", "text", "analysis"

        Returns:
            Dictionary with extracted information
        """
        prompts = {
            "description": "Provide a detailed description of this image, including all visible elements, colors, composition, and context.",
            "objects": "List all objects, people, animals, and items visible in this image. Be specific about their positions and characteristics.",
            "text": "Extract all text visible in this image. Include any signs, labels, captions, or written content.",
            "analysis": "Analyze this image comprehensively. Describe what you see, identify key elements, interpret the context, and provide insights about the image's purpose or meaning.",
        }

        prompt = prompts.get(extract_type, prompts["description"])

        result = await self.analyze_image(image=image, prompt=prompt, max_tokens=2048)

        return {
            "extract_type": extract_type,
            "information": result["text"],
            "model": result["model"],
            "usage": result["usage"],
        }

    async def list_models(self) -> List[str]:
        """List available vision models"""
        return ["llama-3.2-11b-vision-preview", "llama-3.2-90b-vision-preview"]
