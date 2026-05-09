"""Fal.ai method handlers."""

from typing import Dict, Any, Optional
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.fal.client import FalClient
from app.services.fal.queue_manager import QueueManager
from app.services.fal.image_generation import ImageGenerationService
from app.services.fal.audio_generation import AudioGenerationService
from app.services.fal.video_generation import VideoGenerationService


def _fal_services():
    client = FalClient()
    queue = QueueManager(client)
    return (
        ImageGenerationService(client, queue),
        AudioGenerationService(client, queue),
        VideoGenerationService(client, queue),
    )


async def handle_fal_images(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = params.get("prompt")
    if not prompt:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing prompt")
    image_service, _, _ = _fal_services()
    variant = (params.get("variant") or "flux").lower()
    wait = bool(params.get("wait", True))
    if variant == "imagen4":
        return await image_service.generate_imagen4(prompt=prompt, wait=wait, **params)
    if variant == "veo3":
        return await image_service.generate_veo3(prompt=prompt, wait=wait, **params)
    return await image_service.generate_flux_pro(prompt=prompt, wait=wait, **params)


async def handle_fal_audio(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    lyrics = params.get("lyrics")
    genres = params.get("genres")
    if not lyrics or not genres:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing lyrics/genres")
    _, audio_service, _ = _fal_services()
    return await audio_service.generate_music(
        lyrics=lyrics,
        genres=genres,
        wait=bool(params.get("wait", True)),
        duration=params.get("duration"),
        tempo=params.get("tempo"),
    )


async def handle_fal_video(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = params.get("prompt")
    if not prompt:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing prompt")
    _, _, video_service = _fal_services()
    wait = bool(params.get("wait", True))
    if params.get("image_url"):
        return await video_service.generate_from_image(
            prompt=prompt,
            image_url=params["image_url"],
            wait=wait,
            duration=params.get("duration"),
            aspect_ratio=params.get("aspect_ratio"),
            fps=params.get("fps"),
        )
    return await video_service.generate_from_text(
        prompt=prompt,
        wait=wait,
        duration=params.get("duration"),
        aspect_ratio=params.get("aspect_ratio"),
        fps=params.get("fps"),
    )


def get_methods() -> Dict[str, Any]:
    return {
        "fal.images.generate": handle_fal_images,
        "fal.audio.generate": handle_fal_audio,
        "fal.video.generate": handle_fal_video,
    }
