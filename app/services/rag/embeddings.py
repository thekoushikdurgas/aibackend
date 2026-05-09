"""
Embedding Service for RAG
"""

import logging
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings.
    Supports local (sentence-transformers) and HuggingFace API embeddings.
    """

    def __init__(
        self, provider: Optional[str] = None, model_name: Optional[str] = None
    ):
        """
        Initialize embedding service.

        Args:
            provider: Embedding provider (local or huggingface)
            model_name: Model to use for embeddings
        """
        self.provider = provider or settings.embedding_provider
        self.model_name = model_name or settings.embedding_model
        self._model = None
        self._dimension: Optional[int] = None

    @property
    def model(self):
        """Lazy load the embedding model"""
        if self._model is None:
            self._load_model()
        return self._model

    @property
    def dimension(self) -> int:
        """Get embedding dimension"""
        if self._dimension is None:
            # Generate a test embedding to get dimension
            test_embedding = self.embed_text("test")
            self._dimension = len(test_embedding)
        return self._dimension

    def _load_model(self):
        """Load the embedding model"""
        if self.provider == "local":
            self._load_local_model()
        elif self.provider == "huggingface":
            self._load_huggingface_model()
        elif self.provider == "gemini":
            self._load_gemini_model()
        elif self.provider == "cohere":
            self._load_cohere_model()
        else:
            raise ValueError(f"Unknown embedding provider: {self.provider}")

    def _load_local_model(self):
        """Load local sentence-transformers model"""
        try:
            from sentence_transformers import SentenceTransformer

            logger.info(f"Loading local embedding model: {self.model_name}")
            self._model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")

        except ImportError:
            logger.error("sentence-transformers not installed")
            raise ImportError(
                "sentence-transformers is required for local embeddings. "
                "Install with: pip install sentence-transformers"
            )

    def _load_huggingface_model(self):
        """Set up HuggingFace API for embeddings"""
        if not settings.huggingface_api_key:
            raise ValueError("HuggingFace API key required for huggingface embeddings")

        # For HuggingFace API, we'll use httpx in embed methods
        self._model = "huggingface_api"
        logger.info(f"Using HuggingFace API for embeddings: {self.model_name}")

    def _load_gemini_model(self):
        """Set up Gemini API for embeddings"""
        if not settings.gemini_api_key:
            raise ValueError("Gemini API key required for gemini embeddings")

        # For Gemini API, we'll use the GeminiEmbeddingService
        from app.services.gemini.embeddings import GeminiEmbeddingService

        self._model = GeminiEmbeddingService(
            model=self.model_name or settings.gemini_embedding_model
        )
        logger.info(
            f"Using Gemini API for embeddings: {self.model_name or settings.gemini_embedding_model}"
        )

    def _load_cohere_model(self):
        """Set up Cohere API for embeddings"""
        if not settings.cohere_api_key:
            raise ValueError("Cohere API key required for cohere embeddings")

        # For Cohere API, we'll use CohereEmbeddings service
        from app.services.cohere import CohereEmbeddings

        self._model = CohereEmbeddings()
        logger.info(
            f"Using Cohere API for embeddings: {self.model_name or settings.cohere_embed_model}"
        )

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding
        """
        if self.provider == "local":
            return self._embed_local(text)
        elif self.provider == "huggingface":
            return self._embed_huggingface(text)
        elif self.provider == "gemini":
            return self._embed_gemini(text)
        elif self.provider == "cohere":
            return self._embed_cohere(text)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embeddings
        """
        if self.provider == "local":
            return self._embed_local_batch(texts)
        elif self.provider == "huggingface":
            return [self._embed_huggingface(text) for text in texts]
        elif self.provider == "gemini":
            return self._embed_gemini_batch(texts)
        elif self.provider == "cohere":
            return self._embed_cohere_batch(texts)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _embed_local(self, text: str) -> List[float]:
        """Generate embedding using local model"""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def _embed_local_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch using local model"""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def _embed_huggingface(self, text: str) -> List[float]:
        """Generate embedding using HuggingFace Inference API"""
        import asyncio
        from app.services.llm.hf_client import HuggingFaceClient

        # Use async client
        client = HuggingFaceClient(api_key=settings.huggingface_api_key)

        try:
            # Try embeddings endpoint first (for models like Qwen3-Embedding)
            try:
                url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"
                response = asyncio.run(
                    client.inference_api(
                        model=self.model_name,
                        inputs=text,
                        parameters={"options": {"wait_for_model": True}},
                    )
                )
            except Exception:
                # Fallback to feature-extraction endpoint
                import httpx

                url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}"
                headers = {"Authorization": f"Bearer {settings.huggingface_api_key}"}

                response = httpx.post(
                    url,
                    headers=headers,
                    json={"inputs": text, "options": {"wait_for_model": True}},
                    timeout=30.0,
                )
                response.raise_for_status()
                response = response.json()

            # Handle nested response format
            if isinstance(response, list):
                if len(response) > 0 and isinstance(response[0], list):
                    # Mean pooling for token embeddings
                    import numpy as np

                    return np.mean(response, axis=0).tolist()
                elif len(response) > 0:
                    return (
                        response[0]
                        if isinstance(response[0], (list, tuple))
                        else response
                    )
                return response

            # Handle dict response
            if isinstance(response, dict):
                if "embedding" in response:
                    return response["embedding"]
                elif "embeddings" in response:
                    embeddings = response["embeddings"]
                    if isinstance(embeddings, list) and len(embeddings) > 0:
                        return embeddings[0]

            return response if isinstance(response, list) else [response]

        except Exception as e:
            logger.error(f"HuggingFace embedding API error: {e}")
            raise

    def _embed_gemini(self, text: str) -> List[float]:
        """Generate embedding using Gemini API"""
        import asyncio

        gemini_service = self.model
        try:
            return asyncio.run(gemini_service.embed_text(text))
        except Exception as e:
            logger.error(f"Gemini embedding error: {e}")
            raise

    def _embed_gemini_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch using Gemini API"""
        import asyncio

        gemini_service = self.model
        try:
            return asyncio.run(gemini_service.embed_texts(texts))
        except Exception as e:
            logger.error(f"Gemini batch embedding error: {e}")
            raise

    def _embed_cohere(self, text: str) -> List[float]:
        """Generate embedding using Cohere API"""
        import asyncio

        cohere_service = self.model
        try:
            result = asyncio.run(
                cohere_service.embed(
                    texts=[text],
                    model=self.model_name or settings.cohere_embed_model,
                    input_type="search_document",
                )
            )
            embeddings = result.get("embeddings", [])
            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.error(f"Cohere embedding error: {e}")
            raise

    def _embed_cohere_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch using Cohere API"""
        import asyncio

        cohere_service = self.model
        try:
            result = asyncio.run(
                cohere_service.embed(
                    texts=texts,
                    model=self.model_name or settings.cohere_embed_model,
                    input_type="search_document",
                )
            )
            return result.get("embeddings", [])
        except Exception as e:
            logger.error(f"Cohere batch embedding error: {e}")
            raise


# Global embedding service instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get global embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
