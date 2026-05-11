"""Helpers to invoke WebSocket JSON-RPC handlers from GraphQL resolvers."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from strawberry.types import Info

from app.core.auth import user_claims_from_access_token
from app.core.jsonrpc import JSONRPCError
from app.graphql.context import GraphQLContext
from app.graphql.errors import raise_jsonrpc_as_graphql


def graphql_params(params: Any) -> Dict[str, Any]:
    """Normalize Strawberry JSON / optional dict inputs for ws_methods."""
    if not isinstance(params, dict):
        return {}
    return {str(k): v for k, v in params.items()}


def user_from_info(info: Info) -> Optional[Dict[str, Any]]:
    """Map Bearer token to the user dict shape expected by ws_methods."""
    ctx = info.context
    if not isinstance(ctx, GraphQLContext) or not ctx.auth_token:
        return None
    data = user_claims_from_access_token(ctx.auth_token)
    if not data:
        return None
    sub = data.get("sub")
    return {
        "sub": sub,
        "id": sub,
        "email": data.get("email"),
        "user_metadata": data.get("user_metadata") or {},
        "app_metadata": data.get("app_metadata") or {},
    }


async def run_ws(
    handler: Callable[..., Any],
    params: Dict[str, Any],
    info: Info,
) -> Any:
    """Run a ws_methods handler with GraphQL auth context."""
    user = user_from_info(info)
    try:
        return await handler(params, user, None)
    except JSONRPCError as e:
        raise_jsonrpc_as_graphql(e)


async def run_ws_chat_completion(
    handler: Callable[..., Any],
    params: Dict[str, Any],
    info: Info,
) -> Any:
    """Ensure chat completions are non-streaming for GraphQL."""
    merged = {**params, "stream": False}
    return await run_ws(handler, merged, info)
