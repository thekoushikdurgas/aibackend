"""ElevenLabs WebSocket method handlers."""

from typing import Dict, Any, Optional

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.multimodal.elevenlabs_tts import ElevenLabsTextToSpeechService


async def handle_elevenlabs_tts(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    text = params.get("text")
    if not text:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing text")
    service = ElevenLabsTextToSpeechService()
    return await service.generate(
        text=text,
        voice_id=params.get("voice_id"),
        model_id=params.get("model_id"),
        output_format=params.get("output_format", "mp3_44100_128"),
        voice_settings=params.get("voice_settings"),
        pronunciation_dictionary_locators=params.get(
            "pronunciation_dictionary_locators"
        ),
    )


def get_methods() -> Dict[str, Any]:
    return {"elevenlabs.text_to_speech": handle_elevenlabs_tts}
