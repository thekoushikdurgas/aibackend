"""Stability AI image generation WebSocket handlers."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode


async def handle_stability_generate(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    prompt = params.get("prompt")
    if not prompt:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing prompt")
    key = settings.stability_api_key
    if not key:
        raise JSONRPCError(JSONRPCErrorCode.PROVIDER_ERROR, "STABILITY_API_KEY not set")

    url = f"{settings.stability_base_url.rstrip('/')}/stable-image/generate/core"
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    data = {
        "prompt": prompt,
        "output_format": params.get("output_format", "png"),
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, headers=headers, data=data)
        r.raise_for_status()
        return r.json()


def get_methods() -> Dict[str, Any]:
    return {"stability.generate": handle_stability_generate}
