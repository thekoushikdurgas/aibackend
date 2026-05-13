"""
DurgasAI Backend - FastAPI Application Entry Point
"""

import logging
import inspect
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.http_auth_session import router as http_auth_session_router
from app.api.routes.files import router as files_router
from app.api.routes.readiness import router as readiness_router
from app.api.ws_gateway import websocket_gateway_router
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
        from app.services.rag import ChromaVectorStore

        vector_store = ChromaVectorStore()
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
            logger.info("Redis connection closed")
    except Exception as e:
        logger.warning(f"Redis cleanup error: {e}")


# Create FastAPI application
app = FastAPI(
    title="DurgasAI Backend",
    description="FastAPI backend with AI agents for the DurgasAI Chrome extension",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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
# Target order: CORS -> CorrelationId -> RequestLogging -> ErrorHandler -> routes
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

# Include WebSocket gateway (replaces all REST endpoints)
app.include_router(websocket_gateway_router)
app.include_router(readiness_router)
app.include_router(http_auth_session_router)
app.include_router(
    files_router,
    prefix=(settings.storage_url_prefix or "/files").rstrip("/"),
)

# GraphQL (HTTP) — auth and other typed reads/mutations; AI traffic may stay on WebSocket
graphql_router = GraphQLRouter(
    graphql_schema,
    # Strawberry FastAPI stubs expect Callable[..., Awaitable[None]]; runtime accepts async context factories.
    context_getter=get_graphql_context,  # type: ignore[arg-type]
    graphql_ide="graphiql" if settings.debug else None,
)
app.include_router(graphql_router, prefix="/graphql")


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint"""
    return {
        "name": "DurgasAI Backend",
        "version": "1.0.0",
        "status": "running",
        "architecture": "websocket-jsonrpc-and-graphql-http",
        "websocket_endpoint": "/ws/gateway",
        "websocket_protocol": "JSON-RPC 2.0",
        "graphql_endpoint": "/graphql",
        "graphql_protocol": "GraphQL over HTTP POST",
        "session_http": "/api/auth/session",
        "health": "/health",
    }


@app.get("/health")
async def health():
    """Simple HTTP health check for load balancers"""
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
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
