"""Veo WebSocket method handlers."""

from typing import Dict, Any, Optional
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.gemini.veo import VeoService


async def handle_veo_generate(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    service = VeoService()
    if params.get("operation_name"):
        if params.get("result", False):
            return await service.get_result(params["operation_name"])
        return await service.get_status(params["operation_name"])

    prompt = params.get("prompt")
    if not prompt:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing prompt")
    return await service.generate(
        prompt=prompt,
        aspect_ratio=params.get("aspect_ratio"),
        duration=params.get("duration"),
    )


def get_methods() -> Dict[str, Any]:
    return {"veo.generate": handle_veo_generate}
