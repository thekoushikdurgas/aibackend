"""Apply Set-Cookie headers queued during GraphQL execution."""

from __future__ import annotations

from typing import Callable, List

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_ATTR = "graphql_cookie_appliers"


def reset_graphql_cookie_appliers(request: Request) -> None:
    setattr(request.state, _ATTR, [])


def queue_graphql_cookie_applier(
    request: Request, fn: Callable[[Response], None]
) -> None:
    if not hasattr(request.state, _ATTR):
        setattr(request.state, _ATTR, [])
    getattr(request.state, _ATTR).append(fn)


class GraphqlResponseCookieMiddleware(BaseHTTPMiddleware):
    """Runs after the route; applies cookie callbacks registered by GraphQL resolvers."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        appliers: List[Callable[[Response], None]] = getattr(request.state, _ATTR, [])
        for fn in appliers:
            fn(response)
        return response
