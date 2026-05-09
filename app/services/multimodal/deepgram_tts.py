"""
Deepgram Text-to-Speech Service
Uses Deepgram's Aura voices for high-quality speech synthesis
Supports 12 voice models with various characteristics
"""

import base64
import logging
from typing import Optional, Dict, Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class DeepgramTextToSpeechService:
    """Service for generating speech from text using Deepgram's Aura voices"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize Deepgram text-to-speech service.

        Args:
            api_key: Deepgram API key
            model: Default voice model to use (defaults to config)
            base_url: Optional custom base URL
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.deepgram_api_key
        self.model = model or settings.deepgram_default_tts_model
        self.base_url = base_url or settings.deepgram_base_url
        self.timeout = timeout

        if not self.api_key:
            logger.warning("Deepgram API key not configured")

    async def generate(
        self,
        text: str,
        model: Optional[str] = None,
        encoding: str = "mp3",
        sample_rate: int = 24000,
        return_base64: bool = True,
    ) -> dict:
        """
        Generate speech audio from text using Deepgram's Aura voices.

        Args:
            text: Text to convert to speech
            model: Voice model to use (aura-asteria-en, aura-luna-en, etc.)
            encoding: Audio encoding format (mp3, wav, opus, flac)
            sample_rate: Sample rate in Hz (24000, 48000)
            return_base64: Whether to return base64-encoded audio

        Returns:
            Dictionary with audio data and metadata
        """
        if not self.api_key:
            raise Exception("Deepgram API key not configured")

        model = model or self.model
        url = f"{self.base_url}/speak"

        # Build query parameters
        params = {"model": model, "encoding": encoding, "sample_rate": str(sample_rate)}

        # Prepare request body
        body = {"text": text}

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, params=params, json=body, headers=headers
                )
                response.raise_for_status()

                # Deepgram returns audio as binary data
                audio_bytes = response.content
                content_type = response.headers.get("content-type", "audio/mpeg")

                result = {
                    "model": model,
                    "text": text,
                    "audio_base64": None,
                    "audio_url": None,
                    "content_type": content_type,
                    "duration_ms": None,
                }

                if return_base64:
                    result["audio_base64"] = base64.b64encode(audio_bytes).decode(
                        "utf-8"
                    )

                # Try to extract duration from headers if available
                # Note: Deepgram may not always provide this
                content_length = len(audio_bytes)
                # Estimate duration based on file size (rough estimate)
                # This is approximate and depends on encoding
                if encoding == "mp3":
                    # Rough estimate: ~1KB per second for 24kHz MP3
                    estimated_duration = int((content_length / 1024) * 1000)
                    result["duration_ms"] = estimated_duration

                return result

        except httpx.HTTPError as e:
            logger.error(f"Deepgram text-to-speech API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("err_msg", str(e))
                    raise Exception(f"Deepgram text-to-speech API error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    # Response might not be JSON
                    error_text = (
                        e.response.text if hasattr(e.response, "text") else str(e)
                    )
                    raise Exception(f"Deepgram text-to-speech API error: {error_text}")
            raise Exception(f"Deepgram text-to-speech API error: {str(e)}")

    async def list_voices(self) -> list:
        """List available Deepgram voice models"""
        return [
            "aura-asteria-en",
            "aura-luna-en",
            "aura-stella-en",
            "aura-athena-en",
            "aura-hera-en",
            "aura-orion-en",
            "aura-arcas-en",
            "aura-perseus-en",
            "aura-angus-en",
            "aura-orpheus-en",
            "aura-helios-en",
            "aura-zeus-en",
        ]

    def get_voice_info(self, voice: str) -> Dict[str, Any]:
        """
        Get information about a specific voice.

        Args:
            voice: Voice model name

        Returns:
            Dictionary with voice information
        """
        voice_info = {
            "aura-asteria-en": {
                "name": "Asteria",
                "gender": "female",
                "description": "Warm and friendly female voice",
            },
            "aura-luna-en": {
                "name": "Luna",
                "gender": "female",
                "description": "Clear and professional female voice",
            },
            "aura-stella-en": {
                "name": "Stella",
                "gender": "female",
                "description": "Energetic and expressive female voice",
            },
            "aura-athena-en": {
                "name": "Athena",
                "gender": "female",
                "description": "Confident and authoritative female voice",
            },
            "aura-hera-en": {
                "name": "Hera",
                "gender": "female",
                "description": "Sophisticated and elegant female voice",
            },
            "aura-orion-en": {
                "name": "Orion",
                "gender": "male",
                "description": "Deep and resonant male voice",
            },
            "aura-arcas-en": {
                "name": "Arcas",
                "gender": "male",
                "description": "Warm and friendly male voice",
            },
            "aura-perseus-en": {
                "name": "Perseus",
                "gender": "male",
                "description": "Strong and confident male voice",
            },
            "aura-angus-en": {
                "name": "Angus",
                "gender": "male",
                "description": "Professional and clear male voice",
            },
            "aura-orpheus-en": {
                "name": "Orpheus",
                "gender": "male",
                "description": "Smooth and expressive male voice",
            },
            "aura-helios-en": {
                "name": "Helios",
                "gender": "male",
                "description": "Bright and energetic male voice",
            },
            "aura-zeus-en": {
                "name": "Zeus",
                "gender": "male",
                "description": "Powerful and authoritative male voice",
            },
        }

        return voice_info.get(
            voice, {"name": voice, "gender": "unknown", "description": "Unknown voice"}
        )
