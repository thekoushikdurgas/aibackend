"""
Ollama Model Registry
Complete catalog of all available Ollama models with metadata
"""

from dataclasses import dataclass
from typing import List, Optional, Set
from enum import Enum


class ModelCategory(str, Enum):
    """Model category types"""

    CHAT = "chat"
    CODE = "code"
    VISION = "vision"
    EMBEDDING = "embedding"
    REASONING = "reasoning"


class ModelProvider(str, Enum):
    """Model provider/origin"""

    META = "meta"
    GOOGLE = "google"
    MICROSOFT = "microsoft"
    MISTRAL = "mistralai"
    DEEPSEEK = "deepseek-ai"
    QWEN = "qwen"
    OPENAI = "openai"
    PHI = "microsoft"
    GEMMA = "google"


@dataclass
class OllamaModel:
    """Ollama model metadata"""

    id: str
    category: ModelCategory
    provider: ModelProvider
    capabilities: Set[str]
    context_length: Optional[int] = None
    cloud_only: bool = False  # True if only available in cloud mode
    localhost_only: bool = False  # True if only available in localhost mode
    description: Optional[str] = None
    reasoning: bool = False
    vision: bool = False
    code: bool = False
    streaming: bool = True

    def __post_init__(self):
        """Convert capabilities to set if needed"""
        if isinstance(self.capabilities, list):
            self.capabilities = set(self.capabilities)


# Model registry from Postman collection examples
MODEL_REGISTRY: List[OllamaModel] = [
    # Localhost Models
    OllamaModel(
        id="deepseek-coder-v2",
        category=ModelCategory.CODE,
        provider=ModelProvider.DEEPSEEK,
        capabilities={"code", "chat", "completion"},
        context_length=16384,
        code=True,
        localhost_only=True,
        description="DeepSeek Coder v2 for code generation",
    ),
    OllamaModel(
        id="deepseek-r1:1.5b",
        category=ModelCategory.REASONING,
        provider=ModelProvider.DEEPSEEK,
        capabilities={"chat", "reasoning", "problem_solving"},
        context_length=64000,
        reasoning=True,
        localhost_only=True,
        description="DeepSeek R1 1.5B reasoning model",
    ),
    OllamaModel(
        id="gemma2",
        category=ModelCategory.CHAT,
        provider=ModelProvider.GEMMA,
        capabilities={"chat", "general_purpose"},
        context_length=8192,
        description="Google's Gemma 2 model",
    ),
    OllamaModel(
        id="llama3",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "general_purpose"},
        context_length=8192,
        description="Meta's LLaMA 3 base model",
    ),
    OllamaModel(
        id="llama3.1",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "general_purpose", "long_context"},
        context_length=131072,
        description="Meta's LLaMA 3.1 with extended context",
    ),
    OllamaModel(
        id="llama3.2",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "general_purpose"},
        context_length=128000,
        description="Meta's LLaMA 3.2 model",
    ),
    OllamaModel(
        id="llama3.2:1b",
        category=ModelCategory.CHAT,
        provider=ModelProvider.META,
        capabilities={"chat", "general_purpose"},
        context_length=128000,
        description="Meta's lightweight LLaMA 3.2 1B model",
    ),
    OllamaModel(
        id="mistral",
        category=ModelCategory.CHAT,
        provider=ModelProvider.MISTRAL,
        capabilities={"chat", "instruction"},
        context_length=32768,
        description="Mistral 7B instruction model",
    ),
    OllamaModel(
        id="phi3:mini",
        category=ModelCategory.CHAT,
        provider=ModelProvider.PHI,
        capabilities={"chat", "instruction"},
        context_length=128000,
        description="Microsoft's Phi-3 mini model",
    ),
    OllamaModel(
        id="phi3.5",
        category=ModelCategory.CHAT,
        provider=ModelProvider.PHI,
        capabilities={"chat", "instruction"},
        context_length=131072,
        description="Microsoft's Phi-3.5 model",
    ),
    OllamaModel(
        id="qwen2",
        category=ModelCategory.CHAT,
        provider=ModelProvider.QWEN,
        capabilities={"chat", "general_purpose"},
        context_length=32768,
        description="Qwen 2 base model",
    ),
    OllamaModel(
        id="qwen2.5:1.5b",
        category=ModelCategory.CHAT,
        provider=ModelProvider.QWEN,
        capabilities={"chat", "general_purpose"},
        context_length=32768,
        description="Qwen 2.5 1.5B lightweight model",
    ),
    OllamaModel(
        id="qwen2.5:0.5b",
        category=ModelCategory.CHAT,
        provider=ModelProvider.QWEN,
        capabilities={"chat", "general_purpose"},
        context_length=32768,
        description="Qwen 2.5 0.5B ultra-lightweight model",
    ),
    # Cloud Models
    OllamaModel(
        id="deepseek-v3.1:671b-cloud",
        category=ModelCategory.CHAT,
        provider=ModelProvider.DEEPSEEK,
        capabilities={"chat", "instruction", "code"},
        context_length=131072,
        cloud_only=True,
        code=True,
        description="DeepSeek v3.1 671B cloud model",
    ),
    OllamaModel(
        id="qwen3-coder:480b-cloud",
        category=ModelCategory.CODE,
        provider=ModelProvider.QWEN,
        capabilities={"code", "chat", "completion"},
        context_length=131072,
        cloud_only=True,
        code=True,
        description="Qwen 3 Coder 480B cloud model",
    ),
    OllamaModel(
        id="gpt-oss:120b-cloud",
        category=ModelCategory.CHAT,
        provider=ModelProvider.OPENAI,
        capabilities={"chat", "general_purpose"},
        context_length=131072,
        cloud_only=True,
        description="OpenAI GPT-OSS 120B cloud model",
    ),
    OllamaModel(
        id="gpt-oss:20b-cloud",
        category=ModelCategory.CHAT,
        provider=ModelProvider.OPENAI,
        capabilities={"chat", "general_purpose"},
        context_length=131072,
        cloud_only=True,
        description="OpenAI GPT-OSS 20B cloud model",
    ),
]

