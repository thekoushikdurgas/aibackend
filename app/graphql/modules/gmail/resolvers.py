"""Gmail API via WebSocket handlers (GraphQL JSON)."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import gmail as gmail_handlers
from app.graphql.modules.util import graphql_params, run_ws


@strawberry.type
class GmailQuery:
    @strawberry.field
    async def gmail_list_messages(self, info: Info, params: JSON | None = None) -> JSON:
        """Gmail users.messages.list. Params: access_token, max_results?, page_token?, q?."""
        p = graphql_params(params)
        return await run_ws(gmail_handlers.handle_gmail_list_messages, p, info)

    @strawberry.field
    async def gmail_get_message(self, info: Info, params: JSON | None = None) -> JSON:
        """Gmail users.messages.get. Params: access_token, message_id, format?."""
        p = graphql_params(params)
        return await run_ws(gmail_handlers.handle_gmail_get_message, p, info)

    @strawberry.field
    async def gmail_list_threads(self, info: Info, params: JSON | None = None) -> JSON:
        """Gmail users.threads.list. Params: access_token, max_results?, page_token?, q?."""
        p = graphql_params(params)
        return await run_ws(gmail_handlers.handle_gmail_list_threads, p, info)

    @strawberry.field
    async def gmail_get_thread(self, info: Info, params: JSON | None = None) -> JSON:
        """Gmail users.threads.get. Params: access_token, thread_id, format?."""
        p = graphql_params(params)
        return await run_ws(gmail_handlers.handle_gmail_get_thread, p, info)
