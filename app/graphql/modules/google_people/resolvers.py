"""Google People API (contacts) via WebSocket handlers (GraphQL JSON)."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import google_people as google_people_handlers
from app.graphql.modules.util import graphql_params, run_ws


@strawberry.type
class GooglePeopleQuery:
    @strawberry.field
    async def google_people_list_contacts(
        self, info: Info, params: JSON | None = None
    ) -> JSON:
        """People connections.list. Params: access_token, page_size?, page_token?, person_fields?."""
        p = graphql_params(params)
        return await run_ws(
            google_people_handlers.handle_google_people_list_contacts, p, info
        )
