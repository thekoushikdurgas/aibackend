"""Chat GraphQL module."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import chat as chat_handlers
from app.graphql.modules.util import run_ws, run_ws_chat_completion


@strawberry.type
class ChatQuery:
    @strawberry.field
    async def chat_providers(self, info: Info) -> JSON:
        return await run_ws(chat_handlers.handle_chat_providers, {}, info)

    @strawberry.field
    async def chat_conversations(self, info: Info, limit: int = 50) -> JSON:
        return await run_ws(
            chat_handlers.handle_chat_conversations_list,
            {"limit": limit},
            info,
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
        return await run_ws_chat_completion(
            chat_handlers.handle_chat_completions,
            p,
            info,
        )

    @strawberry.mutation
    async def delete_conversation(self, info: Info, conversation_id: str) -> JSON:
        return await run_ws(
            chat_handlers.handle_chat_conversations_delete,
            {"conversation_id": conversation_id},
            info,
        )
