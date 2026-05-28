"""Manifest and helpers for editable AI provider settings (HTTP admin UI)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Literal, Optional, Tuple

FieldKind = Literal["secret", "url", "string", "enum"]


@dataclass(frozen=True)
class FieldSpec:
    key: str
    label: str
    kind: FieldKind
    enum_options: Optional[Tuple[str, ...]] = None


@dataclass(frozen=True)
class SectionSpec:
    id: str
    title: str
    fields: Tuple[FieldSpec, ...]


AI_PROVIDER_SECTIONS: Tuple[SectionSpec, ...] = (
    SectionSpec(
        id="defaults",
        title="Defaults & embeddings",
        fields=(
            FieldSpec("default_llm_provider", "Default LLM provider", "string"),
            FieldSpec("default_model", "Default model", "string"),
            FieldSpec("embedding_provider", "Embedding provider", "string"),
            FieldSpec("embedding_model", "Embedding model", "string"),
        ),
    ),
    SectionSpec(
        id="ollama",
        title="Ollama",
        fields=(
            FieldSpec("ollama_base_url", "Base URL", "url"),
            FieldSpec("ollama_cloud_url", "Cloud API URL", "url"),
            FieldSpec(
                "ollama_mode",
                "Mode",
                "enum",
                enum_options=("localhost", "cloud"),
            ),
            FieldSpec("ollama_api_key", "API key (cloud)", "secret"),
            FieldSpec("ollama_model", "Default chat model", "string"),
        ),
    ),
    SectionSpec(
        id="huggingface",
        title="Hugging Face",
        fields=(
            FieldSpec("huggingface_api_key", "API key", "secret"),
            FieldSpec("hf_router_base_url", "Router base URL", "url"),
            FieldSpec("hf_inference_base_url", "Inference API URL", "url"),
            FieldSpec("huggingface_model", "Default model", "string"),
            FieldSpec("huggingface_inference_provider", "Inference provider", "string"),
        ),
    ),
    SectionSpec(
        id="gemini",
        title="Google Gemini",
        fields=(
            FieldSpec("gemini_api_key", "API key", "secret"),
            FieldSpec("gemini_base_url", "Base URL", "url"),
            FieldSpec("gemini_model", "Chat model", "string"),
            FieldSpec("gemini_embedding_model", "Embedding model", "string"),
            FieldSpec("gemini_vision_model", "Vision model", "string"),
        ),
    ),
    SectionSpec(
        id="ai21",
        title="AI21",
        fields=(
            FieldSpec("ai21_api_key", "API key", "secret"),
            FieldSpec("ai21_base_url", "Base URL", "url"),
            FieldSpec("ai21_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="groq",
        title="Groq",
        fields=(
            FieldSpec("groq_api_key", "API key", "secret"),
            FieldSpec("groq_base_url", "Base URL", "url"),
            FieldSpec("groq_model", "Chat model", "string"),
        ),
    ),
    SectionSpec(
        id="nvidia",
        title="NVIDIA",
        fields=(
            FieldSpec("nvidia_api_key", "API key", "secret"),
            FieldSpec("nvidia_base_url", "Chat base URL", "url"),
            FieldSpec("nvidia_genai_base_url", "GenAI base URL", "url"),
            FieldSpec("nvidia_nim_base_url", "NIM base URL", "url"),
            FieldSpec("nvidia_chat_model", "Chat model", "string"),
        ),
    ),
    SectionSpec(
        id="cerebras",
        title="Cerebras",
        fields=(
            FieldSpec("cerebras_api_key", "API key", "secret"),
            FieldSpec("cerebras_base_url", "Base URL", "url"),
            FieldSpec("cerebras_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="openrouter",
        title="OpenRouter",
        fields=(
            FieldSpec("openrouter_api_key", "API key", "secret"),
            FieldSpec("openrouter_base_url", "Base URL", "url"),
            FieldSpec("openrouter_model", "Model", "string"),
            FieldSpec("openrouter_site_url", "Site URL (optional)", "url"),
            FieldSpec("openrouter_app_name", "App name", "string"),
        ),
    ),
    SectionSpec(
        id="fireworks",
        title="Fireworks",
        fields=(
            FieldSpec("fireworks_api_key", "API key", "secret"),
            FieldSpec("fireworks_base_url", "Base URL", "url"),
            FieldSpec("fireworks_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="deepinfra",
        title="Deep Infra",
        fields=(
            FieldSpec("deepinfra_api_key", "API key", "secret"),
            FieldSpec("deepinfra_base_url", "OpenAI-compatible URL", "url"),
            FieldSpec("deepinfra_inference_base_url", "Inference base URL", "url"),
            FieldSpec("deepinfra_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="anyscale",
        title="Anyscale",
        fields=(
            FieldSpec("anyscale_api_key", "API key", "secret"),
            FieldSpec("anyscale_base_url", "Base URL", "url"),
            FieldSpec("anyscale_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="cohere",
        title="Cohere",
        fields=(
            FieldSpec("cohere_api_key", "API key", "secret"),
            FieldSpec("cohere_base_url", "Base URL", "url"),
            FieldSpec("cohere_model", "Chat model", "string"),
            FieldSpec("cohere_embed_model", "Embed model", "string"),
        ),
    ),
    SectionSpec(
        id="hyperbolic",
        title="Hyperbolic",
        fields=(
            FieldSpec("hyperbolic_api_key", "API key", "secret"),
            FieldSpec("hyperbolic_base_url", "Base URL", "url"),
            FieldSpec("hyperbolic_default_text_model", "Text model", "string"),
        ),
    ),
    SectionSpec(
        id="reka",
        title="Reka",
        fields=(
            FieldSpec("reka_api_key", "API key", "secret"),
            FieldSpec("reka_base_url", "Base URL", "url"),
            FieldSpec("reka_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="fal",
        title="fal.ai",
        fields=(
            FieldSpec("fal_api_key", "API key", "secret"),
            FieldSpec("fal_base_url", "Base URL", "url"),
        ),
    ),
    SectionSpec(
        id="openai",
        title="OpenAI",
        fields=(
            FieldSpec("openai_api_key", "API key", "secret"),
            FieldSpec("openai_base_url", "Base URL", "url"),
            FieldSpec("openai_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="deepseek",
        title="DeepSeek",
        fields=(
            FieldSpec("deepseek_api_key", "API key", "secret"),
            FieldSpec("deepseek_base_url", "Base URL", "url"),
            FieldSpec("deepseek_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="mistral",
        title="Mistral",
        fields=(
            FieldSpec("mistral_api_key", "API key", "secret"),
            FieldSpec("mistral_base_url", "Base URL", "url"),
            FieldSpec("mistral_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="together",
        title="Together AI",
        fields=(
            FieldSpec("together_api_key", "API key", "secret"),
            FieldSpec("together_base_url", "Base URL", "url"),
            FieldSpec("together_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="perplexity",
        title="Perplexity",
        fields=(
            FieldSpec("perplexity_api_key", "API key", "secret"),
            FieldSpec("perplexity_base_url", "Base URL", "url"),
            FieldSpec("perplexity_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="xai",
        title="xAI",
        fields=(
            FieldSpec("xai_api_key", "API key", "secret"),
            FieldSpec("xai_base_url", "Base URL", "url"),
            FieldSpec("xai_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="sambanova",
        title="SambaNova",
        fields=(
            FieldSpec("sambanova_api_key", "API key", "secret"),
            FieldSpec("sambanova_base_url", "Base URL", "url"),
            FieldSpec("sambanova_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="github_ai",
        title="GitHub Models",
        fields=(
            FieldSpec("github_ai_api_key", "API key", "secret"),
            FieldSpec("github_ai_base_url", "Base URL", "url"),
            FieldSpec("github_ai_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="docker_model_runner",
        title="Docker Model Runner",
        fields=(
            FieldSpec("docker_model_runner_api_key", "API key (optional)", "secret"),
            FieldSpec("docker_model_runner_base_url", "Base URL", "url"),
            FieldSpec("docker_model_runner_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="vertex",
        title="Vertex AI",
        fields=(
            FieldSpec("vertex_project_id", "GCP project ID", "string"),
            FieldSpec("vertex_location", "Region", "string"),
            FieldSpec("vertex_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="bedrock",
        title="Amazon Bedrock",
        fields=(
            FieldSpec("bedrock_region", "AWS region", "string"),
            FieldSpec("bedrock_model", "Model ID", "string"),
        ),
    ),
    SectionSpec(
        id="dashscope",
        title="Alibaba DashScope",
        fields=(
            FieldSpec("dashscope_api_key", "API key", "secret"),
            FieldSpec("dashscope_base_url", "Base URL", "url"),
            FieldSpec("dashscope_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="watsonx",
        title="IBM watsonx",
        fields=(
            FieldSpec("watsonx_api_key", "API key", "secret"),
            FieldSpec("watsonx_base_url", "Base URL", "url"),
            FieldSpec("watsonx_project_id", "Project ID", "string"),
            FieldSpec("watsonx_model", "Model", "string"),
        ),
    ),
    SectionSpec(
        id="stability",
        title="Stability AI",
        fields=(
            FieldSpec("stability_api_key", "API key", "secret"),
            FieldSpec("stability_base_url", "Base URL", "url"),
        ),
    ),
    SectionSpec(
        id="replicate",
        title="Replicate",
        fields=(
            FieldSpec("replicate_api_key", "API key", "secret"),
            FieldSpec("replicate_base_url", "Base URL", "url"),
        ),
    ),
    SectionSpec(
        id="eden",
        title="Eden AI",
        fields=(
            FieldSpec("eden_api_key", "API key", "secret"),
            FieldSpec("eden_base_url", "Base URL", "url"),
        ),
    ),
    SectionSpec(
        id="deepgram",
        title="Deepgram",
        fields=(
            FieldSpec("deepgram_api_key", "API key", "secret"),
            FieldSpec("deepgram_base_url", "Base URL", "url"),
        ),
    ),
    SectionSpec(
        id="elevenlabs",
        title="ElevenLabs",
        fields=(
            FieldSpec("elevenlabs_api_key", "API key", "secret"),
            FieldSpec("elevenlabs_base_url", "Base URL", "url"),
        ),
    ),
)


def allowed_field_keys() -> FrozenSet[str]:
    keys: List[str] = []
    for sec in AI_PROVIDER_SECTIONS:
        for f in sec.fields:
            keys.append(f.key)
    return frozenset(keys)


def _secret_preview(val: Optional[str]) -> Dict[str, Any]:
    if not val:
        return {"set": False, "preview": None}
    s = val
    tail = s[-4:] if len(s) >= 4 else s
    return {"set": True, "preview": f"…{tail}"}


def serialize_field_value(settings: Any, spec: FieldSpec) -> Any:
    raw = getattr(settings, spec.key, None)
    if spec.kind == "secret":
        return _secret_preview(raw)
    if raw is None:
        return None
    if isinstance(raw, (list, dict)):
        return raw
    return str(raw)


def sections_public_dict() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for sec in AI_PROVIDER_SECTIONS:
        out.append(
            {
                "id": sec.id,
                "title": sec.title,
                "fields": [
                    {
                        "key": f.key,
                        "label": f.label,
                        "kind": f.kind,
                        "enum_options": (
                            list(f.enum_options) if f.enum_options else None
                        ),
                    }
                    for f in sec.fields
                ],
            }
        )
    return out


def values_public_dict(settings: Any) -> Dict[str, Any]:
    vals: Dict[str, Any] = {}
    for sec in AI_PROVIDER_SECTIONS:
        for f in sec.fields:
            vals[f.key] = serialize_field_value(settings, f)
    return vals
