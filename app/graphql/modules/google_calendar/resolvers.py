"""Google Calendar API via WebSocket handlers (GraphQL JSON)."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import google_calendar as google_calendar_handlers
from app.graphql.modules.util import graphql_params, run_ws


@strawberry.type
class GoogleCalendarQuery:
    @strawberry.field
    async def google_calendar_list_events(
        self, info: Info, params: JSON | None = None
    ) -> JSON:
        """Calendar events.list (primary). Params: access_token, max_results?, page_token?, time_min?, time_max?."""
        p = graphql_params(params)
        return await run_ws(
            google_calendar_handlers.handle_google_calendar_list_events, p, info
        )
