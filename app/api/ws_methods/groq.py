"""
Groq method handlers
"""

import logging
from typing import Dict, Any, Optional, AsyncGenerator

from app.services.llm.groq import GroqProvider
from app.services.llm.groq_models import GroqModelSelector
from app.services.multimodal.groq_vision import GroqVisionService
from app.services.multimodal.groq_speech import GroqSpeechToTextService
from app.services.llm.base import LLMConfig
from app.utils.file_handler import handle_file_param
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


async def handle_groq_chat_completions(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle groq.chat.completions method"""
    messages = params.get("messages", [])
    model = params.get("model")
    temperature = float(params.get("temperature", 0.7))
    max_tokens = int(params.get("max_tokens") or 2048)
    stream = params.get("stream", False)

    if not messages:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: messages"
        )

    try:
        provider = GroqProvider()
        config = LLMConfig(model=model, temperature=temperature, max_tokens=max_tokens)

        # Extract prompt and history
        prompt = ""
        conversation_history = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user" and not prompt:
                prompt = content
            else:
                conversation_history.append({"role": role, "content": content})

        if stream:
            return _stream_groq_chat(provider, prompt, config, conversation_history)

        response = await provider.generate(
            prompt=prompt, config=config, conversation_history=conversation_history
        )

        return {
            "id": f"groq-{response.model}",
            "object": "chat.completion",
            "model": response.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": response.text},
                    "finish_reason": response.finish_reason,
                }
            ],
            "usage": response.usage,
        }
    except Exception as e:
        logger.error(f"Groq chat error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Groq chat failed: {str(e)}"
        )


async def _stream_groq_chat(
    provider: GroqProvider, prompt: str, config: LLMConfig, history: list
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream Groq chat response"""
    yield {"type": "start", "provider": "groq", "model": config.model}
    async for chunk in provider.stream(
        prompt, config=config, conversation_history=history
    ):
        yield {"type": "chunk", "content": chunk}
    yield {"type": "done"}


async def handle_groq_vision_analyze(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle groq.vision.analyze method"""
    prompt = params.get("prompt", "")
    image = params.get("image")

    if not image:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: image"
        )

    # Handle base64 file
    file_result = handle_file_param({"file": image}, "file")
    image_data = None
    if file_result:
        image_data, _ = file_result
    elif isinstance(image, str):
        image_data = image

    try:
        service = GroqVisionService()
        result = await service.analyze(image=image_data, prompt=prompt)
        return result
    except Exception as e:
        logger.error(f"Groq vision error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Groq vision failed: {str(e)}"
        )


async def handle_groq_transcribe(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle groq.transcribe method"""
    audio = params.get("audio")
    if not audio:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: audio"
        )

    # Handle base64 file
    file_result = handle_file_param({"file": audio}, "file")
    audio_data = None
    if file_result:
        audio_data, _ = file_result
    elif isinstance(audio, str):
        audio_data = audio

    try:
        service = GroqSpeechToTextService()
        result = await service.transcribe(audio=audio_data)
        return result
    except Exception as e:
        logger.error(f"Groq transcribe error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Groq transcribe failed: {str(e)}"
        )


async def handle_groq_models_list(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle groq.models.list method"""
    try:
        selector = GroqModelSelector()
        models = selector.list_models()
        return {"object": "list", "data": models}
    except Exception as e:
        logger.error(f"Groq models list error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Failed to list models: {str(e)}"
        )


def get_methods() -> Dict[str, Any]:
    """Return all methods from this module"""
    return {
        "groq.chat.completions": handle_groq_chat_completions,
        "groq.vision.analyze": handle_groq_vision_analyze,
        "groq.transcribe": handle_groq_transcribe,
        "groq.models.list": handle_groq_models_list,
    }
