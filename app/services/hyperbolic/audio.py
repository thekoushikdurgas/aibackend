"""
Hyperbolic Audio Generation Service
Handles text-to-speech generation
"""

import asyncio
import logging
from typing import Optional

import httpx

from .client import HyperbolicClient

logger = logging.getLogger(__name__)


class HyperbolicAudioService:
    """Service for audio generation using Hyperbolic API"""

    def __init__(self, client: Optional[HyperbolicClient] = None):
        """
        Initialize audio service.

        Args:
            client: Optional HyperbolicClient instance
        """
        self.client = client or HyperbolicClient()

    async def generate_audio(self, text: str, speed: float = 1.0) -> bytes:
        """
        Generate audio from text using Melo TTS.

        Args:
            text: Text to convert to speech
            speed: Speech speed multiplier (0.5-2.0, default 1.0)

        Returns:
            Audio binary data (typically WAV or MP3 format)
        """
        if not text:
            raise ValueError("Text cannot be empty")

        if speed < 0.5 or speed > 2.0:
            logger.warning(
                f"Speed {speed} outside recommended range (0.5-2.0), using anyway"
            )

        payload = {"text": text, "speed": speed}

        # Audio generation returns binary data
        # We need to handle this differently from JSON responses

        url = f"{self.client.base_url}/audio/generation"
        headers = self.client._get_headers()

        async with httpx.AsyncClient(timeout=self.client.timeout) as http_client:
            for attempt in range(self.client.max_retries + 1):
                try:
                    response = await http_client.post(
                        url, json=payload, headers=headers
                    )

                    # Handle rate limiting and transient errors
                    if response.status_code == 429:
                        retry_after = int(
                            response.headers.get(
                                "Retry-After", self.client.retry_delay * (2**attempt)
                            )
                        )
                        if attempt < self.client.max_retries:
                            logger.warning(f"Rate limited, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                            continue

                    if response.status_code == 503:
                        if attempt < self.client.max_retries:
                            wait_time = self.client.retry_delay * (2**attempt)
                            logger.info(
                                f"Service unavailable, waiting {wait_time:.1f}s"
                            )
                            await asyncio.sleep(wait_time)
                            continue

                    response.raise_for_status()

                    # Return binary audio data
                    return response.content

                except httpx.HTTPError as e:
                    if attempt < self.client.max_retries:
                        wait_time = self.client.retry_delay * (2**attempt)
                        logger.warning(f"Request failed, retrying in {wait_time}s: {e}")
                        await asyncio.sleep(wait_time)
                        continue
                    raise
