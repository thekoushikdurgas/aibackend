"""
LLM Service module - Multi-provider LLM support
"""

from .base import BaseLLMProvider, LLMResponse, LLMConfig
from .ollama import OllamaProvider
from .huggingface import HuggingFaceProvider
from .gemini import GeminiProvider
from .cerebras import CerebrasProvider
from .groq import GroqProvider
from .groq_safety import GroqSafetyService
from .groq_models import GroqModelSelector, GROQ_MODELS
from .nvidia import NVIDIAProvider  # Legacy - kept for backward compatibility
from app.services.nvidia import NVIDIAChatService
from .openrouter import OpenRouterProvider
from .factory import get_llm_provider, LLMProviderFactory

__all__ = [
    "BaseLLMProvider",
    "LLMResponse",
    "LLMConfig",
    "OllamaProvider",
    "HuggingFaceProvider",
    "GeminiProvider",
    "CerebrasProvider",
    "GroqProvider",
    "GroqSafetyService",
    "GroqModelSelector",
    "GROQ_MODELS",
    "NVIDIAProvider",  # Legacy
    "NVIDIAChatService",
    "OpenRouterProvider",
    "get_llm_provider",
    "LLMProviderFactory",
]
