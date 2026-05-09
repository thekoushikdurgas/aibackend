"""OpenRouter WebSocket method handlers."""

from typing import Dict, Any, Optional, AsyncGenerator

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.llm import LLMConfig, get_llm_provider
from app.services.openrouter.model_registry import OpenRouterModelRegistry


async def handle_openrouter_chat(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
    prompt = params.get("prompt")
    if not prompt:
        msgs = params.get("messages") or []
        prompt = next(
            (m.get("content") for m in reversed(msgs) if m.get("role") == "user"), ""
        )
    if not prompt:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing prompt")

    provider = get_llm_provider("openrouter")
    config = LLMConfig(
        model=params.get("model"),
        temperature=float(params.get("temperature", 0.7)),
        max_tokens=int(params.get("max_tokens", 2048)),
    )
    if bool(params.get("stream", False)):

        async def _stream() -> AsyncGenerator[Dict[str, Any], None]:
            async for chunk in provider.stream(prompt=str(prompt), config=config):
                yield {"type": "chunk", "content": chunk}
            yield {"type": "done"}

        return _stream()

    response = await provider.generate(prompt=str(prompt), config=config)
    return {
        "provider": "openrouter",
        "model": response.model,
        "text": response.text,
        "usage": response.usage,
    }


async def handle_openrouter_models_list(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    force_refresh = bool(params.get("force_refresh", False))
    registry = OpenRouterModelRegistry()
    models = await registry.fetch_models(force_refresh=force_refresh)
    return {"models": models, "count": len(models)}


def get_methods() -> Dict[str, Any]:
    return {
        "openrouter.chat.completions": handle_openrouter_chat,
        "openrouter.models.list": handle_openrouter_models_list,
    }
