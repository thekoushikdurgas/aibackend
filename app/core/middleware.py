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

# 499 = client closed request (common nginx convention; body is not delivered)
_CLIENT_CLOSED_STATUS = 499


def _exception_subexceptions(exc: BaseException) -> tuple[BaseException, ...]:
    """Return nested exceptions from ExceptionGroup / BaseExceptionGroup (3.11+)."""
    subs = getattr(exc, "exceptions", None)
    if isinstance(subs, tuple):
        return subs
    return ()


def _find_client_disconnect(exc: BaseException) -> Optional[ClientDisconnect]:
    """Return ClientDisconnect from exc or from a BaseHTTPMiddleware ExceptionGroup."""
    if isinstance(exc, ClientDisconnect):
        return exc
    for sub in _exception_subexceptions(exc):
        found = _find_client_disconnect(sub)
        if found is not None:
            return found
    return None


def _is_no_response_returned(exc: BaseException) -> bool:
    """True when BaseHTTPMiddleware reports an already-disconnected client."""
    if isinstance(exc, RuntimeError) and str(exc) == "No response returned.":
        return True
    return any(_is_no_response_returned(sub) for sub in _exception_subexceptions(exc))


def _is_client_closed_exception(exc: BaseException) -> bool:
    return _find_client_disconnect(exc) is not None or _is_no_response_returned(exc)


def _client_closed_response() -> Response:
    return Response(status_code=_CLIENT_CLOSED_STATUS)


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
            try:
                response = await call_next(request)
            except BaseException as exc:
                if _is_client_closed_exception(exc):
                    return _client_closed_response()
                raise
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
        try:
            response = await call_next(request)
        except BaseException as exc:
            if _is_client_closed_exception(exc):
                logger.info(
                    "Client disconnected during %s %s",
                    request.method,
                    request.url.path,
                )
                return _client_closed_response()
            raise

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
            logger.info(
                "Client disconnected during %s %s",
                request.method,
                request.url.path,
            )
            return _client_closed_response()
        except StarletteHTTPException:
            raise
        except GraphQLError:
            # Let Strawberry/GraphQL format resolver errors (do not return generic JSON 500).
            raise
        except Exception as exc:
            if _is_client_closed_exception(exc):
                logger.info(
                    "Client disconnected during %s %s",
                    request.method,
                    request.url.path,
                )
                return _client_closed_response()
            logger.error(f"Error processing request: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "path": request.url.path},
            )
        except BaseException as exc:
            if _is_client_closed_exception(exc):
                logger.info(
                    "Client disconnected during %s %s",
                    request.method,
                    request.url.path,
                )
                return _client_closed_response()
            raise


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
