"""HTTP readiness and aggregated API status."""

from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.ws_methods.health import handle_system_health, handle_system_ready
from app.config import settings

router = APIRouter(tags=["readiness"])


def _failing_checks(ready_payload: Dict[str, Any]) -> List[str]:
    checks = ready_payload.get("checks") or {}
    return [name for name, ok in checks.items() if not ok]


@router.get("/ready")
async def ready() -> JSONResponse:
    """
    Deep readiness: database, ChromaDB, LLM provider, and Redis (if enabled).
    Returns 503 if any required check fails.
    """
    payload = await handle_system_ready({}, None, None)
    is_ready = payload.get("status") == "ready"
    failing = _failing_checks(payload) if not is_ready else []
    body: Dict[str, Any] = {
        "ready": is_ready,
        "checks": payload.get("checks", {}),
        "details": payload.get("details", {}),
    }
    if failing:
        body["failing"] = failing
    status = 200 if is_ready else 503
    return JSONResponse(content=body, status_code=status)


@router.get("/api/status")
async def api_status() -> Dict[str, Any]:
    """
    Human-readable summary: same discovery fields as GET / plus live health and ready payloads.
    """
    from app.api.ws_gateway import connection_manager, gateway

    health = await handle_system_health({}, None, None)
    ready_payload = await handle_system_ready({}, None, None)
    return {
        "name": "DurgasAI Backend",
        "version": "1.0.0",
        "status": "running",
        "architecture": "websocket-jsonrpc-and-graphql-http",
        "websocket_endpoint": "/ws/gateway",
        "websocket_protocol": "JSON-RPC 2.0",
        "graphql_endpoint": "/graphql",
        "graphql_protocol": "GraphQL over HTTP POST",
        "session_http": "/api/auth/session",
        "health": "/health",
        "ready": "/ready",
        "environment": settings.environment,
        "websocket": {
            "active_connections": connection_manager.get_connection_count(),
            "registered_methods": len(gateway.methods),
        },
        "system_health": health,
        "system_ready": ready_payload,
    }
