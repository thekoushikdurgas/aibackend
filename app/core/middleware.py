"""
Custom middleware for DurgasAI Backend
"""

import time
import logging
import uuid
from contextvars import ContextVar
from typing import Callable, List, Optional

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from graphql import GraphQLError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import ClientDisconnect
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

CORRELATION_ID_HEADER = "X-Request-ID"
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar(
    "correlation_id", default=None
)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Propagate or generate X-Request-ID for request/response tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        cid = request.headers.get(CORRELATION_ID_HEADER)
        if not cid or not cid.strip():
            cid = str(uuid.uuid4())
        else:
            cid = cid.strip()[:128]
        request.state.correlation_id = cid
        token = correlation_id_ctx.set(cid)
        try:
            response = await call_next(request)
            response.headers[CORRELATION_ID_HEADER] = cid
            return response
        finally:
            correlation_id_ctx.reset(token)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all incoming requests
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        cid = getattr(request.state, "correlation_id", None)
        cid_part = f" [{cid}]" if cid else ""

        # Log request
        logger.info(f"Request{cid_part}: {request.method} {request.url.path}")

        # Process request
        response = await call_next(request)

        if response.status_code == 400 and request.url.path.rstrip("/").endswith(
            "graphql"
        ):
            logger.warning(
                "GraphQL HTTP 400%s: content_type=%r content_length=%r user_agent=%r",
                cid_part,
                request.headers.get("content-type"),
                request.headers.get("content-length"),
                request.headers.get("user-agent"),
            )

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        logger.info(
            f"Response{cid_part}: {request.method} {request.url.path} "
            f"- Status: {response.status_code} "
            f"- Duration: {duration:.3f}s"
        )

        # Add timing header
        response.headers["X-Process-Time"] = f"{duration:.3f}"

        return response


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for handling errors gracefully
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except RequestValidationError as exc:
            logger.error(f"Validation error on {request.url.path}: {exc.errors()}")
            raise
        except ClientDisconnect:
            # Client closed the socket while the body was still streaming (common for
            # large GraphQL uploads). Do not return JSON — the connection is gone and
            # doing so triggers RuntimeError("No response returned.") in BaseHTTPMiddleware.
            logger.info(
                "Client disconnected during %s %s",
                request.method,
                request.url.path,
            )
            raise
        except StarletteHTTPException:
            raise
        except GraphQLError:
            # Let Strawberry/GraphQL format resolver errors (do not return generic JSON 500).
            raise
        except Exception as exc:
            logger.error(f"Error processing request: {exc}", exc_info=True)

            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "path": request.url.path},
            )


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Optional middleware for API key validation on all requests
    """

    def __init__(
        self,
        app,
        api_key: str,
        exclude_paths: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.api_key = api_key
        self.exclude_paths = exclude_paths or [
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/health",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != self.api_key:
            return JSONResponse(
                status_code=401, content={"detail": "Invalid or missing API key"}
            )

        return await call_next(request)
