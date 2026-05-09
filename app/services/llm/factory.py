"""
LLM Provider Factory
"""

import logging
from typing import Dict, Optional, Type

from app.config import settings
from .base import BaseLLMProvider
from .ollama import OllamaProvider
from .huggingface import HuggingFaceProvider
from .gemini import GeminiProvider
from .ai21 import AI21Provider
from .groq import GroqProvider
from app.services.nvidia import NVIDIAChatService
from .cerebras import CerebrasProvider
from .openrouter import OpenRouterProvider
from .cohere import CohereProvider
from .fireworks import FireworksProvider
from .deepinfra import DeepInfraProvider
from .anyscale import AnyscaleProvider
from .hyperbolic import HyperbolicProvider
from .reka import RekaProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """
    Factory for creating and managing LLM providers.
    Supports lazy initialization and provider switching.
    """

    # Registry of available providers
    _providers: Dict[str, Type[BaseLLMProvider]] = {
        "ollama": OllamaProvider,
        "huggingface": HuggingFaceProvider,
        "gemini": GeminiProvider,
        "ai21": AI21Provider,
        "groq": GroqProvider,
        "nvidia": NVIDIAChatService,  # Use new enhanced chat service
        "cerebras": CerebrasProvider,
        "openrouter": OpenRouterProvider,
        "fireworks": FireworksProvider,
        "deepinfra": DeepInfraProvider,
        "anyscale": AnyscaleProvider,
        "cohere": CohereProvider,
        "hyperbolic": HyperbolicProvider,
        "reka": RekaProvider,
    }

    # Cache of initialized providers
    _instances: Dict[str, BaseLLMProvider] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseLLMProvider]):
        """Register a new provider type"""
        cls._providers[name] = provider_class
        logger.info(f"Registered LLM provider: {name}")

    @classmethod
    def get_provider(
        cls, provider_name: Optional[str] = None, **kwargs
    ) -> BaseLLMProvider:
        """
        Get or create a provider instance.

        Args:
            provider_name: Name of the provider (ollama, huggingface, gemini)
            **kwargs: Additional arguments to pass to provider constructor
                - For huggingface: 'provider' (hf, cerebras, groq, etc.) and 'model'

        Returns:
            Initialized provider instance
        """
        provider_name = provider_name or settings.default_llm_provider
        provider_name = provider_name.lower()

        # Check if provider exists
        if provider_name not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ValueError(
                f"Unknown provider: {provider_name}. Available: {available}"
            )

        # For HuggingFace, support provider parameter for inference provider selection
        if provider_name == "huggingface":
            # Extract provider (inference provider) from kwargs if present
            inference_provider = (
                kwargs.pop("provider", None) or settings.huggingface_inference_provider
            )
            kwargs["provider"] = inference_provider

        # Create cache key
        cache_key = f"{provider_name}_{hash(frozenset(kwargs.items()))}"

        # Return cached instance if available
        if cache_key in cls._instances:
            return cls._instances[cache_key]

        # Create new instance
        provider_class = cls._providers[provider_name]
        instance = provider_class(**kwargs)

        # Cache the instance
        cls._instances[cache_key] = instance
        logger.info(f"Created LLM provider instance: {provider_name}")

        return instance

    @classmethod
    def clear_cache(cls):
        """Clear the provider cache"""
        cls._instances.clear()
        logger.info("Cleared LLM provider cache")

    @classmethod
    def list_providers(cls) -> list:
        """List available provider names"""
        return list(cls._providers.keys())

    @classmethod
    async def get_healthy_provider(cls) -> Optional[BaseLLMProvider]:
        """
        Get the first healthy provider.
        Tries providers in order: default, ollama, huggingface, gemini
        """
        # Order of preference
        providers_to_try = [
            settings.default_llm_provider,
            "openrouter",
            "cohere",
            "hyperbolic",
            "reka",
            "ollama",
            "groq",
            "fireworks",
            "deepinfra",
            "anyscale",
            "huggingface",
            "gemini",
            "nvidia",
            "cerebras",
        ]

        # Remove duplicates while preserving order
        seen = set()
        providers_to_try = [
            p for p in providers_to_try if not (p in seen or seen.add(p))
        ]

        for provider_name in providers_to_try:
            try:
                provider = cls.get_provider(provider_name)
                if await provider.health_check():
                    logger.info(f"Using healthy provider: {provider_name}")
                    return provider
            except Exception as e:
                logger.warning(f"Provider {provider_name} unavailable: {e}")
                continue

        return None


def get_llm_provider(provider_name: Optional[str] = None) -> BaseLLMProvider:
    """
    Convenience function to get an LLM provider.

    Args:
        provider_name: Optional provider name, uses default if not specified

    Returns:
        LLM provider instance
    """
    return LLMProviderFactory.get_provider(provider_name)
