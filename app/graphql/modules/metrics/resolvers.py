"""Metrics GraphQL module."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import metrics as metrics_handlers
from app.graphql.modules.util import run_ws


@strawberry.type
class MetricsQuery:
    @strawberry.field
    async def metrics_summary(self, info: Info, params: JSON | None = None) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(metrics_handlers.handle_metrics_summary, p, info)

    @strawberry.field
    async def metrics_providers(self, info: Info, params: JSON | None = None) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(metrics_handlers.handle_metrics_providers, p, info)

    @strawberry.field
    async def metrics_council(self, info: Info, params: JSON | None = None) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(metrics_handlers.handle_metrics_council, p, info)
