"""
Ollama method handlers
"""

import logging
from typing import Dict, Any, Optional, AsyncGenerator

from app.services.ollama import (
    OllamaGenerateService,
    OllamaModelService,
)
from app.services.llm.base import LLMConfig
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


async def handle_ollama_generate(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle ollama.generate method"""
    model = params.get("model")
    prompt = params.get("prompt", "")
    stream = params.get("stream", False)
    temperature = params.get("temperature", 0.7)
    max_tokens = params.get("max_tokens")

    if not model:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: model"
        )

    try:
        service = OllamaGenerateService()
        config = LLMConfig(model=model, temperature=temperature, max_tokens=max_tokens)

        if stream:
            return _stream_ollama_generate(service, prompt, config)

        response = await service.generate(prompt, config=config)
        return {
            "response": response.text,
            "model": response.model,
            "done": True,
            "usage": response.usage,
            "finish_reason": response.finish_reason,
        }
    except Exception as e:
        logger.error(f"Ollama generate error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Ollama generate failed: {str(e)}"
        )


async def _stream_ollama_generate(
    service: OllamaGenerateService, prompt: str, config: LLMConfig
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream Ollama generation"""
    yield {"type": "start", "provider": "ollama", "model": config.model}
    async for chunk in service.stream(prompt, config=config):
        yield {"type": "chunk", "content": chunk}
    yield {"type": "done"}


async def handle_ollama_chat(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle ollama.chat method"""
    model = params.get("model")
    messages = params.get("messages", [])
    stream = params.get("stream", False)
    temperature = params.get("temperature", 0.7)
    max_tokens = params.get("max_tokens")

    if not model:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: model"
        )

    try:
        service = OllamaGenerateService()
        config = LLMConfig(model=model, temperature=temperature, max_tokens=max_tokens)

        if stream:
            return _stream_ollama_chat(service, messages, config)

        response = await service.chat(messages, config=config)
        return {
            "response": response.text,
            "model": response.model,
            "done": True,
            "usage": response.usage,
        }
    except Exception as e:
        logger.error(f"Ollama chat error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Ollama chat failed: {str(e)}"
        )


async def _stream_ollama_chat(
    service: OllamaGenerateService, messages: list, config: LLMConfig
) -> AsyncGenerator[Dict[str, Any], None]:
    """Stream Ollama chat"""
    yield {"type": "start", "provider": "ollama", "model": config.model}
    async for chunk in service.stream_chat(messages, config=config):
        yield {"type": "chunk", "content": chunk}
    yield {"type": "done"}


async def handle_ollama_models_list(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle ollama.models.list method"""
    try:
        service = OllamaModelService()
        models = await service.list_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Ollama models list error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Failed to list models: {str(e)}"
        )


async def handle_ollama_models_pull(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle ollama.models.pull method"""
    model_name = params.get("model_name")
    if not model_name:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing required parameter: model_name"
        )

    try:
        service = OllamaModelService()
        # Collect all progress updates and return the final result
        final_result = None
        async for progress in service.pull_model(model_name, stream_progress=True):
            final_result = progress
            # If we get a success status, we can return early
            if progress.get("status") == "success":
                break
        return final_result or {"status": "completed", "model": model_name}
    except Exception as e:
        logger.error(f"Ollama model pull error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Failed to pull model: {str(e)}"
        )


def get_methods() -> Dict[str, Any]:
    """Return all methods from this module"""
    return {
        "ollama.generate": handle_ollama_generate,
        "ollama.chat": handle_ollama_chat,
        "ollama.models.list": handle_ollama_models_list,
        "ollama.models.pull": handle_ollama_models_pull,
    }
