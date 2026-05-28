"""Factory helpers for manifest-driven OpenAI-compatible providers."""

from __future__ import annotations

from typing import Any

from app.config import settings

from .openai_compat import OpenAICompatibleProvider
from .provider_registry import get_manifest_entry, manifest_metadata


def create_manifest_compat_provider(
    provider_id: str, **kwargs: Any
) -> OpenAICompatibleProvider:
    entry = get_manifest_entry(provider_id) or {}
    api_key_field = entry.get("api_key_env", f"{provider_id.upper()}_API_KEY").lower()
    base_url_field = entry.get(
        "base_url_env", f"{provider_id.upper()}_BASE_URL"
    ).lower()
    model_field = entry.get("model_env", f"{provider_id.upper()}_MODEL").lower()

    api_key = kwargs.get("api_key") or getattr(settings, api_key_field, None)
    base_url = (
        kwargs.get("base_url")
        or getattr(settings, base_url_field, None)
        or entry.get("default_base_url")
        or ""
    )
    model = kwargs.get("model") or getattr(settings, model_field, None) or "default"

    extra_headers: dict[str, str] = {}
    auth_header = "Bearer"
    if entry.get("auth_type") == "apikey":
        auth_header = "api-key"

    return OpenAICompatibleProvider(
        provider_name=provider_id,
        api_key=api_key,
        default_model=str(model),
        base_url=str(base_url).rstrip("/"),
        timeout=float(kwargs.get("timeout", 120.0)),
        extra_headers=extra_headers,
        auth_header=auth_header,
        use_max_completion_tokens=provider_id not in ("mistral", "deepseek"),
    )


def enrich_provider_info(provider_id: str, base: dict[str, Any]) -> dict[str, Any]:
    meta = manifest_metadata(provider_id)
    return {**base, **meta}
