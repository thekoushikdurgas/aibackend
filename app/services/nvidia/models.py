"""
NVIDIA AI Model Registry
Complete catalog of all available NVIDIA models with metadata
"""

from dataclasses import dataclass
from typing import List, Optional, Set
from enum import Enum


class ModelCategory(str, Enum):
    """Model category types"""

    CHAT = "chat"
    EMBEDDING = "embedding"
    VISION = "vision"
    REASONING = "reasoning"
    CODE = "code"
    MULTIMODAL = "multimodal"


class ModelProvider(str, Enum):
    """Model provider/origin"""

    NVIDIA = "nvidia"
    META = "meta"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    MISTRAL = "mistralai"
    DEEPSEEK = "deepseek-ai"
    OPENAI = "openai"
    QWEN = "qwen"
    SNOWFLAKE = "snowflake"
    MOONSHOT = "moonshotai"


@dataclass
class NVIDIAModel:
    """NVIDIA model metadata"""

    id: str
    category: ModelCategory
    provider: ModelProvider
    capabilities: Set[str]
    context_length: Optional[int] = None
    base_url_type: str = "integrate"  # "integrate" or "genai"
    description: Optional[str] = None
    reasoning: bool = False
    vision: bool = False
    code: bool = False
    streaming: bool = True

    def __post_init__(self):
        """Convert capabilities to set if needed"""
        if isinstance(self.capabilities, list):
            self.capabilities = set(self.capabilities)


