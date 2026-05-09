"""
OpenRouter Embedding Service
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any

import httpx

from app.config import settings
from app.services.openrouter.monitoring import get_monitor

logger = logging.getLogger(__name__)


class OpenRouterEmbeddingService:
    """
    Service for generating text embeddings using OpenRouter API.
    Supports multiple embedding models from different providers.
    """

    # Supported embedding models (from Postman collection)
    EMBEDDING_MODELS = [
        "google/gemini-embedding-001",
        "openai/text-embedding-3-small",
        "openai/text-embedding-3-large",
        "openai/text-embedding-ada-002",
        "mistralai/mistral-embed-2312",
        "mistralai/codestral-embed-2505",
        "qwen/qwen3-embedding-0.6b",
        "qwen/qwen3-embedding-4b",
        "qwen/qwen3-embedding-8b",
    ]

    # Model metadata including dimensions and pricing
    MODEL_METADATA = {
        "google/gemini-embedding-001": {
            "dimensions": 768,
            "max_input_tokens": 2048,
            "pricing": {"prompt": "0.0001", "completion": "0"},
        },
        "openai/text-embedding-3-small": {
            "dimensions": 1536,
            "max_input_tokens": 8191,
            "pricing": {"prompt": "0.02", "completion": "0"},
        },
        "openai/text-embedding-3-large": {
            "dimensions": 3072,
            "max_input_tokens": 8191,
            "pricing": {"prompt": "0.13", "completion": "0"},
        },
        "openai/text-embedding-ada-002": {
            "dimensions": 1536,
            "max_input_tokens": 8191,
            "pricing": {"prompt": "0.1", "completion": "0"},
        },
        "mistralai/mistral-embed-2312": {
            "dimensions": 1024,
            "max_input_tokens": 8192,
            "pricing": {"prompt": "0.0001", "completion": "0"},
        },
        "mistralai/codestral-embed-2505": {
            "dimensions": 1024,
            "max_input_tokens": 8192,
            "pricing": {"prompt": "0.0001", "completion": "0"},
        },
        "qwen/qwen3-embedding-0.6b": {
            "dimensions": 512,
            "max_input_tokens": 8192,
            "pricing": {"prompt": "0.00005", "completion": "0"},
        },
        "qwen/qwen3-embedding-4b": {
            "dimensions": 1024,
            "max_input_tokens": 8192,
            "pricing": {"prompt": "0.0001", "completion": "0"},
        },
        "qwen/qwen3-embedding-8b": {
            "dimensions": 2048,
            "max_input_tokens": 8192,
            "pricing": {"prompt": "0.0002", "completion": "0"},
        },
    }

    DEFAULT_MODEL = "openai/text-embedding-3-small"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 60.0,
        base_url: Optional[str] = None,
        site_url: Optional[str] = None,
        app_name: Optional[str] = None,
    ):
        """
        Initialize OpenRouter embedding service.

        Args:
            api_key: OpenRouter API key
            model: Embedding model to use (default: text-embedding-3-small)
            timeout: Request timeout in seconds
            base_url: OpenRouter API base URL
            site_url: Site URL for tracking
            app_name: App name for tracking
        """
        self.api_key = api_key or settings.openrouter_api_key
        self.model = model or self.DEFAULT_MODEL
        self.timeout = timeout
        self.base_url = base_url or settings.openrouter_base_url
        self.site_url = site_url or settings.openrouter_site_url
        self.app_name = app_name or settings.openrouter_app_name

        # Retry configuration
        self._max_retries: int = 3
        self._retry_delay: float = 1.0
        self._retry_backoff: float = 2.0

        # Monitoring
        self._monitor = get_monitor()

        if not self.api_key:
            logger.warning("OpenRouter API key not configured")

    def _build_headers(self) -> dict:
        """Build request headers"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.site_url:
            headers["HTTP-Referer"] = self.site_url
        if self.app_name:
            headers["X-Title"] = self.app_name
        return headers

    async def embed_text(self, text: str, model: Optional[str] = None) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            model: Optional model override

        Returns:
            List of floats representing the embedding
        """
        return (await self.embed_texts([text], model))[0]

    async def embed_texts(
        self, texts: List[str], model: Optional[str] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            model: Optional model override

        Returns:
            List of embeddings
        """
        if not self.api_key:
            raise Exception("OpenRouter API key not configured")

        model = model or self.model

        # OpenRouter uses OpenAI-compatible embeddings endpoint
        url = f"{self.base_url}/embeddings"
        headers = self._build_headers()

        start_time = time.time()

        # Try primary model first, then fallback
        fallback_models = [
            model,
            "openai/text-embedding-3-small",
            "openai/text-embedding-ada-002",
        ]

        last_error = None
        last_status_code = None

        for attempt_model in fallback_models:
            for retry_attempt in range(self._max_retries):
                try:
                    # OpenRouter embeddings API expects input as string or array of strings
                    # For batch, we can send multiple texts in one request
                    payload = {
                        "model": attempt_model,
                        "input": texts if len(texts) > 1 else texts[0],
                    }

                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(url, json=payload, headers=headers)
                        response.raise_for_status()
                        data = response.json()

                        # Extract embeddings from OpenAI-compatible response
                        embeddings_data = data.get("data", [])

                        if isinstance(embeddings_data, list):
                            embeddings = [
                                item.get("embedding", []) for item in embeddings_data
                            ]
                            # Ensure all embeddings are lists of floats
                            result = [list(map(float, emb)) for emb in embeddings]
                        else:
                            # Single embedding response
                            embedding = embeddings_data.get("embedding", [])
                            result = [list(map(float, embedding))]

                        # Calculate metrics
                        latency_ms = (time.time() - start_time) * 1000
                        usage = data.get("usage", {})
                        total_tokens = usage.get("total_tokens", 0)
                        self.calculate_cost(attempt_model, total_tokens)

                        # Record successful request
                        self._monitor.record_request(
                            model=attempt_model,
                            provider="OpenRouter",
                            prompt_tokens=total_tokens,
                            completion_tokens=0,
                            latency_ms=latency_ms,
                            success=True,
                        )

                        return result

                except httpx.HTTPStatusError as e:
                    last_error = e
                    last_status_code = e.response.status_code if e.response else None

                    # Don't retry on 4xx errors (except 429 rate limit)
                    if (
                        last_status_code
                        and 400 <= last_status_code < 500
                        and last_status_code != 429
                    ):
                        logger.warning(
                            f"OpenRouter embedding client error {last_status_code} with model {attempt_model}: {e}"
                        )
                        break  # Don't retry this model

                    # Rate limited - exponential backoff
                    if last_status_code == 429:
                        wait_time = self._retry_delay * (
                            self._retry_backoff**retry_attempt
                        )
                        logger.warning(
                            f"Rate limited, waiting {wait_time:.2f}s before retry {retry_attempt + 1}/{self._max_retries}"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    # Server error - retry with backoff
                    if last_status_code and last_status_code >= 500:
                        wait_time = self._retry_delay * (
                            self._retry_backoff**retry_attempt
                        )
                        logger.warning(
                            f"Server error {last_status_code}, retrying in {wait_time:.2f}s (attempt {retry_attempt + 1}/{self._max_retries})"
                        )
                        await asyncio.sleep(wait_time)
                        continue

                    # Other errors - try next model
                    logger.warning(
                        f"OpenRouter embedding error with model {attempt_model}: {e}"
                    )
                    break

                except httpx.RequestError as e:
                    last_error = e
                    # Network/connection errors - retry with backoff
                    wait_time = self._retry_delay * (self._retry_backoff**retry_attempt)
                    logger.warning(
                        f"Network error, retrying in {wait_time:.2f}s (attempt {retry_attempt + 1}/{self._max_retries}): {e}"
                    )
                    await asyncio.sleep(wait_time)
                    continue

                except Exception as e:
                    last_error = e
                    logger.error(
                        f"Unexpected embedding error with model {attempt_model}: {e}",
                        exc_info=True,
                    )
                    break  # Don't retry on unexpected errors

        # All models failed - record failure
        latency_ms = (time.time() - start_time) * 1000
        error_type = (
            "http_error" if isinstance(last_error, httpx.HTTPError) else "unknown_error"
        )
        error_message = str(last_error) if last_error else "All models failed"

        self._monitor.record_request(
            model=model,
            provider="OpenRouter",
            latency_ms=latency_ms,
            success=False,
            error_type=error_type,
            error_message=error_message,
        )

        # Raise appropriate error
        if last_error:
            if hasattr(last_error, "response") and last_error.response is not None:
                try:
                    error_data = last_error.response.json()
                    error_msg = error_data.get("error", {}).get(
                        "message", str(last_error)
                    )
                    raise Exception(f"OpenRouter embedding API error: {error_msg}")
                except (ValueError, AttributeError, KeyError):
                    pass
            raise Exception(f"OpenRouter embedding API error: {error_message}")
        else:
            raise Exception("OpenRouter embedding API error: All models failed")

    async def get_embedding_dimension(self, model: Optional[str] = None) -> int:
        """
        Get the dimension of embeddings for a model.

        Args:
            model: Model to check (default: current model)

        Returns:
            Embedding dimension
        """
        model = model or self.model
        metadata = self.MODEL_METADATA.get(model, {})
        return metadata.get("dimensions", 1536)  # Default to 1536

    def get_model_metadata(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metadata for an embedding model.

        Args:
            model: Model to check (default: current model)

        Returns:
            Model metadata dictionary
        """
        model = model or self.model
        return self.MODEL_METADATA.get(model, {})

    def calculate_cost(self, model: Optional[str] = None, tokens: int = 0) -> float:
        """
        Calculate cost for embedding generation.

        Args:
            model: Model to use (default: current model)
            tokens: Number of input tokens

        Returns:
            Cost in USD
        """
        model = model or self.model
        metadata = self.MODEL_METADATA.get(model, {})
        pricing = metadata.get("pricing", {})
        prompt_price = float(pricing.get("prompt", "0") or "0")

        # Cost per 1M tokens
        cost = (tokens / 1_000_000) * prompt_price
        return cost

    def list_models(self) -> List[str]:
        """List available embedding models"""
        return self.EMBEDDING_MODELS.copy()
