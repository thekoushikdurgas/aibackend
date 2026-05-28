"""
Deepgram Speech-to-Text Service
Uses Deepgram's API for high-quality speech transcription
Supports multiple models: nova-3, nova-2, enhanced, base, whisper
"""

import base64
import logging
from io import BytesIO
from typing import Optional, Union, Dict, Any, List

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class DeepgramSpeechToTextService:
    """Service for transcribing audio to text using Deepgram's API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize Deepgram speech-to-text service.

        Args:
            api_key: Deepgram API key
            model: Default model to use (defaults to config)
            base_url: Optional custom base URL
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.deepgram_api_key
        self.model = model or settings.deepgram_default_stt_model
        self.base_url = base_url or settings.deepgram_base_url
        self.timeout = timeout

        if not self.api_key:
            logger.warning("Deepgram API key not configured")

    async def transcribe(
        self,
        audio: Union[str, bytes, BytesIO],
        model: Optional[str] = None,
        language: Optional[str] = None,
        punctuate: bool = True,
        diarize: bool = False,
        smart_format: bool = True,
        detect_language: bool = False,
        return_timestamps: bool = False,
    ) -> dict:
        """
        Transcribe audio to text using Deepgram's API.

        Args:
            audio: Audio file path, URL, bytes, BytesIO, or base64 string
            model: Model to use (nova-3, nova-2, nova-2-phonecall, enhanced, base, whisper, etc.)
            language: Language code (e.g., "en", "es") - optional, auto-detected if not provided
            punctuate: Add punctuation and capitalization
            diarize: Identify speakers in the audio
            smart_format: Apply smart formatting (numbers, dates, etc.)
            detect_language: Automatically detect language
            return_timestamps: Return word-level timestamps

        Returns:
            Dictionary with transcription and metadata
        """
        if not self.api_key:
            raise Exception("Deepgram API key not configured")

        model = model or self.model
        url = f"{self.base_url}/listen"

        # Build query parameters
        params = {
            "model": model,
            "punctuate": "true" if punctuate else "false",
            "diarize": "true" if diarize else "false",
            "smart_format": "true" if smart_format else "false",
            "detect_language": "true" if detect_language else "false",
        }

        if language:
            params["language"] = language

        if return_timestamps:
            params["timestamps"] = "true"

        # Prepare request body
        body = None
        files = None

        if isinstance(audio, bytes):
            # Binary audio data
            files = {"audio": ("audio.wav", audio, "audio/wav")}
        elif isinstance(audio, BytesIO):
            audio_bytes = audio.read()
            files = {"audio": ("audio.wav", audio_bytes, "audio/wav")}
        elif isinstance(audio, str):
            if audio.startswith("http://") or audio.startswith("https://"):
                # Remote URL - use JSON body
                body = {"url": audio}
            elif audio.startswith("data:audio"):
                # Base64 data URL
                header, encoded = audio.split(",", 1)
                audio_bytes = base64.b64decode(encoded)
                files = {"audio": ("audio.wav", audio_bytes, "audio/wav")}
            else:
                # Assume base64 string
                try:
                    audio_bytes = base64.b64decode(audio)
                    files = {"audio": ("audio.wav", audio_bytes, "audio/wav")}
                except Exception:
                    # If base64 decode fails, treat as URL
                    body = {"url": audio}
        else:
            raise ValueError(
                "Invalid audio input type. Expected bytes, BytesIO, or string (URL/base64)"
            )

        headers = {"Authorization": f"Token {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if files:
                    # File upload
                    response = await client.post(
                        url, params=params, files=files, headers=headers
                    )
                else:
                    # JSON body with URL
                    headers["Content-Type"] = "application/json"
                    response = await client.post(
                        url, params=params, json=body, headers=headers
                    )

                response.raise_for_status()
                result_data = response.json()

                # Parse Deepgram response
                metadata = result_data.get("metadata", {})
                results = result_data.get("results", {})

                # Extract transcript
                transcript = ""
                words = []
                confidence = None

                channels = results.get("channels", [])
                if channels and len(channels) > 0:
                    channel = channels[0]
                    alternatives = channel.get("alternatives", [])
                    if alternatives and len(alternatives) > 0:
                        alt = alternatives[0]
                        transcript = alt.get("transcript", "")
                        confidence = alt.get("confidence")

                        if return_timestamps:
                            words = alt.get("words", [])

                # Build response
                result = {
                    "transcript": transcript,
                    "confidence": confidence,
                    "model": model,
                    "duration": metadata.get("duration"),
                    "channels": metadata.get("channels"),
                    "language": metadata.get("language") or language,
                    "request_id": metadata.get("request_id"),
                }

                if return_timestamps and words:
                    result["words"] = words

                # Add model info if available
                model_info = metadata.get("model_info", {})
                if model_info:
                    result["model_info"] = model_info

                return result

        except httpx.HTTPError as e:
            logger.error(f"Deepgram speech-to-text API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("err_msg", str(e))
                    raise Exception(f"Deepgram speech-to-text API error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"Deepgram speech-to-text API error: {str(e)}")

    async def list_models(self) -> List[str]:
        """List available Deepgram models"""
        return [
            "nova-3",
            "nova-2",
            "nova-2-phonecall",
            "nova",
            "nova-phonecall",
            "enhanced",
            "enhanced-phonecall",
            "base",
            "base-phonecall",
            "whisper",
        ]

    def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        Get information about a specific model.

        Args:
            model: Model name

        Returns:
            Dictionary with model information
        """
        model_info = {
            "nova-3": {
                "name": "Nova 3",
                "description": "Latest and most accurate model",
                "use_case": "General transcription, highest accuracy",
            },
            "nova-2": {
                "name": "Nova 2",
                "description": "High accuracy, balanced performance",
                "use_case": "General transcription",
            },
            "nova-2-phonecall": {
                "name": "Nova 2 Phonecall",
                "description": "Optimized for phone call audio",
                "use_case": "Phone calls, telephony",
            },
            "nova": {
                "name": "Nova",
                "description": "Original Nova model",
                "use_case": "General transcription",
            },
            "nova-phonecall": {
                "name": "Nova Phonecall",
                "description": "Nova optimized for phone calls",
                "use_case": "Phone calls",
            },
            "enhanced": {
                "name": "Enhanced",
                "description": "Enhanced accuracy model",
                "use_case": "General transcription",
            },
            "enhanced-phonecall": {
                "name": "Enhanced Phonecall",
                "description": "Enhanced model for phone calls",
                "use_case": "Phone calls",
            },
            "base": {
                "name": "Base",
                "description": "Base model, cost-effective",
                "use_case": "Cost-sensitive applications",
            },
            "base-phonecall": {
                "name": "Base Phonecall",
                "description": "Base model for phone calls",
                "use_case": "Phone calls, cost-sensitive",
            },
            "whisper": {
                "name": "Whisper",
                "description": "OpenAI Whisper model",
                "use_case": "General transcription, open-source alternative",
            },
        }

        return model_info.get(
            model,
            {
                "name": model,
                "description": "Unknown model",
                "use_case": "General transcription",
            },
        )
