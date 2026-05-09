"""Storage GraphQL module."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import storage as storage_handlers
from app.graphql.modules.util import run_ws


@strawberry.type
class StorageQuery:
    @strawberry.field
    async def storage_list(self, info: Info, params: JSON | None = None) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(storage_handlers.handle_storage_list, p, info)

    @strawberry.field
    async def storage_buckets(self, info: Info, params: JSON | None = None) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(storage_handlers.handle_storage_buckets_list, p, info)


@strawberry.type
class StorageMutation:
    @strawberry.mutation
    async def storage_upload(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(storage_handlers.handle_storage_upload, p, info)

    @strawberry.mutation
    async def storage_delete(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(storage_handlers.handle_storage_delete, p, info)

    @strawberry.mutation
    async def storage_move(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(storage_handlers.handle_storage_move, p, info)

    @strawberry.mutation
    async def storage_get_url(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(storage_handlers.handle_storage_get_url, p, info)

    @strawberry.mutation
    async def storage_create_signed_url(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(storage_handlers.handle_storage_create_signed_url, p, info)

    @strawberry.mutation
    async def storage_buckets_create(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(storage_handlers.handle_storage_buckets_create, p, info)

    @strawberry.mutation
    async def storage_buckets_delete(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(storage_handlers.handle_storage_buckets_delete, p, info)
