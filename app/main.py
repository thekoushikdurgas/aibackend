"""
DurgasAI Backend - FastAPI Application Entry Point
"""

import logging
import inspect
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Awaitable, Callable, cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.requests import ClientDisconnect
from strawberry.fastapi.context import CustomContext

from app.config import settings
from app.utils.logging_filters import OptionalApiKeyWarningFilter
from app.api.auth_session import router as auth_session_router
from app.api.storage_signed_files import router as storage_signed_files_router
from app.api.ws_gateway import websocket_gateway_router
from app.core.graphql_cookie_middleware import GraphqlResponseCookieMiddleware
from app.core.middleware import (
    CorrelationIdMiddleware,
    RequestLoggingMiddleware,
    ErrorHandlerMiddleware,
)
from app.core.rate_limiter import limiter
from app.core.socketio import mount_socketio
from strawberry.fastapi import GraphQLRouter

from app.graphql.context import get_graphql_context
from app.graphql.schema import schema as graphql_schema

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logging.getLogger().addFilter(OptionalApiKeyWarningFilter())
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan handler for startup and shutdown events
    """
    # Startup
    logger.info(f"Starting DurgasAI Backend v{app.version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Default LLM Provider: {settings.default_llm_provider}")

    # Initialize services
    try:
        # Initialize database (SQLAlchemy / SQLite or Postgres)
        from app.database import init_db

        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization skipped: {e}")

    try:
        # Initialize ChromaDB
        from app.services.rag import get_shared_chroma_vector_store

        vector_store = get_shared_chroma_vector_store()
        await vector_store.initialize()
        app.state.vector_store = vector_store
        logger.info("ChromaDB initialized successfully")
    except Exception as e:
        logger.warning(f"ChromaDB initialization skipped: {e}")

    try:
        # Initialize LLM service
        from app.services.llm import get_llm_provider

        llm_provider = get_llm_provider()
        app.state.llm_provider = llm_provider
        logger.info(f"LLM Provider ({settings.default_llm_provider}) initialized")
    except Exception as e:
        logger.warning(f"LLM Provider initialization skipped: {e}")

    try:
        # Initialize RAG pipeline
        from app.services.rag.pipeline import rag_pipeline

        await rag_pipeline.initialize()
        app.state.rag_pipeline = rag_pipeline
        logger.info("RAG Pipeline initialized successfully")
    except Exception as e:
        logger.warning(f"RAG Pipeline initialization skipped: {e}")

    if settings.use_redis:
        try:
            import redis.asyncio as redis

            redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            await redis_client.ping()
            app.state.redis = redis_client
            logger.info("Redis initialized successfully")
        except Exception as e:
            logger.warning(f"Redis initialization skipped: {e}")

    yield

    # Shutdown
    logger.info("Shutting down DurgasAI Backend")

    # Cleanup services
    try:
        from app.database import close_db

        await close_db()
        logger.info("Database connections closed")
    except Exception as e:
        logger.warning(f"Database cleanup error: {e}")

    try:
        if hasattr(app.state, "vector_store"):
            await app.state.vector_store.close()
            logger.info("Vector store closed")
    except Exception as e:
        logger.warning(f"Vector store cleanup error: {e}")

    try:
        if hasattr(app.state, "rag_pipeline") and hasattr(
            app.state.rag_pipeline, "close"
        ):
            maybe_result = app.state.rag_pipeline.close()
            if inspect.isawaitable(maybe_result):
                await maybe_result
            logger.info("RAG pipeline closed")
    except Exception as e:
        logger.warning(f"RAG pipeline cleanup error: {e}")

    try:
        if hasattr(app.state, "llm_provider") and hasattr(
            app.state.llm_provider, "close"
        ):
            maybe_result = app.state.llm_provider.close()
            if inspect.isawaitable(maybe_result):
                await maybe_result
            logger.info("LLM provider closed")
    except Exception as e:
        logger.warning(f"LLM provider cleanup error: {e}")

    try:
        if hasattr(app.state, "redis"):
            await app.state.redis.close()
            logger.info("Redis connections closed")
    except Exception as e:
        logger.warning(f"Redis cleanup error: {e}")


_docs = "/docs" if settings.debug else None
_redoc = "/redoc" if settings.debug else None
_openapi = "/openapi.json" if settings.debug else None

# Create FastAPI application
app = FastAPI(
    title="DurgasAI Backend",
    description="FastAPI backend with AI agents for the DurgasAI Chrome extension",
    version="1.0.0",
    docs_url=_docs,
    redoc_url=_redoc,
    openapi_url=_openapi,
    lifespan=lifespan,
)

# Add rate limiter state
app.state.limiter = limiter

# Configure CORS — explicit origins only (credentials=True is incompatible with "*").
cors_origins = list(
    dict.fromkeys(
        settings.cors_origins_list
        + [
            "http://localhost:8501",
            "http://127.0.0.1:8501",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
)

# Middleware: last added = outermost (runs first on incoming request).
# Target order: CORS -> CorrelationId -> RequestLogging -> ErrorHandler -> Gzip -> routes
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

mount_socketio(app)

app.include_router(auth_session_router)

_files_prefix = (settings.storage_url_prefix or "/files").rstrip("/") or "/files"
app.include_router(storage_signed_files_router, prefix=_files_prefix)

# Include WebSocket gateway (JSON-RPC)
app.include_router(websocket_gateway_router)

# GraphQL (HTTP) — single application HTTP API surface
graphql_router = GraphQLRouter(
    graphql_schema,
    context_getter=cast(
        Callable[..., CustomContext | None | Awaitable[CustomContext | None]],
        get_graphql_context,
    ),
    graphql_ide="graphiql" if settings.debug else None,
)
app.include_router(graphql_router, prefix="/graphql")

# Apply cookies queued by GraphQL session mutations (outermost on response)
app.add_middleware(GraphqlResponseCookieMiddleware)


@app.get("/health", tags=["Health"])
async def health():
    """Minimal liveness for load balancers (GET-only exception to GraphQL HTTP API)."""
    return {"status": "healthy"}


def _unwrap_client_disconnect(exc: BaseException) -> ClientDisconnect | None:
    from app.core.middleware import _find_client_disconnect

    return _find_client_disconnect(exc)


def _is_client_closed_exception(exc: BaseException) -> bool:
    from app.core.middleware import _is_client_closed_exception as is_client_closed

    return is_client_closed(exc)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    disconnect = _unwrap_client_disconnect(exc)
    if (
        disconnect is not None
        or isinstance(exc, ClientDisconnect)
        or _is_client_closed_exception(exc)
    ):
        logger.info(
            "Client disconnected: %s %s",
            request.method,
            request.url.path,
        )
        return Response(status_code=499)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.debug else "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