# Complete model registry from NVIDIA AI API Postman collection
MODEL_REGISTRY: List[NVIDIAModel] = [
    # NVIDIA Models
    NVIDIAModel(
        id="nvidia/nemotron-4-340b-instruct",
        category=ModelCategory.CHAT,
        provider=ModelProvider.NVIDIA,
        capabilities={"chat", "instruction", "general_purpose"},
        context_length=131072,
        description="NVIDIA's flagship 340B parameter instruction-tuned model",
    ),
    NVIDIAModel(
        id="nvidia/llama-3.1-nemotron-ultra-253b-v1",
        category=ModelCategory.CHAT,
        provider=ModelProvider.NVIDIA,
        capabilities={"chat", "instruction", "long_context"},
        context_length=131072,
        description="Ultra-large 253B parameter model with extended context",
    ),
    NVIDIAModel(
        id="nvidia/llama-3.3-nemotron-super-49b-v1",
        category=ModelCategory.CHAT,
        provider=ModelProvider.NVIDIA,
        capabilities={"chat", "instruction", "general_purpose"},
        context_length=131072,
        description="Super 49B parameter model optimized for quality and speed",
    ),
    NVIDIAModel(
        id="nvidia/llama-3.3-nemotron-super-49b-v1.5",
        category=ModelCategory.CHAT,
        provider=ModelProvider.NVIDIA,
        capabilities={"chat", "instruction", "general_purpose"},
        context_length=131072,
        description="Updated version of the 49B super model",
    ),
    NVIDIAModel(
        id="nv-mistralai/mistral-nemo-12b-instruct",
        category=ModelCategory.CHAT,
        provider=ModelProvider.NVIDIA,
        capabilities={"chat", "instruction"},
        context_length=32768,
        description="NVIDIA-optimized Mistral 12B instruction model",
    ),
    # Meta Models
    NVIDIAModel(
        id="meta/llama2-70b",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "general_purpose"},
        context_length=4096,
        description="Meta's LLaMA 2 70B base model",
    ),
    NVIDIAModel(
        id="meta/llama3-8b",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "general_purpose"},
        context_length=8192,
        description="Meta's LLaMA 3 8B base model",
    ),
    NVIDIAModel(
        id="meta/llama3-8b-instruct",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "instruction"},
        context_length=8192,
        description="Meta's LLaMA 3 8B instruction-tuned model",
    ),
    NVIDIAModel(
        id="meta/llama3-70b",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "general_purpose"},
        context_length=8192,
        description="Meta's LLaMA 3 70B base model",
    ),
    NVIDIAModel(
        id="meta/llama3-70b-instruct",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "instruction"},
        context_length=8192,
        description="Meta's LLaMA 3 70B instruction-tuned model",
    ),
    NVIDIAModel(
        id="meta/llama-3.1-405b-instruct",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "instruction", "long_context"},
        context_length=131072,
        description="Meta's largest 405B instruction model with extended context",
    ),
    NVIDIAModel(
        id="meta/llama-3.2-1b-instruct",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "instruction"},
        context_length=128000,
        description="Ultra-lightweight 1B instruction model",
    ),
    NVIDIAModel(
        id="meta/llama-3.2-3b-instruct",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "instruction"},
        context_length=128000,
        description="Lightweight 3B instruction model",
    ),
    NVIDIAModel(
        id="meta/llama-3.2-11b-vision-instruct",
        category=ModelCategory.VISION,
        provider=ModelProvider.META,
        capabilities={"chat", "vision", "multimodal"},
        context_length=128000,
        vision=True,
        description="11B vision model for image understanding",
    ),
    NVIDIAModel(
        id="meta/llama-3.2-90b-vision-instruct",
        category=ModelCategory.VISION,
        provider=ModelProvider.META,
        capabilities={"chat", "vision", "multimodal"},
        context_length=128000,
        vision=True,
        description="90B vision model for advanced image understanding",
    ),
    NVIDIAModel(
        id="meta/llama-3.3-70b-instruct",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "instruction"},
        context_length=131072,
        description="Latest 70B instruction model",
    ),
    NVIDIAModel(
        id="meta/llama-4-scout-17b-16e-instruct",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "instruction"},
        context_length=131072,
        description="Scout 17B model with 16 expert architecture",
    ),
    NVIDIAModel(
        id="meta/llama-4-maverick-17b-128e-instruct",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "instruction"},
        context_length=131072,
        description="Maverick 17B model with 128 expert architecture",
    ),
    NVIDIAModel(
        id="meta/codellama-70b",
        category=ModelCategory.CODE,
        provider=ModelProvider.META,
        capabilities={"code", "chat"},
        context_length=16384,
        code=True,
        description="70B code generation model",
    ),
    # Google Models
    NVIDIAModel(
        id="google/gemma-2b",
        category=ModelCategory.CHAT,
        provider=ModelProvider.GOOGLE,
        capabilities={"chat", "general_purpose"},
        context_length=8192,
        description="Google's lightweight 2B Gemma model",
    ),
    NVIDIAModel(
        id="google/gemma-7b",
        category=ModelCategory.CHAT,
        provider=ModelProvider.GOOGLE,
        capabilities={"chat", "general_purpose"},
        context_length=8192,
        description="Google's 7B Gemma model",
    ),
    NVIDIAModel(
        id="google/gemma-2-9b-it",
        category=ModelCategory.CHAT,
        provider=ModelProvider.GOOGLE,
        capabilities={"chat", "instruction"},
        context_length=8192,
        description="Google's Gemma 2 9B instruction-tuned model",
    ),
    NVIDIAModel(
        id="google/gemma-3-27b-it",
        category=ModelCategory.CHAT,
        provider=ModelProvider.GOOGLE,
        capabilities={"chat", "instruction"},
        context_length=8192,
        description="Google's Gemma 3 27B instruction-tuned model",
    ),
    NVIDIAModel(
        id="google/codegemma-7b",
        category=ModelCategory.CODE,
        provider=ModelProvider.GOOGLE,
        capabilities={"code", "chat"},
        context_length=8192,
        code=True,
        description="Google's 7B code generation model",
    ),
    # Microsoft Models
    NVIDIAModel(
        id="microsoft/phi-3-mini-128k-instruct",
        category=ModelCategory.CHAT,
        provider=ModelProvider.MICROSOFT,
        capabilities={"chat", "instruction", "long_context"},
        context_length=131072,
        description="Microsoft's Phi-3 mini with 128K context",
    ),
    NVIDIAModel(
        id="microsoft/phi-3.5-moe-instruct",
        category=ModelCategory.CHAT,
        provider=ModelProvider.MICROSOFT,
        capabilities={"chat", "instruction"},
        context_length=131072,
        description="Microsoft's Phi-3.5 MoE instruction model",
    ),
    NVIDIAModel(
        id="microsoft/phi-4-multimodal-instruct",
        category=ModelCategory.VISION,
        provider=ModelProvider.MICROSOFT,
        capabilities={"chat", "vision", "multimodal"},
        context_length=131072,
        vision=True,
        description="Microsoft's Phi-4 multimodal vision model",
    ),
    # Mistral Models
    NVIDIAModel(
        id="mistralai/mistral-7b-instruct-v0.2",
        category=ModelCategory.CHAT,
        provider=ModelProvider.MISTRAL,
        capabilities={"chat", "instruction"},
        context_length=32768,
        description="Mistral 7B instruction model v0.2",
    ),
    NVIDIAModel(
        id="mistralai/mistral-large",
        category=ModelCategory.CHAT,
        provider=ModelProvider.MISTRAL,
        capabilities={"chat", "instruction"},
        context_length=32768,
        description="Mistral's large instruction model",
    ),
    NVIDIAModel(
        id="mistralai/mixtral-8x22b-instruct-v0.1",
        category=ModelCategory.CHAT,
        provider=ModelProvider.MISTRAL,
        capabilities={"chat", "instruction"},
        context_length=65536,
        description="Mistral's Mixtral 8x22B MoE instruction model",
    ),
    # DeepSeek Models
    NVIDIAModel(
        id="deepseek-ai/deepseek-r1",
        category=ModelCategory.REASONING,
        provider=ModelProvider.DEEPSEEK,
        capabilities={"chat", "reasoning", "problem_solving"},
        context_length=64000,
        reasoning=True,
        description="DeepSeek R1 reasoning model for complex problem solving",
    ),
    # OpenAI Models
    NVIDIAModel(
        id="openai/gpt-oss-120b",
        category=ModelCategory.CHAT,
        provider=ModelProvider.OPENAI,
        capabilities={"chat", "general_purpose"},
        context_length=131072,
        description="OpenAI's open-source 120B GPT model",
    ),
    NVIDIAModel(
        id="openai/gpt-oss-20b",
        category=ModelCategory.CHAT,
        provider=ModelProvider.OPENAI,
        capabilities={"chat", "general_purpose"},
        context_length=131072,
        description="OpenAI's open-source 20B GPT model",
    ),
    # Qwen Models
    NVIDIAModel(
        id="qwen/qwen3-235b-a22b",
        category=ModelCategory.CHAT,
        provider=ModelProvider.QWEN,
        capabilities={"chat", "instruction"},
        context_length=131072,
        description="Qwen 3 235B model with 22B active parameters",
    ),
    # Snowflake Models
    NVIDIAModel(
        id="snowflake/arctic",
        category=ModelCategory.CHAT,
        provider=ModelProvider.SNOWFLAKE,
        capabilities={"chat", "instruction"},
        context_length=131072,
        description="Snowflake's Arctic instruction model",
    ),
    # Moonshot Models
    NVIDIAModel(
        id="moonshotai/kimi-k2-instruct",
        category=ModelCategory.CHAT,
        provider=ModelProvider.MOONSHOT,
        capabilities={"chat", "instruction", "long_context"},
        context_length=131072,
        description="Moonshot's Kimi K2 instruction model with long context",
    ),
]

