"""
NVIDIA AI Services
Comprehensive NVIDIA AI API integration including chat, embeddings, vision, NIM, image, and video generation
"""

from .chat import NVIDIAChatService
from .embeddings import NVIDIAEmbeddingService
from .vision import NVIDIAVisionService
from .nim import NVIDIANIMService
from .image import NVIDIAImageService
from .video import NVIDIAVideoService
from .client import NVIDIAClient, BaseURLType
from .models import (
    NVIDIAModel,
    ModelCategory,
    ModelProvider,
    MODEL_REGISTRY,
    EMBEDDING_MODELS,
    MODELS_BY_ID,
    MODELS_BY_CATEGORY,
    MODELS_BY_PROVIDER,
    get_model,
    list_models,
    get_chat_models,
    get_vision_models,
    get_embedding_models,
    get_reasoning_models,
    get_code_models,
    validate_model,
    get_base_url_type,
)

__all__ = [
    "NVIDIAClient",
    "BaseURLType",
    "NVIDIAChatService",
    "NVIDIAEmbeddingService",
    "NVIDIAVisionService",
    "NVIDIANIMService",
    "NVIDIAImageService",
    "NVIDIAVideoService",
    "NVIDIAModel",
    "ModelCategory",
    "ModelProvider",
    "MODEL_REGISTRY",
    "EMBEDDING_MODELS",
    "MODELS_BY_ID",
    "MODELS_BY_CATEGORY",
    "MODELS_BY_PROVIDER",
    "get_model",
    "list_models",
    "get_chat_models",
    "get_vision_models",
    "get_embedding_models",
    "get_reasoning_models",
    "get_code_models",
    "validate_model",
    "get_base_url_type",
]
