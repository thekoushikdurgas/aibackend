"""Orbit-compatible workflow helpers over the JSON-RPC gateway."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.orbit.codegen import CodegenError, generate


async def handle_orbit_preview(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Compile an Orbit graph to the workflow.py preview used by the UI."""
    graph = (params or {}).get("graph")
    inputs = (params or {}).get("inputs")
    if not isinstance(graph, dict):
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing graph object")
    if inputs is not None and not isinstance(inputs, dict):
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "inputs must be an object")

    try:
        code = generate(graph, inputs=inputs if isinstance(inputs, dict) else None)
    except CodegenError as exc:
        raise JSONRPCError(JSONRPCErrorCode.VALIDATION_ERROR, str(exc)) from exc

    return {
        "schema": "durgasos.orbit.preview.v1",
        "code": code,
        "node_count": len(graph.get("nodes") or []),
        "edge_count": len(graph.get("edges") or []),
    }


def get_methods() -> Dict[str, Any]:
    return {
        "orbit.preview": handle_orbit_preview,
    }
