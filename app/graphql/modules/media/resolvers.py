"""Media generation GraphQL module (FAL, ElevenLabs, Deepgram, Imagen, Veo)."""

from __future__ import annotations

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import (
    deepgram,
    elevenlabs,
    fal,
    imagen,
    veo,
)
from app.graphql.modules.async_job_dispatch import start_ws_job
from app.graphql.modules.util import run_ws


@strawberry.type
class MediaMutation:
    @strawberry.mutation
    async def generate_image(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return start_ws_job(info, fal.handle_fal_images, p)

    @strawberry.mutation
    async def generate_audio(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return start_ws_job(info, fal.handle_fal_audio, p)

    @strawberry.mutation
    async def generate_video(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return start_ws_job(info, fal.handle_fal_video, p)

    @strawberry.mutation
    async def elevenlabs_text_to_speech(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(elevenlabs.handle_elevenlabs_tts, p, info)

    @strawberry.mutation
    async def deepgram_transcribe(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(deepgram.handle_deepgram_transcribe, p, info)

    @strawberry.mutation
    async def imagen_generate(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(imagen.handle_imagen_generate, p, info)

    @strawberry.mutation
    async def veo_generate(self, info: Info, params: JSON) -> JSON:
        p = dict(params) if isinstance(params, dict) else {}
        return await run_ws(veo.handle_veo_generate, p, info)
