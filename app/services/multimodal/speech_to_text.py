"""
Speech-to-Text Service using HuggingFace Inference API
Supports Whisper and other speech recognition models
"""

import base64
import logging
from typing import Optional, Union

from app.config import settings
from app.services.llm.hf_client import HuggingFaceClient

logger = logging.getLogger(__name__)


class SpeechToTextService:
    """Service for transcribing audio to text"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize speech-to-text service.

        Args:
            api_key: HuggingFace API key
            model: Model to use (defaults to config)
        """
        self.api_key = api_key or settings.huggingface_api_key
        self.model = model or settings.hf_speech_to_text_model
        self.client = HuggingFaceClient(api_key=self.api_key)

    async def transcribe(
        self,
        audio: Union[str, bytes],
        model: Optional[str] = None,
        language: Optional[str] = None,
        return_timestamps: bool = False,
    ) -> dict:
        """
        Transcribe audio to text.

        Args:
            audio: Audio file path, URL, bytes, or base64 string
            model: Model to use (overrides default)
            language: Language code (e.g., "en", "es")
            return_timestamps: Whether to return word-level timestamps

        Returns:
            Dictionary with transcription and metadata
        """
        model = model or self.model

        # Prepare audio data
        audio_bytes = None
        if isinstance(audio, bytes):
            audio_bytes = audio
        elif isinstance(audio, str):
            if audio.startswith("http://") or audio.startswith("https://"):
                # Audio URL - will be handled by API
                audio_bytes = None
            elif audio.startswith("data:audio"):
                # Base64 data URL
                header, encoded = audio.split(",", 1)
                audio_bytes = base64.b64decode(encoded)
            else:
                # Assume base64 string
                audio_bytes = base64.b64decode(audio)

        try:
            # Call inference API with form-data
            if audio_bytes:
                # Use form-data for binary audio
                files = {"data-binary": ("audio.wav", audio_bytes, "audio/wav")}
                response = await self.client.inference_api_formdata(
                    model=model, files=files
                )
            else:
                # Use JSON for URL
                response = await self.client.inference_api(model=model, inputs=audio)

            # Parse response
            text = ""
            language_detected = None

            if isinstance(response, dict):
                text = response.get("text", "")
                language_detected = response.get("language", language)
            elif isinstance(response, str):
                text = response

            result = {
                "text": text,
                "model": model,
                "language": language_detected or language,
            }

            if return_timestamps and isinstance(response, dict):
                result["timestamps"] = response.get("chunks", [])

            return result

        except Exception as e:
            logger.error(f"Speech-to-text transcription error: {e}")
            raise Exception(f"Failed to transcribe audio: {str(e)}")
