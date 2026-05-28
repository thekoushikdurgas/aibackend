"""
Groq Speech-to-Text Service
Uses Groq's Whisper models for ultra-fast transcription
"""

import base64
import logging
from io import BytesIO
from typing import List, Optional, Union

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class GroqSpeechToTextService:
    """Service for transcribing audio to text using Groq's Whisper models"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize Groq speech-to-text service.

        Args:
            api_key: Groq API key
            model: Model to use (defaults to whisper-large-v3-turbo)
            base_url: Optional custom base URL
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.groq_api_key
        self.model = model or "whisper-large-v3-turbo"
        self.base_url = base_url or settings.groq_base_url
        self.timeout = timeout

        if not self.api_key:
            logger.warning("Groq API key not configured")

    async def transcribe(
        self,
        audio: Union[str, bytes, BytesIO],
        model: Optional[str] = None,
        language: Optional[str] = None,
        temperature: float = 0.0,
        response_format: str = "json",
    ) -> dict:
        """
        Transcribe audio to text using Groq's Whisper API.

        Args:
            audio: Audio file path, URL, bytes, BytesIO, or base64 string
            model: Model to use (whisper-large-v3, whisper-large-v3-turbo, distil-whisper-large-v3-en)
            language: Language code (e.g., "en", "es") - optional, auto-detected if not provided
            temperature: Sampling temperature (0.0 for deterministic)
            response_format: Response format - "json", "text", "srt", "vtt", "verbose_json"

        Returns:
            Dictionary with transcription and metadata
        """
        if not self.api_key:
            raise Exception("Groq API key not configured")

        model = model or self.model
        url = f"{self.base_url}/audio/transcriptions"

        # Prepare audio file
        audio_file = None
        if isinstance(audio, bytes):
            audio_file = ("audio.wav", audio, "audio/wav")
        elif isinstance(audio, BytesIO):
            audio_bytes = audio.read()
            audio_file = ("audio.wav", audio_bytes, "audio/wav")
        elif isinstance(audio, str):
            if audio.startswith("http://") or audio.startswith("https://"):
                # URL - Groq API doesn't support URLs directly, need to download first
                async with httpx.AsyncClient() as client:
                    response = await client.get(audio)
                    response.raise_for_status()
                    audio_file = ("audio.wav", response.content, "audio/wav")
            elif audio.startswith("data:audio"):
                # Base64 data URL
                header, encoded = audio.split(",", 1)
                audio_bytes = base64.b64decode(encoded)
                audio_file = ("audio.wav", audio_bytes, "audio/wav")
            else:
                # Assume base64 string
                audio_bytes = base64.b64decode(audio)
                audio_file = ("audio.wav", audio_bytes, "audio/wav")
        else:
            raise ValueError(
                "Invalid audio input type. Expected bytes, BytesIO, or string (URL/base64)"
            )

        # Prepare form data
        files = {"file": audio_file}

        data = {
            "model": model,
            "temperature": str(temperature),
            "response_format": response_format,
        }

        if language:
            data["language"] = language

        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, files=files, data=data, headers=headers
                )
                response.raise_for_status()

                # Parse response based on format
                if response_format == "json":
                    result_data = response.json()
                    return {
                        "text": result_data.get("text", ""),
                        "model": model,
                        "language": language or result_data.get("language"),
                        "raw_response": result_data,
                    }
                elif response_format == "text":
                    return {"text": response.text, "model": model, "language": language}
                elif response_format in ["srt", "vtt"]:
                    return {
                        "text": response.text,
                        "format": response_format,
                        "model": model,
                        "language": language,
                    }
                elif response_format == "verbose_json":
                    result_data = response.json()
                    return {
                        "text": result_data.get("text", ""),
                        "model": model,
                        "language": result_data.get("language", language),
                        "duration": result_data.get("duration"),
                        "words": result_data.get("words", []),
                        "segments": result_data.get("segments", []),
                        "raw_response": result_data,
                    }
                else:
                    # Default to JSON parsing
                    result_data = response.json()
                    return {
                        "text": result_data.get("text", ""),
                        "model": model,
                        "language": language,
                        "raw_response": result_data,
                    }

        except httpx.HTTPError as e:
            logger.error(f"Groq speech-to-text API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"Groq speech-to-text API error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"Groq speech-to-text API error: {str(e)}")

    async def transcribe_batch(
        self,
        audio_files: List[Union[str, bytes, BytesIO]],
        model: Optional[str] = None,
        language: Optional[str] = None,
        temperature: float = 0.0,
        response_format: str = "json",
    ) -> List[dict]:
        """
        Transcribe multiple audio files in batch.

        Args:
            audio_files: List of audio files (URLs, bytes, BytesIO, or base64 strings)
            model: Model to use
            language: Language code
            temperature: Sampling temperature
            response_format: Response format

        Returns:
            List of transcription results
        """
        if not self.api_key:
            raise Exception("Groq API key not configured")

        results = []
        for audio in audio_files:
            try:
                result = await self.transcribe(
                    audio=audio,
                    model=model,
                    language=language,
                    temperature=temperature,
                    response_format=response_format,
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Batch transcription error for file: {e}")
                results.append(
                    {"error": str(e), "text": "", "model": model or self.model}
                )

        return results

    async def list_models(self) -> list:
        """List available Whisper models on Groq"""
        return [
            "whisper-large-v3",
            "whisper-large-v3-turbo",
            "distil-whisper-large-v3-en",
        ]
