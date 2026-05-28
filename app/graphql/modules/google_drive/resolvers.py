"""Google Drive API v3 via WebSocket handlers (GraphQL JSON)."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import google_drive as google_drive_handlers
from app.graphql.modules.util import graphql_params, run_ws


@strawberry.type
class GoogleDriveQuery:
    @strawberry.field
    async def google_drive_list_files(
        self, info: Info, params: JSON | None = None
    ) -> JSON:
        """Drive files.list. Params: access_token, page_size?, page_token?, q?, fields?."""
        p = graphql_params(params)
        return await run_ws(
            google_drive_handlers.handle_google_drive_list_files, p, info
        )
