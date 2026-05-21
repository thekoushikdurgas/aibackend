"""System health GraphQL module."""

from __future__ import annotations

import json
from typing import cast

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import health as health_handlers
from app.core.response_cache import cached_json_response
from app.graphql.context import GraphQLContext
from app.graphql.modules.util import graphql_params, run_ws


@strawberry.type
class HealthQuery:
    @strawberry.field
    async def system_health(self, info: Info, params: JSON | None = None) -> JSON:
        p = graphql_params(params)
        ctx = info.context
        req = ctx.request if isinstance(ctx, GraphQLContext) else None
        if req is not None:
            key = (
                f"gql:system_health:{hash(json.dumps(p, sort_keys=True, default=str))}"
            )
            return await cached_json_response(
                req,
                key,
                15.0,
                lambda: run_ws(health_handlers.handle_system_health, p, info),
            )
        return await run_ws(health_handlers.handle_system_health, p, info)

    @strawberry.field
    async def system_ready(self, info: Info, params: JSON | None = None) -> JSON:
        p = graphql_params(params)
        ctx = info.context
        req = ctx.request if isinstance(ctx, GraphQLContext) else None
        if req is not None:
            key = f"gql:system_ready:{hash(json.dumps(p, sort_keys=True, default=str))}"
            return await cached_json_response(
                req,
                key,
                15.0,
                lambda: run_ws(health_handlers.handle_system_ready, p, info),
            )
        return await run_ws(health_handlers.handle_system_ready, p, info)

    @strawberry.field
    async def websocket_gateway_status(self, info: Info) -> JSON:
        """Replaces ``GET /ws/status``."""
        from app.api.ws_gateway import connection_manager, gateway

        return cast(
            JSON,
            {
                "active_connections": connection_manager.get_connection_count(),
                "registered_methods": len(gateway.methods),
                "status": "running",
            },
        )

    @strawberry.field
    async def api_discovery(self, info: Info) -> JSON:
        """Replaces ``GET /`` and ``GET /api/status`` style discovery payloads."""
        from app.api.ws_gateway import connection_manager, gateway
        from app.config import settings as app_settings

        health = await run_ws(health_handlers.handle_system_health, {}, info)
        ready_payload = await run_ws(health_handlers.handle_system_ready, {}, info)
        return cast(
            JSON,
            {
                "name": "DurgasAI Backend",
                "version": "1.0.0",
                "status": "running",
                "architecture": "websocket-jsonrpc-and-graphql-http",
                "graphql_endpoint": "/graphql",
                "graphql_protocol": "GraphQL over HTTP POST",
                "websocket_endpoint": "/ws/gateway",
                "websocket_protocol": "JSON-RPC 2.0",
                "environment": app_settings.environment,
                "websocket": {
                    "active_connections": connection_manager.get_connection_count(),
                    "registered_methods": len(gateway.methods),
                },
                "system_health": health,
                "system_ready": ready_payload,
            },
        )
