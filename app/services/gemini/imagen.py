"""
Imagen-4 Image Generation Service
"""

import logging
from typing import Any, Dict, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class ImagenService:
    """
    Service for image generation using Imagen-4 API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 300.0,
    ):
        """
        Initialize Imagen service.

        Args:
            api_key: Gemini API key
            model: Imagen model to use
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_imagen_model
        self.timeout = timeout
        self.base_url = settings.gemini_base_url

        if not self.api_key:
            logger.warning("Gemini API key not configured")

    async def generate(
        self,
        prompt: str,
        aspect_ratio: Optional[str] = None,
        number_of_images: int = 1,
        safety_filter_level: Optional[str] = None,
        person_generation: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate image from text prompt.

        Args:
            prompt: Text prompt describing the image
            aspect_ratio: Image aspect ratio (e.g., "1:1", "16:9")
            number_of_images: Number of images to generate
            safety_filter_level: Safety filter level
            person_generation: Person generation setting
            seed: Random seed for reproducibility

        Returns:
            Generated image response with image data/URL
        """
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        url = f"{self.base_url}/models/{self.model}:predict"
        headers = {"x-goog-api-key": self.api_key}

        payload = {"instances": [{"prompt": prompt}], "parameters": {}}

        if aspect_ratio:
            payload["parameters"]["aspectRatio"] = aspect_ratio
        if number_of_images:
            payload["parameters"]["numberOfImages"] = number_of_images
        if safety_filter_level:
            payload["parameters"]["safetyFilterLevel"] = safety_filter_level
        if person_generation:
            payload["parameters"]["personGeneration"] = person_generation
        if seed is not None:
            payload["parameters"]["seed"] = seed

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                # Extract image data
                predictions = data.get("predictions", [])
                images = []
                for pred in predictions:
                    if "bytesBase64Encoded" in pred:
                        images.append(
                            {
                                "base64": pred["bytesBase64Encoded"],
                                "mimeType": pred.get("mimeType", "image/png"),
                            }
                        )
                    elif "imageUri" in pred:
                        images.append(
                            {
                                "uri": pred["imageUri"],
                                "mimeType": pred.get("mimeType", "image/png"),
                            }
                        )

                return {
                    "images": images,
                    "model": self.model,
                    "prompt": prompt,
                    "raw_response": data,
                }

        except httpx.HTTPError as e:
            logger.error(f"Imagen API error: {e}")
            raise Exception(f"Imagen API error: {str(e)}")
