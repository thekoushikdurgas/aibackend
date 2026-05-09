"""Council GraphQL module."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import council as council_handlers
from app.graphql.modules.util import run_ws


@strawberry.type
class CouncilMutation:
    @strawberry.mutation
    async def run_council(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(council_handlers.handle_council_run, p, info)
