"""
Load provider_manifest.json and build OpenAI-compatible provider classes.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from app.config import settings

from .base import BaseLLMProvider
from .openai_compat import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

_MANIFEST_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "config"
    / "provider_manifest.json"
)


@lru_cache(maxsize=1)
def load_provider_manifest() -> Dict[str, Any]:
    if not _MANIFEST_PATH.is_file():
        logger.warning("provider_manifest.json not found at %s", _MANIFEST_PATH)
        return {"providers": []}
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def get_manifest_entry(provider_id: str) -> Optional[Dict[str, Any]]:
    for p in load_provider_manifest().get("providers", []):
        if p.get("id") == provider_id:
            return p
    return None


def list_manifest_providers(
    *,
    implementation: Optional[str] = None,
    enabled_only: bool = True,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in load_provider_manifest().get("providers", []):
        if enabled_only and not p.get("enabled", True):
            continue
        if implementation and p.get("implementation") != implementation:
            continue
        out.append(p)
    return out


def _settings_get(field: str, default: Any = None) -> Any:
    return getattr(settings, field, default)


def _resolve_provider_config(entry: Dict[str, Any]) -> Dict[str, Any]:
    pid = entry["id"]
    api_key_field = _env_to_field(entry.get("api_key_env", f"{pid.upper()}_API_KEY"))
    base_url_field = _env_to_field(entry.get("base_url_env", f"{pid.upper()}_BASE_URL"))
    model_field = _env_to_field(entry.get("model_env", f"{pid.upper()}_MODEL"))

    api_key = _settings_get(api_key_field)
    base_url = _settings_get(base_url_field) or entry.get("default_base_url") or ""
    model = _settings_get(model_field) or ""

    return {
        "api_key": api_key,
        "base_url": str(base_url).rstrip("/") if base_url else "",
        "default_model": str(model) if model else _default_model_for(pid),
        "api_key_field": api_key_field,
        "base_url_field": base_url_field,
        "model_field": model_field,
    }


def _env_to_field(env_name: str) -> str:
    return env_name.lower()


def _default_model_for(provider_id: str) -> str:
    defaults = {
        "openai": "gpt-4o-mini",
        "deepseek": "deepseek-chat",
        "mistral": "mistral-small-latest",
        "together": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        "perplexity": "sonar",
        "xai": "grok-2-latest",
        "sambanova": "Meta-Llama-3.1-70B-Instruct",
        "github_ai": "gpt-4o",
        "docker_model_runner": "llama3.2",
        "novita": "meta-llama/llama-3-70b-instruct",
        "nebius": "meta-llama/Meta-Llama-3.1-70B-Instruct",
        "kluster": "meta-llama/Meta-Llama-3.1-70B-Instruct",
        "lamini": "meta-llama/Meta-Llama-3.1-8B-Instruct",
        "lepton": "meta-llama/Meta-Llama-3.1-70B-Instruct",
    }
    return defaults.get(provider_id, "default")


def build_compat_provider_class(entry: Dict[str, Any]) -> Type[BaseLLMProvider]:
    """Dynamically create a provider class for manifest entry."""
    pid = entry["id"]
    cfg = _resolve_provider_config(entry)

    class _ManifestCompatProvider(OpenAICompatibleProvider):
        provider_name = pid

        def __init__(self, **kwargs: Any):
            extra_headers: Dict[str, str] = {}
            auth_header = "Bearer"
            if pid == "perplexity":
                pass  # bearer only
            if entry.get("auth_type") == "apikey":
                auth_header = "api-key"
            super().__init__(
                provider_name=pid,
                api_key=kwargs.get("api_key") or cfg["api_key"],
                default_model=kwargs.get("model") or cfg["default_model"],
                base_url=kwargs.get("base_url") or cfg["base_url"],
                timeout=float(kwargs.get("timeout", 120.0)),
                extra_headers=extra_headers,
                auth_header=auth_header,
                use_max_completion_tokens=pid not in ("mistral", "deepseek"),
            )

    _ManifestCompatProvider.__name__ = f"{pid.title().replace('_', '')}Provider"
    _ManifestCompatProvider.__qualname__ = _ManifestCompatProvider.__name__
    return _ManifestCompatProvider


# Built once at import
_COMPAT_REGISTRY: Dict[str, Type[BaseLLMProvider]] = {}
_STATIC_COMPAT_IDS = frozenset(
    {
        "cerebras",
        "groq",
        "fireworks",
        "deepinfra",
        "anyscale",
        "hyperbolic",
        "reka",
        "openrouter",
    }
)


def get_compat_provider_class(provider_id: str) -> Optional[Type[BaseLLMProvider]]:
    if provider_id in _COMPAT_REGISTRY:
        return _COMPAT_REGISTRY[provider_id]
    entry = get_manifest_entry(provider_id)
    if not entry or entry.get("implementation") != "openai_compat":
        return None
    if provider_id in _STATIC_COMPAT_IDS:
        return None
    cls = build_compat_provider_class(entry)
    _COMPAT_REGISTRY[provider_id] = cls
    return cls


def register_compat_providers(factory: Any) -> None:
    """Register manifest openai_compat providers on LLMProviderFactory."""
    for entry in list_manifest_providers(implementation="openai_compat"):
        pid = entry["id"]
        if pid in _STATIC_COMPAT_IDS:
            continue
        if pid in factory._providers:
            continue
        cls = get_compat_provider_class(pid)
        if cls:
            factory.register_provider(pid, cls)
            logger.debug("Registered manifest compat provider: %s", pid)


def manifest_metadata(provider_id: str) -> Dict[str, Any]:
    entry = get_manifest_entry(provider_id) or {}
    return {
        "capabilities": entry.get("capabilities", ["chat"]),
        "latency_tier": entry.get("latency_tier", "normal"),
        "requires_api_key": entry.get("requires_api_key", True),
        "category": entry.get("category", "chat"),
        "display_name": entry.get("display_name", provider_id),
        "postman_link": entry.get("postman_link", ""),
        "implementation": entry.get("implementation", ""),
    }
