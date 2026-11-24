"""
WebSocket handlers for runtime AI provider settings.

Mirrors GraphQL ``aiProviderSettings`` / ``updateAiProviderSettings`` for the
extension (JSON-RPC over ``/ws/gateway``).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.api.schemas.ai_provider_settings import (
    allowed_field_keys,
    sections_public_dict,
    values_public_dict,
)
from app.config import settings
from app.config_runtime_overlay import SettingsOverlayProxy, apply_ai_provider_updates
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.core.ws_auth import require_auth

logger = logging.getLogger(__name__)


def _ai_provider_warnings(proxy: object) -> list[str]:
    warnings: list[str] = []
    if isinstance(proxy, SettingsOverlayProxy):
        if proxy.has_stored_secrets():
            path = proxy.overrides_path
            warnings.append(
                f"API keys in the overrides file ({path.name}) are stored as plaintext JSON "
                "with owner-only permissions (mode 600). Prefer environment variables in production."
            )
        if proxy.has_embedding_overrides():
            warnings.append(
                "Embedding provider or model is overridden here. Changing them may require a new "
                "Chroma collection or re-ingest of existing documents."
            )
    return warnings


async def _gate_settings_auth(
    user: Optional[Dict[str, Any]], method_name: str
) -> Optional[Dict[str, Any]]:
    """Require WS auth when the backend API key gate is configured."""
    if settings.api_key:
        return await require_auth(user, method_name)
    return user


async def handle_settings_ai_providers_get(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """settings.ai_providers.get — public sections + masked secret values."""
    await _gate_settings_auth(user, "settings.ai_providers.get")
    return {
        "sections": sections_public_dict(),
        "values": values_public_dict(settings),
        "warnings": _ai_provider_warnings(settings),
    }


async def handle_settings_ai_providers_update(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """settings.ai_providers.update — persist allowlisted overlay fields.

    Empty/whitespace secret strings are skipped by ``merge_overlay`` so they
    do not wipe an existing key.
    """
    await _gate_settings_auth(user, "settings.ai_providers.update")

    updates = params.get("updates")
    if updates is None and isinstance(params.get("nvidia_api_key"), str):
        # Convenience: allow flat nvidia_api_key at top level from the extension.
        updates = {"nvidia_api_key": params["nvidia_api_key"]}
    if not isinstance(updates, dict):
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            "Missing or invalid parameter: updates (object required)",
        )

    body: Dict[str, Any] = {str(k): v for k, v in updates.items()}
    allowed = allowed_field_keys()
    unknown = [k for k in body if k not in allowed]
    if unknown:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS,
            f"Unknown or disallowed keys: {', '.join(sorted(unknown))}",
        )

    mode = body.get("ollama_mode")
    if mode is not None and isinstance(mode, str):
        m = mode.strip().lower()
        if m not in ("localhost", "cloud"):
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS,
                "ollama_mode must be 'localhost' or 'cloud'",
            )
        body["ollama_mode"] = m

    filtered = {k: v for k, v in body.items() if k in allowed}
    # Empty/whitespace strings must not wipe existing secrets (merge_overlay skips them).
    non_empty = {
        k: v
        for k, v in filtered.items()
        if v is not None and not (isinstance(v, str) and not str(v).strip())
    }
    if not non_empty:
        return {"ok": True, "applied": 0, "keys": [], "message": "No non-empty updates"}

    if not isinstance(settings, SettingsOverlayProxy):
        logger.warning(
            "settings is not SettingsOverlayProxy; runtime overrides may not apply"
        )
    apply_ai_provider_updates(settings, non_empty)
    return {
        "ok": True,
        "applied": len(non_empty),
        "keys": sorted(non_empty.keys()),
    }


def get_methods() -> Dict[str, Any]:
    return {
        "settings.ai_providers.get": handle_settings_ai_providers_get,
        "settings.ai_providers.update": handle_settings_ai_providers_update,
    }
