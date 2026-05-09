"""RAG GraphQL module."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import rag as rag_handlers
from app.graphql.modules.util import run_ws


@strawberry.type
class RagQuery:
    @strawberry.field
    async def rag_documents(
        self,
        info: Info,
        collection_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> JSON:
        return await run_ws(
            rag_handlers.handle_rag_documents_list,
            {
                "collection_name": collection_name,
                "limit": limit,
                "offset": offset,
            },
            info,
        )

    @strawberry.field
    async def rag_query(
        self,
        info: Info,
        query: str,
        k: int = 5,
        collection_name: str | None = None,
    ) -> JSON:
        return await run_ws(
            rag_handlers.handle_rag_query,
            {
                "query": query,
                "k": k,
                "collection_name": collection_name,
            },
            info,
        )

    @strawberry.field
    async def rag_list(
        self,
        info: Info,
        collection_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> JSON:
        return await run_ws(
            rag_handlers.handle_rag_list,
            {
                "collection_name": collection_name,
                "limit": limit,
                "offset": offset,
            },
            info,
        )


@strawberry.type
class RagMutation:
    @strawberry.mutation
    async def rag_ingest(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(rag_handlers.handle_rag_ingest, p, info)

    @strawberry.mutation
    async def rag_delete(self, info: Info, document_id: str) -> JSON:
        return await run_ws(
            rag_handlers.handle_rag_delete,
            {"document_id": document_id},
            info,
        )

    @strawberry.mutation
    async def rag_upload(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(rag_handlers.handle_rag_documents_upload, p, info)

    @strawberry.mutation
    async def rag_chat(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(rag_handlers.handle_rag_chat, p, info)
