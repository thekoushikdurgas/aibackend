"""Hyperbolic WebSocket method handlers."""

from typing import Dict, Any, Optional, AsyncGenerator

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.llm import LLMConfig, get_llm_provider


def _prompt(params: Dict[str, Any]) -> str:
    if params.get("prompt"):
        return str(params["prompt"])
    for msg in reversed(params.get("messages") or []):
        if msg.get("role") == "user":
            return str(msg.get("content", ""))
    return ""


async def handle_hyperbolic_chat(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any] | AsyncGenerator[Dict[str, Any], None]:
    prompt = _prompt(params)
    if not prompt:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing prompt")
    stream = bool(params.get("stream", False))
    provider = get_llm_provider("hyperbolic")
    config = LLMConfig(
        model=params.get("model"),
        temperature=float(params.get("temperature", 0.7)),
        max_tokens=int(params.get("max_tokens", 2048)),
    )
    if stream:

        async def _stream() -> AsyncGenerator[Dict[str, Any], None]:
            async for chunk in provider.stream(prompt=prompt, config=config):
                yield {"type": "chunk", "content": chunk}
            yield {"type": "done"}

        return _stream()
    response = await provider.generate(prompt=prompt, config=config)
    return {
        "provider": "hyperbolic",
        "model": response.model,
        "text": response.text,
        "usage": response.usage,
    }


def get_methods() -> Dict[str, Any]:
    return {"hyperbolic.chat.completions": handle_hyperbolic_chat}
