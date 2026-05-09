"""Deepgram WebSocket method handlers."""

from typing import Dict, Any, Optional
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.multimodal.deepgram_speech import DeepgramSpeechToTextService


async def handle_deepgram_transcribe(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    audio = params.get("audio")
    if not audio:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing audio")
    service = DeepgramSpeechToTextService()
    return await service.transcribe(
        audio=audio,
        model=params.get("model"),
        language=params.get("language"),
        punctuate=bool(params.get("punctuate", True)),
        diarize=bool(params.get("diarize", False)),
        smart_format=bool(params.get("smart_format", True)),
        detect_language=bool(params.get("detect_language", False)),
        return_timestamps=bool(params.get("return_timestamps", False)),
    )


def get_methods() -> Dict[str, Any]:
    return {"deepgram.transcribe": handle_deepgram_transcribe}
