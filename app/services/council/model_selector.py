"""
Smart model selection for council based on health and availability
"""

import logging
import asyncio
from typing import List, Dict, Optional

from app.config import settings
from app.services.llm import LLMProviderFactory

logger = logging.getLogger(__name__)


class ModelSelector:
    """
    Selects models for council based on health checks and performance.
    """

    # Cache for health check results (1 minute TTL for failed, 5 minutes for success)
    _health_cache: Dict[str, tuple] = {}  # provider -> (is_healthy, timestamp)
    _cache_ttl_success: float = 300.0  # 5 minutes for healthy
    _cache_ttl_failure: float = 60.0  # 1 minute for unhealthy (retry sooner)

    # Preferred providers in order of preference (fastest/reliable first)
    PREFERRED_PROVIDERS = [
        "openrouter",  # Unified access to 100+ models with auto-routing
        "groq",  # Very fast
        "gemini",  # Fast and reliable
        "hyperbolic",  # Open access AI cloud with diverse models
        "ollama",  # Local, fast if available
        "cerebras",  # Fast inference
        "nvidia",  # Good performance
        "huggingface",  # Fallback
        "ai21",  # Fallback
    ]

    # Providers that are good for chairman role (fast, reliable)
    CHAIRMAN_CANDIDATES = [
        "openrouter",
        "gemini",
        "groq",
        "hyperbolic",
        "cerebras",
        "nvidia",
    ]

    @classmethod
    async def _check_provider_health(cls, provider_name: str) -> bool:
        """
        Check if a provider is healthy, with caching.

        Args:
            provider_name: Name of the provider

        Returns:
            True if healthy, False otherwise
        """
        # Check cache first
        if provider_name in cls._health_cache:
            is_healthy, timestamp = cls._health_cache[provider_name]
            import time

            # Use different TTL for success vs failure
            ttl = cls._cache_ttl_success if is_healthy else cls._cache_ttl_failure
            if time.time() - timestamp < ttl:
                return is_healthy

        # Perform health check
        try:
            provider = LLMProviderFactory.get_provider(provider_name)
            is_healthy = await asyncio.wait_for(
                provider.health_check(),
                timeout=10.0,  # Increased from 5s to 10s for slower APIs
            )

            # Update cache
            import time

            cls._health_cache[provider_name] = (is_healthy, time.time())

            return is_healthy
        except asyncio.TimeoutError:
            # Don't cache timeouts - network might be temporarily slow
            logger.warning(f"Health check timeout for {provider_name} (not cached)")
            return False
        except Exception as e:
            # Cache other errors (like auth failures) but with shorter TTL
            logger.debug(f"Health check failed for {provider_name}: {e}")
            import time

            cls._health_cache[provider_name] = (False, time.time())
            return False

    @classmethod
    async def _check_providers_parallel(
        cls, provider_names: List[str]
    ) -> Dict[str, bool]:
        """
        Check multiple providers in parallel.

        Args:
            provider_names: List of provider names to check

        Returns:
            Dict mapping provider name to health status
        """
        tasks = {name: cls._check_provider_health(name) for name in provider_names}

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        return {
            name: result if isinstance(result, bool) else False
            for name, result in zip(tasks.keys(), results)
        }

    @classmethod
    async def select_council_models(
        cls, min_models: int | None = None, max_models: int | None = None
    ) -> List[str]:
        """
        Select models for the council based on health and availability.

        Args:
            min_models: Minimum number of models to select (default from config)
            max_models: Maximum number of models to select (default from config)

        Returns:
            List of provider names selected for council
        """
        min_models = (
            min_models
            if min_models is not None
            else int(getattr(settings, "council_min_models", 3) or 3)
        )
        max_models = (
            max_models
            if max_models is not None
            else int(getattr(settings, "council_max_models", 5) or 5)
        )

        # Get preferred providers in order
        providers_to_check = [
            p
            for p in cls.PREFERRED_PROVIDERS
            if p in LLMProviderFactory.list_providers()
        ]

        if not providers_to_check:
            logger.warning("No providers available in factory")
            return []

        # Check health of all preferred providers in parallel
        logger.info(f"Checking health of {len(providers_to_check)} providers...")
        health_status = await cls._check_providers_parallel(providers_to_check)

        # Filter to healthy providers
        healthy_providers = [
            p for p in providers_to_check if health_status.get(p, False)
        ]

        if len(healthy_providers) < min_models:
            logger.warning(
                f"Only {len(healthy_providers)} healthy providers found, "
                f"minimum requested: {min_models}"
            )
            # Return what we have, or empty if none
            return healthy_providers[:max_models] if healthy_providers else []

        # Select up to max_models
        selected = healthy_providers[:max_models]

        logger.info(f"Selected {len(selected)} models for council: {selected}")
        return selected

    @classmethod
    async def select_chairman_model(cls) -> Optional[str]:
        """
        Select the best model for chairman role (fast, reliable).

        Returns:
            Provider name for chairman, or None if none available
        """
        # Check chairman candidates
        candidates = [
            p
            for p in cls.CHAIRMAN_CANDIDATES
            if p in LLMProviderFactory.list_providers()
        ]

        if not candidates:
            # Fallback to any available provider
            candidates = LLMProviderFactory.list_providers()

        if not candidates:
            return None

        # Check health of candidates
        health_status = await cls._check_providers_parallel(candidates)

        # Prefer configured chairman if available and healthy
        preferred = getattr(settings, "council_preferred_chairman", "gemini")
        if preferred in health_status and health_status[preferred]:
            return preferred

        # Return first healthy candidate
        for candidate in candidates:
            if health_status.get(candidate, False):
                return candidate

        # If no healthy candidates, try any provider
        all_providers = LLMProviderFactory.list_providers()
        for provider in all_providers:
            if await cls._check_provider_health(provider):
                logger.warning(f"Using fallback chairman: {provider}")
                return provider

        return None

    @classmethod
    def clear_health_cache(cls):
        """Clear the health check cache"""
        cls._health_cache.clear()
        logger.info("Cleared model health cache")


# Convenience functions
async def select_council_models(
    min_models: int | None = None, max_models: int | None = None
) -> List[str]:
    """Select council models"""
    return await ModelSelector.select_council_models(min_models, max_models)


async def select_chairman_model() -> Optional[str]:
    """Select chairman model"""
    return await ModelSelector.select_chairman_model()
