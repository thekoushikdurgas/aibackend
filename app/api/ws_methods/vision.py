"""
Vision method handlers with base64 file support
"""

import logging
from typing import Dict, Any, Optional

from app.services.gemini import GeminiVisionService
from app.services.nvidia import NVIDIAVisionService
from app.utils.file_handler import handle_file_param
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


async def handle_vision_analyze(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle vision.analyze method"""
    image = params.get("image")
    prompt = params.get("prompt", "")

    if not image:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: image"
        )

    # Handle base64 file
    file_result = handle_file_param({"file": image}, "file")
    image_data: str | bytes | None = None
    if file_result:
        image_data, _ = file_result
    elif isinstance(image, str):
        # URL or base64 string
        image_data = image

    config = params.get("config", {})

    if image_data is None:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Could not resolve image data"
        )

    try:
        service = GeminiVisionService()
        result = await service.analyze_image(
            image=image_data, prompt=prompt, config=config
        )

        return {
            "text": result.get("text"),
            "model": result.get("model"),
            "usage": result.get("usage"),
        }
    except Exception as e:
        logger.error(f"Vision analysis error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Vision analysis failed: {str(e)}"
        )


async def handle_vision_nvidia(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle vision.nvidia method"""
    prompt = params.get("prompt")
    if not prompt:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: prompt"
        )

    image = params.get("image")
    image_url = params.get("image_url")
    model = params.get("model")
    max_tokens = params.get("max_tokens")
    temperature = params.get("temperature", 0.7)

    # Handle base64 file
    if image and isinstance(image, dict):
        file_result = handle_file_param({"file": image}, "file")
        if file_result:
            image_bytes, _ = file_result
            # Convert to base64 string for NVIDIA service
            import base64

            image = base64.b64encode(image_bytes).decode("utf-8")

    try:
        service = NVIDIAVisionService()
        result = await service.analyze(
            prompt=prompt,
            image=image,
            image_url=image_url,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

        return {
            "text": result.get("text"),
            "model": result.get("model"),
            "usage": result.get("usage", {}),
        }
    except Exception as e:
        logger.error(f"NVIDIA vision analysis error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"NVIDIA vision analysis failed: {str(e)}"
        )


def get_methods() -> Dict[str, Any]:
    """Return all methods from this module"""
    return {
        "vision.analyze": handle_vision_analyze,
        "vision.nvidia": handle_vision_nvidia,
    }
