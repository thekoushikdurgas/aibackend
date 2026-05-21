"""Runtime AI provider settings via GraphQL (replaces REST ``/api/settings/ai-providers``)."""

from __future__ import annotations

import logging
from typing import Any, Dict, cast

import strawberry
from graphql import GraphQLError
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.schemas.ai_provider_settings import (
    allowed_field_keys,
    sections_public_dict,
    values_public_dict,
)
from app.config import settings
from app.config_runtime_overlay import SettingsOverlayProxy, apply_ai_provider_updates
from app.core.response_cache import cache_invalidate_prefix
from app.graphql.context import GraphQLContext
from app.graphql.http_user import require_auth_user_dict

logger = logging.getLogger(__name__)


def _ai_provider_warnings(proxy: object) -> list[str]:
    """Actionable warnings only when relevant to current overlay state."""
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


@strawberry.type
class RuntimeSettingsQuery:
    @strawberry.field
    async def ai_provider_settings(self, info: Info) -> JSON:
        require_auth_user_dict(info)
        return cast(
            JSON,
            {
                "sections": sections_public_dict(),
                "values": values_public_dict(settings),
                "warnings": _ai_provider_warnings(settings),
            },
        )


@strawberry.type
class RuntimeSettingsMutation:
    @strawberry.mutation
    async def update_ai_provider_settings(self, info: Info, updates: JSON) -> JSON:
        auth_user = require_auth_user_dict(info)
        if not isinstance(updates, dict):
            raise GraphQLError(
                "updates must be a JSON object",
                extensions={"code": "BAD_USER_INPUT"},
            )
        body: Dict[str, Any] = {str(k): v for k, v in updates.items()}
        allowed = allowed_field_keys()
        unknown = [k for k in body if k not in allowed]
        if unknown:
            raise GraphQLError(
                f"Unknown or disallowed keys: {', '.join(sorted(unknown))}",
                extensions={"code": "BAD_USER_INPUT"},
            )

        mode = body.get("ollama_mode")
        if mode is not None and isinstance(mode, str):
            m = mode.strip().lower()
            if m not in ("localhost", "cloud"):
                raise GraphQLError(
                    "ollama_mode must be 'localhost' or 'cloud'",
                    extensions={"code": "BAD_USER_INPUT"},
                )
            body["ollama_mode"] = m

        filtered = {k: v for k, v in body.items() if k in allowed}
        if not filtered:
            return cast(
                JSON, {"ok": True, "applied": 0, "message": "No non-empty updates"}
            )

        if not isinstance(settings, SettingsOverlayProxy):
            logger.warning(
                "settings is not SettingsOverlayProxy; runtime overrides may not apply"
            )
        apply_ai_provider_updates(settings, filtered)
        ctx = info.context
        if isinstance(ctx, GraphQLContext):
            sub = str(auth_user.get("sub", ""))
            if sub:
                await cache_invalidate_prefix(ctx.request, f"gql:me:v1:{sub}")
        return cast(
            JSON,
            {
                "ok": True,
                "applied": len(filtered),
                "keys": sorted(filtered.keys()),
            },
        )
