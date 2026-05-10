"""
Multimodal method handlers (text-to-image, image-to-text, speech-to-text, etc.)
"""

import logging
from typing import Dict, Any, Optional

from app.services.multimodal import (
    TextToImageService,
    ImageToTextService,
    SpeechToTextService,
    TextToSpeechService,
    ObjectDetectionService,
)
from app.utils.file_handler import handle_file_param
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


async def handle_multimodal_text_to_image(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle multimodal.text_to_image method"""
    prompt = params.get("prompt", "")
    model = params.get("model")
    negative_prompt = params.get("negative_prompt")
    num_inference_steps = params.get("num_inference_steps")
    guidance_scale = params.get("guidance_scale")

    if not prompt:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: prompt"
        )

    try:
        service = TextToImageService()
        result = await service.generate(
            prompt=prompt,
            model=model,
            negative_prompt=negative_prompt,
            num_inference_steps=int(num_inference_steps or 50),
            guidance_scale=float(guidance_scale or 7.5),
        )
        return result
    except Exception as e:
        logger.error(f"Text-to-image error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Text-to-image failed: {str(e)}"
        )


async def handle_multimodal_image_to_text(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle multimodal.image_to_text method"""
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
        image_data = image

    try:
        service = ImageToTextService()
        if image_data is None:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS, "Could not resolve image data"
            )
        result = await service.generate(image=image_data, prompt=prompt or None)
        return result
    except Exception as e:
        logger.error(f"Image-to-text error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Image-to-text failed: {str(e)}"
        )


async def handle_multimodal_speech_to_text(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle multimodal.speech_to_text method"""
    audio = params.get("audio")
    language = params.get("language")

    if not audio:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: audio"
        )

    # Handle base64 file
    file_result = handle_file_param({"file": audio}, "file")
    audio_data: str | bytes | None = None
    if file_result:
        audio_data, _ = file_result
    elif isinstance(audio, str):
        audio_data = audio

    try:
        service = SpeechToTextService()
        if audio_data is None:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS, "Could not resolve audio data"
            )
        result = await service.transcribe(audio=audio_data, language=language)
        return result
    except Exception as e:
        logger.error(f"Speech-to-text error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Speech-to-text failed: {str(e)}"
        )


async def handle_multimodal_text_to_speech(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle multimodal.text_to_speech method"""
    text = params.get("text", "")
    _voice = params.get("voice")  # reserved for HF models that support voice selection
    model = params.get("model")

    if not text:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: text"
        )

    try:
        service = TextToSpeechService()
        result = await service.generate(text=text, model=model)
        # Encode audio to base64 for WebSocket
        if result.get("audio"):
            from app.utils.file_handler import encode_base64_file

            audio_data = encode_base64_file(result["audio"], "audio/mpeg")
            result["audio"] = audio_data
        return result
    except Exception as e:
        logger.error(f"Text-to-speech error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Text-to-speech failed: {str(e)}"
        )


async def handle_multimodal_object_detection(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle multimodal.object_detection method"""
    image = params.get("image")

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
        image_data = image

    try:
        service = ObjectDetectionService()
        if image_data is None:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS, "Could not resolve image data"
            )
        if isinstance(image_data, bytes):
            raw = await service.detect(image_data)
        else:
            if image_data.startswith("http://") or image_data.startswith("https://"):
                raw = await service.detect_from_url(image_data)
            else:
                raw = await service.detect_from_base64(image_data)
        return {"detections": raw}
    except Exception as e:
        logger.error(f"Object detection error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Object detection failed: {str(e)}"
        )


def get_methods() -> Dict[str, Any]:
    """Return all methods from this module"""
    return {
        "multimodal.text_to_image": handle_multimodal_text_to_image,
        "multimodal.image_to_text": handle_multimodal_image_to_text,
        "multimodal.speech_to_text": handle_multimodal_speech_to_text,
        "multimodal.text_to_speech": handle_multimodal_text_to_speech,
        "multimodal.object_detection": handle_multimodal_object_detection,
    }
