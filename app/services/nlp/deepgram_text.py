"""
Deepgram Text-to-Text Service
Uses Deepgram's API for text summarization
"""

import logging
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class DeepgramTextService:
    """Service for text summarization using Deepgram's API"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize Deepgram text service.

        Args:
            api_key: Deepgram API key
            base_url: Optional custom base URL
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.deepgram_api_key
        self.base_url = base_url or settings.deepgram_base_url
        self.timeout = timeout

        if not self.api_key:
            logger.warning("Deepgram API key not configured")

    async def summarize(
        self, text: str, language: str = "en", max_length: Optional[int] = None
    ) -> dict:
        """
        Summarize text using Deepgram's API.

        Args:
            text: Text to summarize
            language: Language code (default: "en")
            max_length: Maximum length of summary (optional)

        Returns:
            Dictionary with summary and metadata
        """
        if not self.api_key:
            raise Exception("Deepgram API key not configured")

        url = f"{self.base_url}/read"

        # Build query parameters
        params = {"language": language, "summarize": "true"}

        if max_length:
            params["max_length"] = str(max_length)

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
                result_data = response.json()

                # Parse Deepgram response
                # The response structure may vary, so we'll handle it flexibly
                summary = ""

                # Try different possible response structures
                if isinstance(result_data, dict):
                    if "summary" in result_data:
                        summary = result_data["summary"]
                    elif "text" in result_data:
                        summary = result_data["text"]
                    elif "result" in result_data:
                        summary = result_data["result"]
                    elif "content" in result_data:
                        summary = result_data["content"]
                    else:
                        # If it's a nested structure, try to find text
                        summary = str(result_data)
                elif isinstance(result_data, str):
                    summary = result_data
                else:
                    summary = str(result_data)

                result = {
                    "summary": summary,
                    "original_text": text,
                    "language": language,
                    "original_length": len(text),
                    "summary_length": len(summary),
                }

                return result

        except httpx.HTTPError as e:
            logger.error(f"Deepgram text summarization API error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("err_msg", str(e))
                    raise Exception(
                        f"Deepgram text summarization API error: {error_msg}"
                    )
                except (ValueError, AttributeError, KeyError):
                    # Response might not be JSON
                    error_text = (
                        e.response.text if hasattr(e.response, "text") else str(e)
                    )
                    raise Exception(
                        f"Deepgram text summarization API error: {error_text}"
                    )
            raise Exception(f"Deepgram text summarization API error: {str(e)}")
