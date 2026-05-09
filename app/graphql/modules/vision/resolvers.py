"""Vision GraphQL module."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import vision as vision_handlers
from app.graphql.modules.util import run_ws


@strawberry.type
class VisionMutation:
    @strawberry.mutation
    async def analyze_image(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(vision_handlers.handle_vision_analyze, p, info)

    @strawberry.mutation
    async def vision_nvidia(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(vision_handlers.handle_vision_nvidia, p, info)
