"""Imagen WebSocket method handlers."""

from typing import Dict, Any, Optional
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.gemini.imagen import ImagenService


async def handle_imagen_generate(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = params.get("prompt")
    if not prompt:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing prompt")
    service = ImagenService()
    return await service.generate(
        prompt=prompt,
        aspect_ratio=params.get("aspect_ratio"),
        number_of_images=int(params.get("number_of_images", 1)),
        safety_filter_level=params.get("safety_filter_level"),
        person_generation=params.get("person_generation"),
        seed=params.get("seed"),
    )


def get_methods() -> Dict[str, Any]:
    return {"imagen.generate": handle_imagen_generate}
