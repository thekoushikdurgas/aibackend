"""
Deep Infra Image Generation Service
Supports FLUX and SDXL models for high-quality image generation
"""

import base64
import logging
from typing import Optional, Dict, Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class DeepInfraImageGenerator:
    """
    Image generation service using Deep Infra's direct inference endpoints.
    Supports FLUX-1-dev, FLUX-1-schnell, and SDXL-turbo models.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 180.0,
        inference_base_url: Optional[str] = None,
    ):
        """
        Initialize Deep Infra image generator.

        Args:
            api_key: Deep Infra API key
            model: Default image generation model
            timeout: Request timeout in seconds (longer for image generation)
            inference_base_url: Base URL for direct inference endpoints
        """
        self.api_key = api_key or getattr(settings, "deepinfra_api_key", None)
        self.default_model = model or getattr(
            settings, "deepinfra_image_model", "black-forest-labs/FLUX-1-schnell"
        )
        self.timeout = timeout
        self.inference_base_url = inference_base_url or getattr(
            settings, "deepinfra_inference_base_url", "https://api.deepinfra.com/v1"
        )

        if not self.api_key:
            logger.warning("Deep Infra API key not configured for image generation")

    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        num_inference_steps: Optional[int] = None,
        guidance_scale: Optional[float] = None,
        seed: Optional[int] = None,
        return_base64: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the image to generate
            model: Model to use (FLUX-1-dev, FLUX-1-schnell, or sdxl-turbo)
            negative_prompt: What to avoid in the image
            num_inference_steps: Number of inference steps (model-dependent)
            guidance_scale: Guidance scale for generation (model-dependent)
            seed: Random seed for reproducibility
            return_base64: If True, return base64 string; if False, return bytes

        Returns:
            Dictionary with image data, model, and metadata
        """
        if not self.api_key:
            raise Exception("Deep Infra API key not configured")

        model = model or self.default_model

        # Build request payload
        payload: Dict[str, Any] = {"prompt": prompt}

        # Add optional parameters based on model
        if negative_prompt:
            payload["negative_prompt"] = negative_prompt

        if num_inference_steps is not None:
            payload["num_inference_steps"] = num_inference_steps

        if guidance_scale is not None:
            payload["guidance_scale"] = guidance_scale

        if seed is not None:
            payload["seed"] = seed

        # Construct URL
        url = f"{self.inference_base_url}/{model}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                # Check content type
                content_type = response.headers.get("content-type", "")

                if "image" in content_type:
                    # Binary image data
                    image_bytes = response.content

                    result = {
                        "image": (
                            base64.b64encode(image_bytes).decode("utf-8")
                            if return_base64
                            else image_bytes
                        ),
                        "content_type": content_type,
                        "model": model,
                        "format": "base64" if return_base64 else "bytes",
                    }

                    return result
                else:
                    # JSON response (some models return JSON with image data)
                    data = response.json()

                    # Handle different response formats
                    if "image" in data:
                        image_data = data["image"]
                        if isinstance(image_data, str):
                            # Base64 string
                            result = {
                                "image": (
                                    image_data
                                    if return_base64
                                    else base64.b64decode(image_data)
                                ),
                                "content_type": "image/png",
                                "model": model,
                                "format": "base64" if return_base64 else "bytes",
                            }
                        else:
                            result = {
                                "image": image_data,
                                "model": model,
                                "format": "base64" if return_base64 else "bytes",
                            }
                    else:
                        # Return full response
                        result = {"data": data, "model": model}

                    return result

        except httpx.HTTPError as e:
            logger.error(f"Deep Infra image generation error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"Deep Infra image generation error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"Deep Infra image generation error: {str(e)}")

    async def generate_image_bytes(
        self, prompt: str, model: Optional[str] = None, **kwargs
    ) -> bytes:
        """
        Generate image and return as bytes.

        Args:
            prompt: Text description
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            Image bytes
        """
        result = await self.generate_image(
            prompt=prompt, model=model, return_base64=False, **kwargs
        )

        if isinstance(result.get("image"), bytes):
            return result["image"]
        elif isinstance(result.get("image"), str):
            # Decode base64
            return base64.b64decode(result["image"])
        else:
            raise Exception("Unexpected image format in response")

    async def generate_image_base64(
        self, prompt: str, model: Optional[str] = None, **kwargs
    ) -> str:
        """
        Generate image and return as base64 string.

        Args:
            prompt: Text description
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            Base64-encoded image string
        """
        result = await self.generate_image(
            prompt=prompt, model=model, return_base64=True, **kwargs
        )

        if isinstance(result.get("image"), str):
            return result["image"]
        else:
            # Encode bytes to base64
            return base64.b64encode(result["image"]).decode("utf-8")

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of available image generation models with descriptions.

        Returns:
            Dictionary mapping model names to metadata
        """
        return {
            "black-forest-labs/FLUX-1-dev": {
                "name": "FLUX-1-dev",
                "description": "High-quality image generation, slower but best quality",
                "recommended_steps": 50,
                "guidance_scale": 3.5,
            },
            "black-forest-labs/FLUX-1-schnell": {
                "name": "FLUX-1-schnell",
                "description": "Fast image generation with good quality",
                "recommended_steps": 4,
                "guidance_scale": 3.5,
            },
            "stabilityai/sdxl-turbo": {
                "name": "SDXL Turbo",
                "description": "Ultra-fast image generation",
                "recommended_steps": 1,
                "guidance_scale": 0.0,
            },
        }
