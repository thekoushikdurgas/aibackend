"""Per-request GraphQL context (Bearer token for authenticated operations)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from starlette.requests import Request
from strawberry.fastapi.context import BaseContext

from app.core.graphql_cookie_middleware import reset_graphql_cookie_appliers
from app.core.session_cookies import ACCESS_TOKEN_COOKIE


@dataclass
class GraphQLContext(BaseContext):
    """Request-scoped context passed to Strawberry resolvers."""

    request: Request
    auth_token: Optional[str] = None
    background_tasks: Optional[Any] = None

    def __post_init__(self) -> None:
        super().__init__()


async def get_graphql_context(
    request: Request,
    background_tasks: Optional[Any] = None,
) -> GraphQLContext:
    reset_graphql_cookie_appliers(request)
    raw = request.headers.get("authorization") or ""
    token: Optional[str] = None
    if raw.lower().startswith("bearer "):
        token = raw[7:].strip() or None
    if token is None:
        token = request.cookies.get(ACCESS_TOKEN_COOKIE) or None
    bt = background_tasks
    if bt is None:
        bt = getattr(request.state, "background_tasks", None)
    return GraphQLContext(request=request, auth_token=token, background_tasks=bt)
