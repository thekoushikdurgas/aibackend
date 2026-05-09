"""Cerebras WebSocket method handlers."""

from typing import Dict, Any, Optional, AsyncGenerator

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.llm import LLMConfig, get_llm_provider


def _extract_prompt(params: Dict[str, Any]) -> str:
    if params.get("prompt"):
        return str(params["prompt"])
    messages = params.get("messages") or []
    for msg in reversed(messages):
        if msg.get("role") == "user" and msg.get("content"):
            return str(msg["content"])
    return ""


async def handle_cerebras_chat(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
    prompt = _extract_prompt(params)
    if not prompt:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing prompt or user message"
        )

    stream = bool(params.get("stream", False))
    config = LLMConfig(
        model=params.get("model"),
        temperature=float(params.get("temperature", 0.7)),
        max_tokens=int(params.get("max_tokens", 2048)),
        top_p=float(params.get("top_p", 0.9)),
    )
    provider = get_llm_provider("cerebras")

    if stream:

        async def _stream() -> AsyncGenerator[Dict[str, Any], None]:
            async for chunk in provider.stream(prompt=prompt, config=config):
                yield {"type": "chunk", "content": chunk}
            yield {"type": "done"}

        return _stream()

    response = await provider.generate(prompt=prompt, config=config)
    return {
        "provider": "cerebras",
        "model": response.model,
        "text": response.text,
        "usage": response.usage,
        "finish_reason": response.finish_reason,
    }


def get_methods() -> Dict[str, Any]:
    return {"cerebras.chat": handle_cerebras_chat}
