"""
AI21 Labs NLP Service
Provides specialized NLP features using AI21 Labs API:
- Text summarization
- Grammar error correction
- Text improvements (fluency, vocabulary)
- Text embeddings
"""

import logging
from typing import Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AI21NLPService:
    """Service for AI21 Labs specialized NLP features"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize AI21 NLP service.

        Args:
            api_key: AI21 API key
            base_url: Base URL for AI21 API
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.ai21_api_key
        self.base_url = base_url or settings.ai21_base_url
        self.timeout = timeout

        if not self.api_key:
            logger.warning("AI21 API key not configured")

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def summarize(
        self, text: str, source_type: str = "TEXT", focus: Optional[str] = None
    ) -> Dict:
        """
        Summarize text using AI21 Labs API.

        Args:
            text: Text to summarize
            source_type: Type of source (TEXT, URL, etc.)
            focus: Optional focus area for the summary

        Returns:
            Dictionary with summary and metadata
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/summarize"
        payload = {"source": text, "sourceType": source_type}

        if focus:
            payload["focus"] = focus

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "summary": data.get("summary", ""),
                    "id": data.get("id"),
                    "original_length": len(text),
                    "summary_length": len(data.get("summary", "")),
                }
        except httpx.HTTPError as e:
            logger.error(f"AI21 summarization error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 summarization error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 summarization error: {str(e)}")

    async def summarize_by_segment(
        self, text: str, source_type: str = "TEXT", focus: Optional[str] = None
    ) -> Dict:
        """
        Summarize text by segment using AI21 Labs API.

        Args:
            text: Text to summarize
            source_type: Type of source (TEXT, URL, etc.)
            focus: Optional focus area for the summary

        Returns:
            Dictionary with segments and their summaries
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/summarize-by-segment"
        payload = {"source": text, "sourceType": source_type}

        if focus:
            payload["focus"] = focus

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                return {"segments": data.get("segments", []), "id": data.get("id")}
        except httpx.HTTPError as e:
            logger.error(f"AI21 segment summarization error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 segment summarization error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 segment summarization error: {str(e)}")

    async def grammar_check(self, text: str) -> Dict:
        """
        Check and correct grammatical errors in text.

        Args:
            text: Text to check

        Returns:
            Dictionary with corrections and metadata
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/gec"
        payload = {"text": text}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "corrections": data.get("corrections", []),
                    "id": data.get("id"),
                    "original_text": text,
                }
        except httpx.HTTPError as e:
            logger.error(f"AI21 grammar check error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 grammar check error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 grammar check error: {str(e)}")

    async def improve_text(
        self, text: str, improvement_types: Optional[List[str]] = None
    ) -> Dict:
        """
        Improve text with suggestions for fluency, vocabulary, etc.

        Args:
            text: Text to improve
            improvement_types: List of improvement types (e.g., ["fluency", "vocabulary/specificity"])

        Returns:
            Dictionary with improvement suggestions
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/improvements"
        payload = {"text": text}

        if improvement_types:
            payload["types"] = improvement_types

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "improvements": data.get("improvements", []),
                    "id": data.get("id"),
                    "original_text": text,
                }
        except httpx.HTTPError as e:
            logger.error(f"AI21 text improvement error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 text improvement error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 text improvement error: {str(e)}")

    async def get_embeddings(
        self, texts: List[str], embedding_type: str = "segment"
    ) -> Dict:
        """
        Get embeddings for text(s).

        Args:
            texts: List of texts to embed
            embedding_type: Type of embedding (segment, query, etc.)

        Returns:
            Dictionary with embeddings and metadata
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/embed"
        payload = {"texts": texts, "type": embedding_type}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                return {"results": data.get("results", []), "id": data.get("id")}
        except httpx.HTTPError as e:
            logger.error(f"AI21 embedding error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 embedding error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 embedding error: {str(e)}")

    async def tokenize(self, text: str) -> Dict:
        """
        Tokenize text using AI21 Labs API.

        Args:
            text: Text to tokenize

        Returns:
            Dictionary with tokens and metadata
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/tokenize"
        payload = {"text": text}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "tokens": data.get("tokens", []),
                    "text": data.get("text", text),
                }
        except httpx.HTTPError as e:
            logger.error(f"AI21 tokenization error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 tokenization error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 tokenization error: {str(e)}")

    async def paraphrase(self, text: str, style: Optional[str] = None) -> Dict:
        """
        Paraphrase text using AI21 Labs API.

        Args:
            text: Text to paraphrase
            style: Optional style for paraphrasing

        Returns:
            Dictionary with paraphrase suggestions
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/paraphrase"
        payload = {"text": text}

        if style:
            payload["style"] = style

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "suggestions": data.get("suggestions", []),
                    "id": data.get("id"),
                    "original_text": text,
                }
        except httpx.HTTPError as e:
            logger.error(f"AI21 paraphrase error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 paraphrase error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 paraphrase error: {str(e)}")

    async def segment_text(self, text: str, source_type: str = "TEXT") -> Dict:
        """
        Segment text into parts using AI21 Labs API.

        Args:
            text: Text to segment
            source_type: Type of source (TEXT, URL, etc.)

        Returns:
            Dictionary with segments and boundaries
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/segmentation"
        payload = {"source": text, "sourceType": source_type}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                return {"segments": data.get("segments", []), "id": data.get("id")}
        except httpx.HTTPError as e:
            logger.error(f"AI21 segmentation error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 segmentation error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 segmentation error: {str(e)}")

    async def summarize_conversation(self, messages: List[Dict]) -> Dict:
        """
        Summarize a conversation using AI21 Labs API.

        Args:
            messages: List of conversation messages with role and text

        Returns:
            Dictionary with conversation summary
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/summarize-conversation"
        payload = {"messages": messages}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "summary": data.get("summary", ""),
                    "id": data.get("id"),
                    "message_count": len(messages),
                }
        except httpx.HTTPError as e:
            logger.error(f"AI21 conversation summarization error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(
                        f"AI21 conversation summarization error: {error_msg}"
                    )
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 conversation summarization error: {str(e)}")
