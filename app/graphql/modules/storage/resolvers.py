"""Storage GraphQL module."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import storage as storage_handlers
from app.graphql.modules.util import graphql_params, require_authenticated_sub, run_ws
from app.services.local_storage_service import absolute_signed_file_url


@strawberry.type
class StorageQuery:
    @strawberry.field
    async def storage_signed_http_url(
        self,
        info: Info,
        bucket: str,
        file_path: str,
        expires_in: int = 3600,
    ) -> str | None:
        """
        Absolute signed URL for a stored object (replaces ``GET /files/{bucket}/{path}``).
        """
        require_authenticated_sub(info)
        base_url = str(info.context.request.base_url).rstrip("/")
        return absolute_signed_file_url(base_url, bucket, file_path, expires_in)

    @strawberry.field
    async def storage_list(self, info: Info, params: JSON | None = None) -> JSON:
        p = graphql_params(params)
        return await run_ws(storage_handlers.handle_storage_list, p, info)

    @strawberry.field
    async def storage_buckets(self, info: Info, params: JSON | None = None) -> JSON:
        p = graphql_params(params)
        return await run_ws(storage_handlers.handle_storage_buckets_list, p, info)


@strawberry.type
class StorageMutation:
    @strawberry.mutation
    async def storage_upload(self, info: Info, params: JSON) -> JSON:
        p = graphql_params(params)
        return await run_ws(storage_handlers.handle_storage_upload, p, info)

    @strawberry.mutation
    async def storage_delete(self, info: Info, params: JSON) -> JSON:
        p = graphql_params(params)
        return await run_ws(storage_handlers.handle_storage_delete, p, info)

    @strawberry.mutation
    async def storage_move(self, info: Info, params: JSON) -> JSON:
        p = graphql_params(params)
        return await run_ws(storage_handlers.handle_storage_move, p, info)

    @strawberry.mutation
    async def storage_mkdir(self, info: Info, params: JSON) -> JSON:
        p = graphql_params(params)
        return await run_ws(storage_handlers.handle_storage_mkdir, p, info)

    @strawberry.mutation
    async def storage_get_url(self, info: Info, params: JSON) -> JSON:
        p = graphql_params(params)
        return await run_ws(storage_handlers.handle_storage_get_url, p, info)

    @strawberry.mutation
    async def storage_create_signed_url(self, info: Info, params: JSON) -> JSON:
        p = graphql_params(params)
        return await run_ws(storage_handlers.handle_storage_create_signed_url, p, info)

    @strawberry.mutation
    async def storage_buckets_create(self, info: Info, params: JSON) -> JSON:
        p = graphql_params(params)
        return await run_ws(storage_handlers.handle_storage_buckets_create, p, info)

    @strawberry.mutation
    async def storage_buckets_delete(self, info: Info, params: JSON) -> JSON:
        p = graphql_params(params)
        return await run_ws(storage_handlers.handle_storage_buckets_delete, p, info)
