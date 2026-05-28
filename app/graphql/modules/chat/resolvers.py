"""Chat GraphQL module."""

from __future__ import annotations

import asyncio
import logging

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import chat as chat_handlers
from app.core.response_cache import cache_invalidate_prefix, cached_json_response
from app.graphql.context import GraphQLContext
from app.graphql.modules.util import run_ws, run_ws_chat_completion, user_from_info

logger = logging.getLogger(__name__)


@strawberry.type
class ChatQuery:
    @strawberry.field
    async def chat_providers(self, info: Info) -> JSON:
        ctx = info.context
        req = ctx.request if isinstance(ctx, GraphQLContext) else None
        if req is None:
            return await run_ws(chat_handlers.handle_chat_providers, {}, info)
        return await cached_json_response(
            req,
            "gql:chat_providers:v1",
            300.0,
            lambda: run_ws(chat_handlers.handle_chat_providers, {}, info),
        )

    @strawberry.field
    async def chat_conversations(self, info: Info, limit: int = 50) -> JSON:
        ctx = info.context
        req = ctx.request if isinstance(ctx, GraphQLContext) else None
        user = user_from_info(info)
        sub = str(user.get("sub", "anon")) if user else "anon"
        if req is None:
            return await run_ws(
                chat_handlers.handle_chat_conversations_list,
                {"limit": limit},
                info,
            )
        key = f"gql:chat_convos:{sub}:{limit}"
        return await cached_json_response(
            req,
            key,
            30.0,
            lambda: run_ws(
                chat_handlers.handle_chat_conversations_list,
                {"limit": limit},
                info,
            ),
        )

    @strawberry.field
    async def chat_conversation(self, info: Info, conversation_id: str) -> JSON:
        return await run_ws(
            chat_handlers.handle_chat_conversations_get,
            {"conversation_id": conversation_id},
            info,
        )


@strawberry.type
class ChatMutation:
    @strawberry.mutation
    async def chat_completion(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        result = await run_ws_chat_completion(
            chat_handlers.handle_chat_completions,
            p,
            info,
        )

        async def _deferred_metrics() -> None:
            try:
                logger.debug("chat_completion finished (deferred bookkeeping)")
            except Exception:
                pass

        asyncio.create_task(_deferred_metrics())
        return result

    @strawberry.mutation
    async def delete_conversation(self, info: Info, conversation_id: str) -> JSON:
        ctx = info.context
        if isinstance(ctx, GraphQLContext):
            user = user_from_info(info)
            if user and user.get("sub"):
                sub = str(user["sub"])
                await cache_invalidate_prefix(ctx.request, f"gql:chat_convos:{sub}:")
        return await run_ws(
            chat_handlers.handle_chat_conversations_delete,
            {"conversation_id": conversation_id},
            info,
        )
