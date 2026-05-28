"""Google Photos Library API via WebSocket handler (GraphQL JSON)."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import google_photos as google_photos_handlers
from app.graphql.modules.util import graphql_params, run_ws


@strawberry.type
class GooglePhotosQuery:
    @strawberry.field
    async def google_photos_list(self, info: Info, params: JSON | None = None) -> JSON:
        """Proxy to Google Photos `mediaItems.list`. Params: access_token, page_token?, page_size?."""
        p = graphql_params(params)
        return await run_ws(google_photos_handlers.handle_google_photos_list, p, info)

    @strawberry.field
    async def google_photos_picker_create(
        self, info: Info, params: JSON | None = None
    ) -> JSON:
        """Create a Google Photos Picker session."""
        p = graphql_params(params)
        return await run_ws(
            google_photos_handlers.handle_google_photos_picker_create, p, info
        )

    @strawberry.field
    async def google_photos_picker_get(
        self, info: Info, params: JSON | None = None
    ) -> JSON:
        """Get a Google Photos Picker session."""
        p = graphql_params(params)
        return await run_ws(
            google_photos_handlers.handle_google_photos_picker_get, p, info
        )

    @strawberry.field
    async def google_photos_picker_list(
        self, info: Info, params: JSON | None = None
    ) -> JSON:
        """List selected media from a completed Google Photos Picker session."""
        p = graphql_params(params)
        return await run_ws(
            google_photos_handlers.handle_google_photos_picker_list, p, info
        )
