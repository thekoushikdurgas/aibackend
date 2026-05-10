"""
Image-to-Text Service using HuggingFace Inference API
Supports BLIP, GPT-4V, and other vision-language models
"""

import base64
import logging
from typing import Any, Optional, Union

from app.config import settings
from app.services.llm.hf_client import HuggingFaceClient

logger = logging.getLogger(__name__)


class ImageToTextService:
    """Service for generating text descriptions from images"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize image-to-text service.

        Args:
            api_key: HuggingFace API key
            model: Model to use (defaults to config)
        """
        self.api_key = api_key or settings.huggingface_api_key
        self.model = model or settings.hf_image_to_text_model
        self.client = HuggingFaceClient(api_key=self.api_key)

    async def generate(
        self,
        image: Union[str, bytes],
        model: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> dict:
        """
        Generate text description from an image.

        Args:
            image: Image URL, base64 string, or bytes
            model: Model to use (overrides default)
            prompt: Optional prompt/question about the image

        Returns:
            Dictionary with generated text and metadata
        """
        model = model or self.model

        # Prepare inputs (HF accepts str or small dict for VQA-style prompts)
        inputs: str | dict[str, Any]
        if isinstance(image, bytes):
            # Convert bytes to base64
            image_b64 = base64.b64encode(image).decode("utf-8")
            inputs = f"data:image/jpeg;base64,{image_b64}"
        elif image.startswith("data:image"):
            # Already base64 data URL
            inputs = image
        elif image.startswith("http://") or image.startswith("https://"):
            # Image URL
            inputs = image
        else:
            # Assume base64 string
            if not image.startswith("data:"):
                inputs = f"data:image/jpeg;base64,{image}"
            else:
                inputs = image

        # Add prompt if provided
        if prompt:
            inputs = {"image": inputs, "text": prompt}

        try:
            # Call inference API
            response = await self.client.inference_api(model=model, inputs=inputs)

            # Parse response
            text = ""
            if isinstance(response, list):
                if len(response) > 0:
                    item = response[0]
                    if isinstance(item, dict):
                        text = item.get("generated_text", "")
                    elif isinstance(item, str):
                        text = item
            elif isinstance(response, dict):
                text = response.get("generated_text", response.get("text", ""))
            elif isinstance(response, str):
                text = response

            return {
                "text": text,
                "model": model,
                "confidence": None,  # Some models don't provide confidence
            }

        except Exception as e:
            logger.error(f"Image-to-text generation error: {e}")
            raise Exception(f"Failed to generate text from image: {str(e)}")
