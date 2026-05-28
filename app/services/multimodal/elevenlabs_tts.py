"""
ElevenLabs Text-to-Speech Service
Uses ElevenLabs API for high-quality speech synthesis
Supports multiple models, voices, and voice customization
"""

import base64
import logging
import time
from functools import wraps
from typing import Optional, Dict, Any, List, AsyncGenerator

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


# Simple in-memory cache with TTL
class CacheEntry:
    """Cache entry with TTL"""

    def __init__(self, data: Any, ttl: int):
        self.data = data
        self.expires_at = time.time() + ttl

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class SimpleCache:
    """Simple in-memory cache"""

    def __init__(self) -> None:
        self._cache: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry and not entry.is_expired():
            return entry.data
        if entry:
            del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int):
        self._cache[key] = CacheEntry(value, ttl)

    def clear(self):
        self._cache.clear()


# Global cache instance
_cache = SimpleCache()


def cached(ttl: int = 3600):
    """Decorator for caching function results"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            cached_value = _cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)
            _cache.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


class ElevenLabsTextToSpeechService:
    """Service for generating speech from text using ElevenLabs API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_voice_id: Optional[str] = None,
        default_model_id: Optional[str] = None,
        timeout: float = 120.0,
        cache_ttl: int = 3600,
    ):
        """
        Initialize ElevenLabs text-to-speech service.

        Args:
            api_key: ElevenLabs API key
            base_url: Base URL for ElevenLabs API
            default_voice_id: Default voice ID to use
            default_model_id: Default model ID to use
            timeout: Request timeout in seconds
            cache_ttl: Cache TTL in seconds
        """
        self.api_key = api_key or settings.elevenlabs_api_key
        self.base_url = base_url or settings.elevenlabs_base_url
        self.default_voice_id = default_voice_id or settings.elevenlabs_default_voice_id
        self.default_model_id = default_model_id or settings.elevenlabs_default_model_id
        self.timeout = timeout or settings.elevenlabs_timeout
        self.cache_ttl = cache_ttl or settings.elevenlabs_cache_ttl

        if not self.api_key:
            logger.warning("ElevenLabs API key not configured")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {"xi-api-key": self.api_key or "", "Content-Type": "application/json"}

    @cached(ttl=3600)
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List all available models.

        Returns:
            List of model dictionaries
        """
        if not self.api_key:
            raise Exception("ElevenLabs API key not configured")

        url = f"{self.base_url}/models"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"ElevenLabs models API error: {e.response.status_code} - {e.response.text}"
            )
            if e.response.status_code == 401:
                raise Exception("Invalid ElevenLabs API key")
            raise Exception(f"Failed to fetch models: {e.response.text}")
        except httpx.HTTPError as e:
            logger.error(f"ElevenLabs models API error: {e}")
            raise Exception(f"Failed to fetch models: {str(e)}")

    async def get_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific model information.

        Args:
            model_id: Model ID to fetch

        Returns:
            Model dictionary or None if not found
        """
        models = await self.list_models()
        for model in models:
            if model.get("model_id") == model_id:
                return model
        return None

    @cached(ttl=3600)
    async def list_voices(self) -> List[Dict[str, Any]]:
        """
        List all available voices.

        Returns:
            List of voice dictionaries
        """
        if not self.api_key:
            raise Exception("ElevenLabs API key not configured")

        url = f"{self.base_url}/voices"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()
                return data.get("voices", [])
        except httpx.HTTPStatusError as e:
            logger.error(
                f"ElevenLabs voices API error: {e.response.status_code} - {e.response.text}"
            )
            if e.response.status_code == 401:
                raise Exception("Invalid ElevenLabs API key")
            raise Exception(f"Failed to fetch voices: {e.response.text}")
        except httpx.HTTPError as e:
            logger.error(f"ElevenLabs voices API error: {e}")
            raise Exception(f"Failed to fetch voices: {str(e)}")

    async def get_voice(self, voice_id: str) -> Optional[Dict[str, Any]]:
        """
        Get specific voice information.

        Args:
            voice_id: Voice ID to fetch

        Returns:
            Voice dictionary or None if not found
        """
        voices = await self.list_voices()
        for voice in voices:
            if voice.get("voice_id") == voice_id:
                return voice
        return None

    async def filter_voices(
        self,
        gender: Optional[str] = None,
        accent: Optional[str] = None,
        age: Optional[str] = None,
        use_case: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Filter voices by various criteria.

        Args:
            gender: Filter by gender (male, female, non-binary)
            accent: Filter by accent (American, British, etc.)
            age: Filter by age (young, middle-aged, old)
            use_case: Filter by use case (narration, conversational, etc.)
            category: Filter by category (premade, cloned, etc.)

        Returns:
            Filtered list of voices
        """
        voices = await self.list_voices()
        filtered = []

        for voice in voices:
            labels = voice.get("labels", {})

            if gender and labels.get("gender", "").lower() != gender.lower():
                continue
            if accent and labels.get("accent", "").lower() != accent.lower():
                continue
            if age and labels.get("age", "").lower() != age.lower():
                continue
            if use_case and labels.get("use_case", "").lower() != use_case.lower():
                continue
            if category and voice.get("category", "").lower() != category.lower():
                continue

            filtered.append(voice)

        return filtered

    async def validate_text_length(
        self, text: str, model_id: Optional[str] = None
    ) -> bool:
        """
        Validate text length against model limits.

        Args:
            text: Text to validate
            model_id: Model ID to check (uses default if not provided)

        Returns:
            True if valid, raises exception if invalid
        """
        model_id = model_id or self.default_model_id
        model = await self.get_model(model_id)

        if not model:
            raise Exception(f"Model {model_id} not found")

        max_length = model.get("maximum_text_length_per_request", 10000)
        if len(text) > max_length:
            raise Exception(
                f"Text length ({len(text)}) exceeds model limit ({max_length}) "
                f"for model {model_id}"
            )

        return True

    async def generate(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        voice_settings: Optional[Dict[str, Any]] = None,
        return_base64: bool = True,
        optimize_streaming_latency: Optional[int] = None,
        output_format: Optional[str] = None,
        pronunciation_dictionary_locators: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Generate speech audio from text.

        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use (defaults to configured default)
            model_id: Model ID to use (defaults to configured default)
            voice_settings: Voice settings (stability, similarity_boost, style, use_speaker_boost)
            return_base64: Whether to return base64-encoded audio
            optimize_streaming_latency: Optimize for streaming latency (0-4)

        Returns:
            Dictionary with audio data and metadata
        """
        if not self.api_key:
            raise Exception("ElevenLabs API key not configured")

        voice_id = voice_id or self.default_voice_id
        model_id = model_id or self.default_model_id

        # Validate voice exists
        voice = await self.get_voice(voice_id)
        if not voice:
            raise Exception(f"Voice {voice_id} not found")

        # Validate text length
        await self.validate_text_length(text, model_id)

        # Build request body
        body: Dict[str, Any] = {"text": text, "model_id": model_id}

        # Add voice settings if provided
        if voice_settings:
            body["voice_settings"] = voice_settings
        else:
            # Use default voice settings
            body["voice_settings"] = {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "use_speaker_boost": True,
            }

        # Add streaming optimization if provided
        if optimize_streaming_latency is not None:
            body["optimize_streaming_latency"] = optimize_streaming_latency

        if output_format is not None:
            body["output_format"] = output_format
        if pronunciation_dictionary_locators is not None:
            body["pronunciation_dictionary_locators"] = (
                pronunciation_dictionary_locators
            )

        url = f"{self.base_url}/text-to-speech/{voice_id}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=body, headers=self._get_headers()
                )
                response.raise_for_status()

                # ElevenLabs returns audio as binary data
                audio_bytes = response.content
                content_type = response.headers.get("content-type", "audio/mpeg")

                result = {
                    "voice_id": voice_id,
                    "model_id": model_id,
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

                # Estimate duration (rough estimate for MP3)
                if content_type == "audio/mpeg":
                    # Rough estimate: ~1KB per second for MP3
                    estimated_duration = int((len(audio_bytes) / 1024) * 1000)
                    result["duration_ms"] = estimated_duration

                return result

        except httpx.HTTPStatusError as e:
            logger.error(
                f"ElevenLabs TTS API error: {e.response.status_code} - {e.response.text}"
            )
            if e.response.status_code == 401:
                raise Exception("Invalid ElevenLabs API key")
            elif e.response.status_code == 429:
                raise Exception("Rate limit exceeded. Please try again later.")
            elif e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("detail", {}).get(
                        "message", e.response.text
                    )
                    raise Exception(f"Invalid request: {error_msg}")
                except (ValueError, KeyError):
                    raise Exception(f"Invalid request: {e.response.text}")
            raise Exception(f"ElevenLabs TTS API error: {e.response.text}")
        except httpx.HTTPError as e:
            logger.error(f"ElevenLabs TTS API error: {e}")
            raise Exception(f"Failed to generate speech: {str(e)}")

    async def generate_stream(
        self,
        text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        voice_settings: Optional[Dict[str, Any]] = None,
        optimize_streaming_latency: Optional[int] = 2,
    ) -> AsyncGenerator[bytes, None]:
        """
        Generate speech audio from text with streaming.

        Args:
            text: Text to convert to speech
            voice_id: Voice ID to use (defaults to configured default)
            model_id: Model ID to use (defaults to configured default)
            voice_settings: Voice settings
            optimize_streaming_latency: Optimize for streaming latency (0-4, default 2)

        Yields:
            Audio data chunks as bytes
        """
        if not self.api_key:
            raise Exception("ElevenLabs API key not configured")

        voice_id = voice_id or self.default_voice_id
        model_id = model_id or self.default_model_id

        # Validate voice exists
        voice = await self.get_voice(voice_id)
        if not voice:
            raise Exception(f"Voice {voice_id} not found")

        # Validate text length
        await self.validate_text_length(text, model_id)

        # Build request body
        body: Dict[str, Any] = {"text": text, "model_id": model_id}

        if voice_settings:
            body["voice_settings"] = voice_settings
        else:
            body["voice_settings"] = {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "use_speaker_boost": True,
            }

        if optimize_streaming_latency is not None:
            body["optimize_streaming_latency"] = optimize_streaming_latency

        url = f"{self.base_url}/text-to-speech/{voice_id}/stream"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", url, json=body, headers=self._get_headers()
                ) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        if chunk:
                            yield chunk
        except httpx.HTTPStatusError as e:
            logger.error(
                f"ElevenLabs streaming TTS API error: {e.response.status_code} - {e.response.text}"
            )
            if e.response.status_code == 401:
                raise Exception("Invalid ElevenLabs API key")
            elif e.response.status_code == 429:
                raise Exception("Rate limit exceeded. Please try again later.")
            raise Exception(f"ElevenLabs streaming TTS API error: {e.response.text}")
        except httpx.HTTPError as e:
            logger.error(f"ElevenLabs streaming TTS API error: {e}")
            raise Exception(f"Failed to stream speech: {str(e)}")