# Model lookup dictionaries
MODELS_BY_ID: dict[str, OllamaModel] = {model.id: model for model in MODEL_REGISTRY}
MODELS_BY_CATEGORY: dict[ModelCategory, List[OllamaModel]] = {}
MODELS_BY_PROVIDER: dict[ModelProvider, List[OllamaModel]] = {}

# Build category and provider indexes
for model in MODEL_REGISTRY:
    if model.category not in MODELS_BY_CATEGORY:
        MODELS_BY_CATEGORY[model.category] = []
    MODELS_BY_CATEGORY[model.category].append(model)

    if model.provider not in MODELS_BY_PROVIDER:
        MODELS_BY_PROVIDER[model.provider] = []
    MODELS_BY_PROVIDER[model.provider].append(model)


def get_model(model_id: str) -> Optional[OllamaModel]:
    """Get model metadata by ID"""
    return MODELS_BY_ID.get(model_id)


def list_models(
    category: Optional[ModelCategory] = None,
    provider: Optional[ModelProvider] = None,
    cloud_only: Optional[bool] = None,
    localhost_only: Optional[bool] = None,
    vision: Optional[bool] = None,
    reasoning: Optional[bool] = None,
    code: Optional[bool] = None,
) -> List[OllamaModel]:
    """
    List models with optional filters

    Args:
        category: Filter by model category
        provider: Filter by provider
        cloud_only: Filter by cloud-only models
        localhost_only: Filter by localhost-only models
        vision: Filter by vision capability
        reasoning: Filter by reasoning capability
        code: Filter by code capability

    Returns:
        List of matching models
    """
    models = MODEL_REGISTRY

    if category:
        models = [m for m in models if m.category == category]

    if provider:
        models = [m for m in models if m.provider == provider]

    if cloud_only is not None:
        models = [m for m in models if m.cloud_only == cloud_only]

    if localhost_only is not None:
        models = [m for m in models if m.localhost_only == localhost_only]

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


def get_code_models() -> List[str]:
    """Get list of all code model IDs"""
    return [m.id for m in list_models(code=True)]


def validate_model(model_id: str) -> bool:
    """Check if a model ID is valid"""
    return model_id in MODELS_BY_ID
