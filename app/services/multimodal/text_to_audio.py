"""
Text-to-Audio Service using HuggingFace Inference API
Supports MusicGen and other audio generation models
"""

import base64
import logging
from typing import Optional

from app.config import settings
from app.services.llm.hf_client import HuggingFaceClient

logger = logging.getLogger(__name__)


class TextToAudioService:
    """Service for generating audio/music from text prompts"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize text-to-audio service.

        Args:
            api_key: HuggingFace API key
            model: Model to use (defaults to config)
        """
        self.api_key = api_key or settings.huggingface_api_key
        self.model = model or settings.hf_text_to_audio_model
        self.client = HuggingFaceClient(api_key=self.api_key)

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        duration: float = 5.0,
        return_base64: bool = True,
    ) -> dict:
        """
        Generate audio/music from a text prompt.

        Args:
            prompt: Text description of desired audio
            model: Model to use (overrides default)
            duration: Duration of audio in seconds
            return_base64: Whether to return base64-encoded audio

        Returns:
            Dictionary with audio data and metadata
        """
        model = model or self.model

        # Build parameters
        parameters = {"duration": duration}

        try:
            # Call inference API
            response = await self.client.inference_api(
                model=model, inputs=prompt, parameters=parameters
            )

            # Handle response - typically returns audio bytes
            audio_bytes = None
            if isinstance(response, bytes):
                audio_bytes = response
            elif isinstance(response, dict):
                if "audio" in response:
                    audio_bytes = response["audio"]
                elif "generated_audio" in response:
                    audio_bytes = response["generated_audio"]

            if not audio_bytes:
                # Try list response
                if isinstance(response, list) and len(response) > 0:
                    item = response[0]
                    if isinstance(item, bytes):
                        audio_bytes = item
                    elif isinstance(item, dict) and "audio" in item:
                        audio_bytes = item["audio"]

            if not audio_bytes:
                raise ValueError("Could not extract audio from response")

            result = {
                "model": model,
                "prompt": prompt,
                "audio_base64": None,
                "audio_url": None,
            }

            if return_base64:
                if isinstance(audio_bytes, str):
                    result["audio_base64"] = audio_bytes
                else:
                    result["audio_base64"] = base64.b64encode(audio_bytes).decode(
                        "utf-8"
                    )

            return result

        except Exception as e:
            logger.error(f"Text-to-audio generation error: {e}")
            raise Exception(f"Failed to generate audio: {str(e)}")
