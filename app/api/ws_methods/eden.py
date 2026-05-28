"""Eden AI aggregator WebSocket handlers."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode


async def handle_eden_chat(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    text = params.get("text") or params.get("prompt")
    providers = params.get("providers") or ["openai"]
    if not text:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing text/prompt")
    key = settings.eden_api_key
    if not key:
        raise JSONRPCError(JSONRPCErrorCode.PROVIDER_ERROR, "EDEN_API_KEY not set")

    url = f"{settings.eden_base_url.rstrip('/')}/text/chat"
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = {
        "providers": providers,
        "text": text,
        "chatbot_global_action": params.get("system", "You are a helpful assistant."),
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        return r.json()


def get_methods() -> Dict[str, Any]:
    return {"eden.chat": handle_eden_chat}
