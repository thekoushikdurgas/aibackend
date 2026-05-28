"""
NVIDIA Embeddings Service
Text embeddings for semantic search and RAG applications
"""

import logging
from typing import Dict, List, Optional, Union, Any

from app.config import settings
from .client import NVIDIAClient, BaseURLType
from .models import get_embedding_models, get_model, validate_model

logger = logging.getLogger(__name__)


class NVIDIAEmbeddingService:
    """
    NVIDIA embedding service for generating text embeddings.

    Supports:
    - Single and batch embeddings (up to 32 texts)
    - Multiple embedding dimensions
    - Query and passage input types
    - Truncation strategies
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        genai_base_url: Optional[str] = None,
    ):
        """
        Initialize NVIDIA embedding service.

        Args:
            api_key: NVIDIA API key
            model: Default embedding model
            timeout: Request timeout in seconds
            genai_base_url: Optional custom GenAI base URL
        """
        self.client = NVIDIAClient(
            api_key=api_key,
            genai_base_url=genai_base_url,
            timeout=timeout or settings.nvidia_embedding_timeout,
        )
        self.default_model = model or settings.nvidia_embedding_model

        if not self.client.api_key:
            logger.warning("NVIDIA API key not configured")

    async def embed(
        self,
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        input_type: str = "query",
        truncate: str = "END",
        dimensions: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate embeddings for text(s).

        Args:
            texts: Single text string or list of texts (max 32)
            model: Embedding model to use
            input_type: Type of input - "query" or "passage"
            truncate: Truncation strategy - "START", "END", or "NONE"
            dimensions: Optional dimension size (256, 512, 768, 1024)

        Returns:
            Dictionary with embeddings and metadata
        """
        if not self.client.api_key:
            raise Exception("NVIDIA API key not configured")

        model = model or self.default_model

        # Validate model
        if not validate_model(model):
            logger.warning(f"Model {model} not in registry, proceeding anyway")

        # Normalize input to list
        if isinstance(texts, str):
            texts = [texts]

        # Validate batch size
        if len(texts) > 32:
            raise ValueError("Maximum 32 texts per batch")

        # Build request payload
        payload: Dict[str, Any] = {
            "input": texts,
            "model": model,
            "input_type": input_type,
            "truncate": truncate,
        }

        if dimensions:
            payload["dimensions"] = dimensions

        try:
            response = await self.client.post(
                "genai/embed", url_type=BaseURLType.GENAI, model_id=model, json=payload
            )

            data = response.json()

            # Extract NVIDIA-specific headers
            nvidia_headers = self.client._extract_nvidia_headers(response)

            result = {
                "model": model,
                "embeddings": data.get("data", []),
                "usage": data.get("usage", {}),
                **nvidia_headers,
            }

            return result

        except Exception as e:
            logger.error(f"NVIDIA embedding error: {e}")
            raise

    async def embed_query(
        self, query: str, model: Optional[str] = None, dimensions: Optional[int] = None
    ) -> List[float]:
        """
        Generate embedding for a query.

        Args:
            query: Query text
            model: Embedding model to use
            dimensions: Optional dimension size

        Returns:
            Embedding vector as list of floats
        """
        result = await self.embed(
            texts=query, model=model, input_type="query", dimensions=dimensions
        )

        embeddings = result.get("embeddings", [])
        if embeddings:
            return embeddings[0].get("embedding", [])
        return []

    async def embed_passages(
        self,
        passages: List[str],
        model: Optional[str] = None,
        dimensions: Optional[int] = None,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple passages.

        Args:
            passages: List of passage texts
            model: Embedding model to use
            dimensions: Optional dimension size

        Returns:
            List of embedding vectors
        """
        result = await self.embed(
            texts=passages, model=model, input_type="passage", dimensions=dimensions
        )

        embeddings = result.get("embeddings", [])
        return [item.get("embedding", []) for item in embeddings]

    async def health_check(self) -> bool:
        """Check if NVIDIA embedding API is available"""
        return await self.client.health_check(BaseURLType.GENAI)

    async def list_models(self) -> List[str]:
        """List all available embedding models"""
        return get_embedding_models()

    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an embedding model.

        Args:
            model_id: Model identifier

        Returns:
            Model metadata dictionary or None if not found
        """
        model = get_model(model_id)
        if not model or model.category.value != "embedding":
            return None

        return {
            "id": model.id,
            "category": model.category.value,
            "provider": model.provider.value,
            "capabilities": list(model.capabilities),
            "description": model.description,
        }
