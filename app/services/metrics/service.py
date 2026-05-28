"""
High-level metrics API for JSON-RPC / WebSocket handlers.
Aggregates in-process WebSocket metrics (no DB required for summary).
"""

from __future__ import annotations

from typing import Any, Dict

from app.services.metrics.websocket_metrics import websocket_metrics


class MetricsService:
    """Facade used by `app.api.ws_methods.metrics`."""

    async def get_summary(self) -> Dict[str, Any]:
        stats = websocket_metrics.get_stats()
        return {
            "total_requests": stats.get("message_count", 0),
            "total_tokens": stats.get("total_tokens", 0),
            "providers": stats.get("token_usage", {}),
            "websocket": stats,
        }

    async def get_provider_metrics(self) -> Dict[str, Any]:
        return websocket_metrics.get_provider_stats()