# Embedding Models (from NVIDIA GenAI API)
EMBEDDING_MODELS: List[NVIDIAModel] = [
    NVIDIAModel(
        id="nvidia/nv-embedqa-e5-v5",
        category=ModelCategory.EMBEDDING,
        provider=ModelProvider.NVIDIA,
        capabilities={"embedding", "semantic_search", "rag"},
        base_url_type="genai",
        description="NVIDIA embedding model optimized for Q&A and semantic search",
    ),
    NVIDIAModel(
        id="nvidia/nv-embed-v2",
        category=ModelCategory.EMBEDDING,
        provider=ModelProvider.NVIDIA,
        capabilities={"embedding", "semantic_search", "rag"},
        base_url_type="genai",
        description="NVIDIA general-purpose embedding model v2",
    ),
]

# Model lookup dictionaries
MODELS_BY_ID: dict[str, NVIDIAModel] = {
    model.id: model for model in MODEL_REGISTRY + EMBEDDING_MODELS
}
MODELS_BY_CATEGORY: dict[ModelCategory, List[NVIDIAModel]] = {}
MODELS_BY_PROVIDER: dict[ModelProvider, List[NVIDIAModel]] = {}

# Build category and provider indexes
for model in MODEL_REGISTRY + EMBEDDING_MODELS:
    if model.category not in MODELS_BY_CATEGORY:
        MODELS_BY_CATEGORY[model.category] = []
    MODELS_BY_CATEGORY[model.category].append(model)

    if model.provider not in MODELS_BY_PROVIDER:
        MODELS_BY_PROVIDER[model.provider] = []
    MODELS_BY_PROVIDER[model.provider].append(model)


def get_model(model_id: str) -> Optional[NVIDIAModel]:
    """Get model metadata by ID"""
    return MODELS_BY_ID.get(model_id)


def list_models(
    category: Optional[ModelCategory] = None,
    provider: Optional[ModelProvider] = None,
    vision: Optional[bool] = None,
    reasoning: Optional[bool] = None,
    code: Optional[bool] = None,
) -> List[NVIDIAModel]:
    """
    List models with optional filters

    Args:
        category: Filter by model category
        provider: Filter by provider
        vision: Filter by vision capability
        reasoning: Filter by reasoning capability
        code: Filter by code capability

    Returns:
        List of matching models
    """
    models = MODEL_REGISTRY + EMBEDDING_MODELS

    if category:
        models = [m for m in models if m.category == category]

    if provider:
        models = [m for m in models if m.provider == provider]

    if vision is not None:
        models = [m for m in models if m.vision == vision]

    if reasoning is not None:
        models = [m for m in models if m.reasoning == reasoning]

    if code is not None:
        models = [m for m in models if m.code == code]

    return models


def get_chat_models() -> List[str]:
    """Get list of all chat model IDs"""
    return [m.id for m in list_models(category=ModelCategory.CHAT)]


def get_vision_models() -> List[str]:
    """Get list of all vision model IDs"""
    return [m.id for m in list_models(vision=True)]


def get_embedding_models() -> List[str]:
    """Get list of all embedding model IDs"""
    return [m.id for m in list_models(category=ModelCategory.EMBEDDING)]


def get_reasoning_models() -> List[str]:
    """Get list of all reasoning model IDs"""
    return [m.id for m in list_models(reasoning=True)]


def get_code_models() -> List[str]:
    """Get list of all code model IDs"""
    return [m.id for m in list_models(code=True)]


def validate_model(model_id: str) -> bool:
    """Check if a model ID is valid"""
    return model_id in MODELS_BY_ID


def get_base_url_type(model_id: str) -> str:
    """Get the base URL type (integrate or genai) for a model"""
    model = get_model(model_id)
    if model:
        return model.base_url_type
    # Default to integrate for unknown models
    return "integrate"
