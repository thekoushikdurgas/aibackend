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
from .bedrock import BedrockProvider
from .dashscope import DashScopeProvider
from .watsonx import WatsonxProvider
from .vertex import VertexProvider
from .manifest_compat import create_manifest_compat_provider
from .provider_registry import get_manifest_entry, register_compat_providers

logger = logging.getLogger(__name__)

_STATIC_IDS = frozenset(
    {
        "ollama",
        "huggingface",
        "gemini",
        "vertex",
        "ai21",
        "groq",
        "nvidia",
        "cerebras",
        "openrouter",
        "fireworks",
        "deepinfra",
        "anyscale",
        "cohere",
        "hyperbolic",
        "reka",
        "bedrock",
        "dashscope",
        "watsonx",
    }
)


class LLMProviderFactory:
    """Factory for creating and managing LLM providers."""

    _providers: Dict[str, Type[BaseLLMProvider]] = {
        "ollama": OllamaProvider,
        "huggingface": HuggingFaceProvider,
        "gemini": GeminiProvider,
        "vertex": VertexProvider,
        "ai21": AI21Provider,
        "groq": GroqProvider,
        "nvidia": NVIDIAChatService,
        "cerebras": CerebrasProvider,
        "openrouter": OpenRouterProvider,
        "fireworks": FireworksProvider,
        "deepinfra": DeepInfraProvider,
        "anyscale": AnyscaleProvider,
        "cohere": CohereProvider,
        "hyperbolic": HyperbolicProvider,
        "reka": RekaProvider,
        "bedrock": BedrockProvider,
        "dashscope": DashScopeProvider,
        "watsonx": WatsonxProvider,
    }

    _instances: Dict[str, BaseLLMProvider] = {}

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[BaseLLMProvider]):
        cls._providers[name] = provider_class
        logger.info("Registered LLM provider: %s", name)

    @classmethod
    def get_provider(
        cls, provider_name: Optional[str] = None, **kwargs
    ) -> BaseLLMProvider:
        provider_name = (provider_name or settings.default_llm_provider).lower()

        cache_key = f"{provider_name}_{hash(frozenset(kwargs.items()))}"
        if cache_key in cls._instances:
            return cls._instances[cache_key]

        if provider_name == "huggingface":
            inference_provider = (
                kwargs.pop("provider", None) or settings.huggingface_inference_provider
            )
            kwargs["provider"] = inference_provider

        if provider_name in cls._providers:
            instance = cls._providers[provider_name](**kwargs)
        else:
            entry = get_manifest_entry(provider_name)
            if entry and entry.get("implementation") == "openai_compat":
                instance = create_manifest_compat_provider(provider_name, **kwargs)
            else:
                available = ", ".join(
                    sorted(set(cls._providers) | _manifest_compat_ids())
                )
                raise ValueError(
                    f"Unknown provider: {provider_name}. Available: {available}"
                )

        cls._instances[cache_key] = instance
        logger.info("Created LLM provider instance: %s", provider_name)
        return instance

    @classmethod
    def clear_cache(cls):
        cls._instances.clear()

    @classmethod
    def list_providers(cls) -> list:
        return sorted(set(cls._providers.keys()) | _manifest_compat_ids())

    @classmethod
    async def get_healthy_provider(cls) -> Optional[BaseLLMProvider]:
        providers_to_try = list(
            dict.fromkeys(
                [
                    settings.default_llm_provider,
                    "openrouter",
                    "openai",
                    "groq",
                    "cerebras",
                    "sambanova",
                    "cohere",
                    "ollama",
                    "deepseek",
                    "mistral",
                    "gemini",
                    "nvidia",
                ]
            )
        )
        for name in providers_to_try:
            try:
                provider = cls.get_provider(name)
                if await provider.health_check():
                    return provider
            except Exception as e:
                logger.warning("Provider %s unavailable: %s", name, e)
        return None


def _manifest_compat_ids() -> set[str]:
    from .provider_registry import list_manifest_providers

    return {
        p["id"]
        for p in list_manifest_providers(implementation="openai_compat")
        if p["id"] not in _STATIC_IDS
    }


register_compat_providers(LLMProviderFactory)


def get_llm_provider(provider_name: Optional[str] = None) -> BaseLLMProvider:
    return LLMProviderFactory.get_provider(provider_name)
