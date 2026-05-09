"""Multimodal GraphQL module."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import multimodal as multimodal_handlers
from app.graphql.modules.util import run_ws


@strawberry.type
class MultimodalMutation:
    @strawberry.mutation
    async def text_to_image(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(
            multimodal_handlers.handle_multimodal_text_to_image, p, info
        )

    @strawberry.mutation
    async def image_to_text(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(
            multimodal_handlers.handle_multimodal_image_to_text, p, info
        )

    @strawberry.mutation
    async def speech_to_text(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(
            multimodal_handlers.handle_multimodal_speech_to_text, p, info
        )

    @strawberry.mutation
    async def text_to_speech(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(
            multimodal_handlers.handle_multimodal_text_to_speech, p, info
        )

    @strawberry.mutation
    async def object_detection(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(
            multimodal_handlers.handle_multimodal_object_detection, p, info
        )
