"""Replicate prediction API WebSocket handlers."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode


async def handle_replicate_run(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    version = params.get("version")
    input_payload = params.get("input")
    if not version or not isinstance(input_payload, dict):
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Missing version or input object"
        )
    key = settings.replicate_api_key
    if not key:
        raise JSONRPCError(JSONRPCErrorCode.PROVIDER_ERROR, "REPLICATE_API_KEY not set")

    url = f"{settings.replicate_base_url.rstrip('/')}/predictions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    body = {"version": version, "input": input_payload}
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        return r.json()


def get_methods() -> Dict[str, Any]:
    return {"replicate.run": handle_replicate_run}
