"""System health GraphQL module."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import health as health_handlers
from app.graphql.modules.util import graphql_params, run_ws


@strawberry.type
class HealthQuery:
    @strawberry.field
    async def system_health(self, info: Info, params: JSON | None = None) -> JSON:
        p = graphql_params(params)
        return await run_ws(health_handlers.handle_system_health, p, info)

    @strawberry.field
    async def system_ready(self, info: Info, params: JSON | None = None) -> JSON:
        p = graphql_params(params)
        return await run_ws(health_handlers.handle_system_ready, p, info)
