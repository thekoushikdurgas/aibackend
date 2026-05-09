"""
AI21 Labs Answer Service
Provides Q&A functionality with single document and RAG engine support
"""

import logging
from typing import Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class AI21AnswerService:
    """Service for AI21 Labs Answer/Q&A features"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        """
        Initialize AI21 Answer service.

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

    async def answer_single_document(self, context: str, question: str) -> Dict:
        """
        Answer a question from a single document context.

        Args:
            context: The document context to answer from
            question: The question to answer

        Returns:
            Dictionary with answer, id, and answerInContext flag
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/answer"
        payload = {"context": context, "question": question}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "id": data.get("id"),
                    "answer": data.get("answer", ""),
                    "answerInContext": data.get("answerInContext", False),
                }
        except httpx.HTTPError as e:
            logger.error(f"AI21 answer error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 answer error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 answer error: {str(e)}")

    async def answer_rag(self, question: str, document_ids: List[str]) -> Dict:
        """
        Answer a question using RAG engine with document IDs.

        Args:
            question: The question to answer
            document_ids: List of document IDs from the library

        Returns:
            Dictionary with answer, sources, highlights, and metadata
        """
        if not self.api_key:
            raise Exception("AI21 API key not configured")

        url = f"{self.base_url}/library/answer"
        payload = {"question": question, "documentIds": document_ids}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url, json=payload, headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "id": data.get("id"),
                    "answer": data.get("answer", ""),
                    "answerInContext": data.get("answerInContext", False),
                    "sources": data.get("sources", []),
                }
        except httpx.HTTPError as e:
            logger.error(f"AI21 RAG answer error: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get("error", {}).get("message", str(e))
                    raise Exception(f"AI21 RAG answer error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"AI21 RAG answer error: {str(e)}")
