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
from starlette.middleware.base import BaseHTTPMiddleware
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
        if not cid or not str(cid).strip():
            cid = str(uuid.uuid4())
        else:
            cid = str(cid).strip()[:128]
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
