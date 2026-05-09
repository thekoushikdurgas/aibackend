"""LLM provider routing GraphQL module."""

from __future__ import annotations

from typing import Any

import strawberry
from graphql import GraphQLError
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import (
    ai21,
    cerebras,
    chat as chat_handlers,
    deepinfra,
    groq,
    hyperbolic,
    nvidia,
    ollama,
    openrouter,
    reka,
)
from app.graphql.modules.util import run_ws, run_ws_chat_completion


def _provider_chat_handlers() -> dict[str, Any]:
    return {
        "groq": groq.handle_groq_chat_completions,
        "nvidia": nvidia.handle_nvidia_chat_completions,
        "openrouter": openrouter.handle_openrouter_chat,
        "ollama": ollama.handle_ollama_chat,
        "hyperbolic": hyperbolic.handle_hyperbolic_chat,
        "deepinfra": deepinfra.handle_deepinfra_chat,
        "cerebras": cerebras.handle_cerebras_chat,
        "reka": reka.handle_reka_chat,
        "ai21": ai21.handle_ai21_complete,
    }


@strawberry.type
class ProvidersQuery:
    @strawberry.field
    async def list_models(self, info: Info, provider_name: str) -> JSON:
        return await run_ws(
            chat_handlers.handle_chat_provider_models,
            {"provider_name": provider_name},
            info,
        )


@strawberry.type
class ProvidersMutation:
    @strawberry.mutation
    async def provider_chat(
        self,
        info: Info,
        provider_name: str,
        params: JSON,
    ) -> JSON:
        key = provider_name.strip().lower()
        handlers = _provider_chat_handlers()
        handler = handlers.get(key)
        if handler is None:
            raise GraphQLError(f"Unknown provider for providerChat: {provider_name}")
        p = dict(params) if isinstance(params, dict) else {}
        if key in (
            "groq",
            "nvidia",
            "openrouter",
            "ollama",
            "hyperbolic",
            "deepinfra",
            "cerebras",
            "reka",
        ):
            return await run_ws_chat_completion(handler, p, info)
        return await run_ws(handler, p, info)
