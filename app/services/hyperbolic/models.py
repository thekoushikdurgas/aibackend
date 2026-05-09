"""
Hyperbolic API Model Registry
All available models and their metadata
"""

from enum import Enum
from typing import Any, Dict, List, Optional


class HyperbolicTextModel(str, Enum):
    """Text generation models"""

    # DeepSeek models
    DEEPSEEK_R1_ZERO = "deepseek-ai/DeepSeek-R1-Zero"
    DEEPSEEK_R1 = "deepseek-ai/DeepSeek-R1"
    DEEPSEEK_V2_5 = "deepseek-ai/DeepSeek-V2.5"
    DEEPSEEK_V3 = "deepseek-ai/DeepSeek-V3"

    # Meta Llama models
    LLAMA_3_2_3B = "meta-llama/Llama-3.2-3B-Instruct"
    LLAMA_3_70B = "meta-llama/Meta-Llama-3-70B-Instruct"
    LLAMA_3_1_8B = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    LLAMA_3_1_70B = "meta-llama/Meta-Llama-3.1-70B-Instruct"
    LLAMA_3_1_405B = "meta-llama/Meta-Llama-3.1-405B-Instruct"
    LLAMA_3_3_70B = "meta-llama/Llama-3.3-70B-Instruct"

    # Other models
    HERMES_3_70B = "NousResearch/Hermes-3-Llama-3.1-70B"
    QWEN_2_5_72B = "Qwen/Qwen2.5-72B-Instruct"


class HyperbolicVisionModel(str, Enum):
    """Vision/multimodal models"""

    LLAMA_3_2_90B_VISION = "meta-llama/Llama-3.2-90B-Vision-Instruct"
    PIXTRAL_12B = "mistralai/Pixtral-12B-2409"
    QWEN_2_VL_7B = "Qwen/Qwen2-VL-7B-Instruct"
    QWEN_2_VL_72B = "Qwen/Qwen2-VL-72B-Instruct"


class HyperbolicImageModel(str, Enum):
    """Image generation models"""

    FLUX_1_DEV = "FLUX.1-dev"
    SD1_5 = "SD1.5"
    SD2 = "SD2"
    SDXL_1_0_BASE = "SDXL1.0-base"
    SDXL_TURBO = "SDXL-turbo"
    SSD = "SSD"


class HyperbolicAudioModel(str, Enum):
    """Audio generation models"""

    MELO_TTS = "Melo TTS"


# Model lists for easy access
TEXT_MODELS: List[str] = [model.value for model in HyperbolicTextModel]
VISION_MODELS: List[str] = [model.value for model in HyperbolicVisionModel]
IMAGE_MODELS: List[str] = [model.value for model in HyperbolicImageModel]
AUDIO_MODELS: List[str] = [model.value for model in HyperbolicAudioModel]

# Model metadata
MODEL_METADATA: Dict[str, Dict[str, Any]] = {
    # Text models
    "deepseek-ai/DeepSeek-R1-Zero": {
        "type": "text",
        "capabilities": ["reasoning", "chat"],
        "context_window": 128000,
    },
    "deepseek-ai/DeepSeek-R1": {
        "type": "text",
        "capabilities": ["reasoning", "chat"],
        "context_window": 128000,
    },
    "deepseek-ai/DeepSeek-V2.5": {
        "type": "text",
        "capabilities": ["chat", "code"],
        "context_window": 128000,
    },
    "deepseek-ai/DeepSeek-V3": {
        "type": "text",
        "capabilities": ["reasoning", "chat", "code"],
        "context_window": 128000,
    },
    "meta-llama/Llama-3.2-3B-Instruct": {
        "type": "text",
        "capabilities": ["chat"],
        "context_window": 128000,
    },
    "meta-llama/Meta-Llama-3-70B-Instruct": {
        "type": "text",
        "capabilities": ["chat"],
        "context_window": 8192,
    },
    "meta-llama/Meta-Llama-3.1-8B-Instruct": {
        "type": "text",
        "capabilities": ["chat"],
        "context_window": 128000,
    },
    "meta-llama/Meta-Llama-3.1-70B-Instruct": {
        "type": "text",
        "capabilities": ["chat"],
        "context_window": 128000,
    },
    "meta-llama/Meta-Llama-3.1-405B-Instruct": {
        "type": "text",
        "capabilities": ["chat"],
        "context_window": 128000,
    },
    "meta-llama/Llama-3.3-70B-Instruct": {
        "type": "text",
        "capabilities": ["chat"],
        "context_window": 128000,
    },
    "NousResearch/Hermes-3-Llama-3.1-70B": {
        "type": "text",
        "capabilities": ["chat"],
        "context_window": 128000,
    },
    "Qwen/Qwen2.5-72B-Instruct": {
        "type": "text",
        "capabilities": ["chat", "code"],
        "context_window": 128000,
    },
    # Vision models
    "meta-llama/Llama-3.2-90B-Vision-Instruct": {
        "type": "vision",
        "capabilities": ["vision", "chat"],
        "context_window": 128000,
    },
    "mistralai/Pixtral-12B-2409": {
        "type": "vision",
        "capabilities": ["vision", "chat"],
        "context_window": 128000,
    },
    "Qwen/Qwen2-VL-7B-Instruct": {
        "type": "vision",
        "capabilities": ["vision", "chat"],
        "context_window": 128000,
    },
    "Qwen/Qwen2-VL-72B-Instruct": {
        "type": "vision",
        "capabilities": ["vision", "chat"],
        "context_window": 128000,
    },
    # Image models
    "FLUX.1-dev": {
        "type": "image",
        "capabilities": ["text-to-image"],
        "max_resolution": "2048x2048",
    },
    "SD1.5": {
        "type": "image",
        "capabilities": ["text-to-image"],
        "max_resolution": "1024x1024",
    },
    "SD2": {
        "type": "image",
        "capabilities": ["text-to-image"],
        "max_resolution": "1024x1024",
    },
    "SDXL1.0-base": {
        "type": "image",
        "capabilities": ["text-to-image"],
        "max_resolution": "1024x1024",
    },
    "SDXL-turbo": {
        "type": "image",
        "capabilities": ["text-to-image"],
        "max_resolution": "1024x1024",
    },
    "SSD": {
        "type": "image",
        "capabilities": ["text-to-image"],
        "max_resolution": "1024x1024",
    },
    # Audio models
    "Melo TTS": {
        "type": "audio",
        "capabilities": ["text-to-speech"],
        "languages": [
            "en",
            "es",
            "fr",
            "de",
            "it",
            "pt",
            "pl",
            "tr",
            "ru",
            "nl",
            "cs",
            "ar",
            "zh",
            "ja",
            "hu",
            "ko",
        ],
    },
}


def get_model_info(model_name: str) -> Optional[Dict[str, Any]]:
    """Get metadata for a specific model"""
    return MODEL_METADATA.get(model_name)


def is_text_model(model_name: str) -> bool:
    """Check if model is a text generation model"""
    return model_name in TEXT_MODELS


def is_vision_model(model_name: str) -> bool:
    """Check if model is a vision model"""
    return model_name in VISION_MODELS


def is_image_model(model_name: str) -> bool:
    """Check if model is an image generation model"""
    return model_name in IMAGE_MODELS


def is_audio_model(model_name: str) -> bool:
    """Check if model is an audio generation model"""
    return model_name in AUDIO_MODELS
