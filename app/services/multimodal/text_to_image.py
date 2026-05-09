"""
Text-to-Image Service using HuggingFace Inference API
Supports FLUX.1, Stable Diffusion, and other image generation models
"""

import base64
import logging
from typing import Optional

from app.config import settings
from app.services.llm.hf_client import HuggingFaceClient

logger = logging.getLogger(__name__)


class TextToImageService:
    """Service for generating images from text prompts"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize text-to-image service.

        Args:
            api_key: HuggingFace API key
            model: Model to use (defaults to config)
        """
        self.api_key = api_key or settings.huggingface_api_key
        self.model = model or settings.hf_text_to_image_model
        self.client = HuggingFaceClient(api_key=self.api_key)

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        negative_prompt: Optional[str] = None,
        num_inference_steps: int = 50,
        guidance_scale: float = 7.5,
        return_base64: bool = True,
    ) -> dict:
        """
        Generate an image from a text prompt.

        Args:
            prompt: Text description of the image
            model: Model to use (overrides default)
            negative_prompt: What to avoid in the image
            num_inference_steps: Number of denoising steps
            guidance_scale: How closely to follow the prompt
            return_base64: Whether to return base64-encoded image

        Returns:
            Dictionary with image data and metadata
        """
        model = model or self.model

        # Build parameters
        parameters = {
            "num_inference_steps": num_inference_steps,
            "guidance_scale": guidance_scale,
        }

        if negative_prompt:
            parameters["negative_prompt"] = negative_prompt

        try:
            # Call inference API
            response = await self.client.inference_api(
                model=model, inputs=prompt, parameters=parameters
            )

            # Handle response - can be bytes (image) or dict with image data
            image_bytes = None
            if isinstance(response, bytes):
                image_bytes = response
            elif isinstance(response, dict):
                # Some models return dict with image data
                if "image" in response:
                    image_bytes = response["image"]
                elif "generated_image" in response:
                    image_bytes = response["generated_image"]

            if not image_bytes:
                # Try to get from list response
                if isinstance(response, list) and len(response) > 0:
                    item = response[0]
                    if isinstance(item, dict) and "generated_image" in item:
                        image_bytes = item["generated_image"]
                    elif isinstance(item, bytes):
                        image_bytes = item

            if not image_bytes:
                raise ValueError("Could not extract image from response")

            result = {
                "model": model,
                "prompt": prompt,
                "image_base64": None,
                "image_url": None,
            }

            if return_base64:
                # Encode to base64
                if isinstance(image_bytes, str):
                    # Already base64 string
                    result["image_base64"] = image_bytes
                else:
                    result["image_base64"] = base64.b64encode(image_bytes).decode(
                        "utf-8"
                    )

            return result

        except Exception as e:
            logger.error(f"Text-to-image generation error: {e}")
            raise Exception(f"Failed to generate image: {str(e)}")
