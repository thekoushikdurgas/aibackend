"""
Custom middleware for DurgasAI Backend
"""

import time
import logging
from typing import Callable, List, Optional

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all incoming requests
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} "
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
