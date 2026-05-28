"""
Gemini Embedding Service
"""

import logging
from typing import List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class GeminiEmbeddingService:
    """
    Service for generating text embeddings using Gemini API.
    Uses gemini-embedding-001 model.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
    ):
        """
        Initialize Gemini embedding service.

        Args:
            api_key: Gemini API key
            model: Embedding model to use
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_embedding_model
        self.timeout = timeout
        self.base_url = settings.gemini_base_url

        if not self.api_key:
            logger.warning("Gemini API key not configured")

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding
        """
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        url = f"{self.base_url}/models/{self.model}:embedContent?key={self.api_key}"
        payload = {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]},
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                # Extract embedding
                embedding = data.get("embedding", {}).get("values", [])
                return embedding

        except httpx.HTTPError as e:
            logger.error(f"Gemini embedding API error: {e}")
            raise Exception(f"Gemini embedding API error: {str(e)}")

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        # Gemini API supports batch embedding
        if not self.api_key:
            raise Exception("Gemini API key not configured")

        url = (
            f"{self.base_url}/models/{self.model}:batchEmbedContents?key={self.api_key}"
        )
        payload = {
            "requests": [
                {
                    "model": f"models/{self.model}",
                    "content": {"parts": [{"text": text}]},
                }
                for text in texts
            ]
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()

                # Extract embeddings
                embeddings = []
                for embed_response in data.get("embeddings", []):
                    embedding = embed_response.get("values", [])
                    embeddings.append(embedding)

                return embeddings

        except httpx.HTTPError as e:
            logger.error(f"Gemini batch embedding API error: {e}")
            # Fallback to individual requests
            logger.warning("Falling back to individual embedding requests")
            return [await self.embed_text(text) for text in texts]
