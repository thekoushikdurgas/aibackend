"""
NVIDIA method handlers
"""

import logging
from typing import Dict, Any, Optional, AsyncGenerator

from app.services.nvidia import (
    NVIDIAChatService,
    NVIDIAVisionService,
    NVIDIAEmbeddingService,
)
from app.services.llm.base import LLMConfig
from app.utils.file_handler import handle_file_param
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


async def handle_nvidia_chat_completions(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
    """Handle nvidia.chat.completions method"""
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
        service = NVIDIAChatService()
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
            return _stream_nvidia_chat(service, prompt, config, conversation_history)

        response = await service.generate(
            prompt=prompt, config=config, conversation_history=conversation_history
        )

        return {
            "id": f"nvidia-{response.model}",
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
        logger.error(f"NVIDIA chat error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"NVIDIA chat failed: {str(e)}"
        )


async def _stream_nvidia_chat(
    service: NVIDIAChatService, prompt: str, config: LLMConfig, history: list
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream NVIDIA chat response"""
    yield {"type": "start", "provider": "nvidia", "model": config.model}
    async for chunk in service.stream(
        prompt, config=config, conversation_history=history
    ):
        yield {"type": "chunk", "content": chunk}
    yield {"type": "done"}


async def handle_nvidia_vision_analyze(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle nvidia.vision.analyze method"""
    prompt = params.get("prompt", "")
    image = params.get("image")
    image_url = params.get("image_url")
    model = params.get("model")
    max_tokens = params.get("max_tokens")
    temperature = params.get("temperature", 0.7)

    nvidia_image: str | bytes | None = None
    img_in = image
    if img_in and isinstance(img_in, dict):
        file_result = handle_file_param({"file": img_in}, "file")
        if file_result:
            import base64

            image_bytes, _ = file_result
            nvidia_image = base64.b64encode(image_bytes).decode("utf-8")
    elif isinstance(img_in, (str, bytes)):
        nvidia_image = img_in

    try:
        service = NVIDIAVisionService()
        result = await service.analyze(
            prompt=prompt,
            image=nvidia_image,
            image_url=image_url,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return result
    except Exception as e:
        logger.error(f"NVIDIA vision error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"NVIDIA vision failed: {str(e)}"
        )


async def handle_nvidia_embeddings(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle nvidia.embeddings method"""
    text = params.get("text")
    texts = params.get("texts")  # Batch
    model = params.get("model")

    if not text and not texts:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: text or texts"
        )

    try:
        service = NVIDIAEmbeddingService()
        if texts:
            result = await service.embed(texts, model=model)
        else:
            result = await service.embed(text or "", model=model)
        return result
    except Exception as e:
        logger.error(f"NVIDIA embeddings error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"NVIDIA embeddings failed: {str(e)}"
        )


async def handle_nvidia_models_list(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle nvidia.models.list method"""
    try:
        service = NVIDIAChatService()
        models = await service.list_models()
        return {
            "object": "list",
            "data": [
                {"id": model_id, "object": "model", "owned_by": "nvidia"}
                for model_id in models
            ],
        }
    except Exception as e:
        logger.error(f"NVIDIA models list error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Failed to list models: {str(e)}"
        )


def get_methods() -> Dict[str, Any]:
    """Return all methods from this module"""
    return {
        "nvidia.chat.completions": handle_nvidia_chat_completions,
        "nvidia.vision.analyze": handle_nvidia_vision_analyze,
        "nvidia.embeddings": handle_nvidia_embeddings,
        "nvidia.models.list": handle_nvidia_models_list,
    }
