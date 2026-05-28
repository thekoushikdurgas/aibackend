"""
Ollama Services
Comprehensive Ollama API integration with localhost and cloud support
"""

from .client import OllamaClient, OllamaMode
from .models import (
    OllamaModel,
    ModelCategory,
    ModelProvider,
    MODEL_REGISTRY,
    get_model,
    list_models,
    validate_model,
    get_chat_models,
    get_code_models,
)
from .generate import OllamaGenerateService
from .model_management import OllamaModelService
from .lifecycle import OllamaLifecycleService
from .web_search import OllamaWebSearchService

__all__ = [
    "OllamaClient",
    "OllamaMode",
    "OllamaModel",
    "ModelCategory",
    "ModelProvider",
    "MODEL_REGISTRY",
    "get_model",
    "list_models",
    "validate_model",
    "get_chat_models",
    "get_code_models",
    "OllamaGenerateService",
    "OllamaModelService",
    "OllamaLifecycleService",
    "OllamaWebSearchService",
]
