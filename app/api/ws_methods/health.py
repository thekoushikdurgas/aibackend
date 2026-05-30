"""
Health check method handlers.
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from sqlalchemy import text

from app.config import settings
from app.utils.helpers import utc_now
from app.services.ollama.client import _normalize_ollama_api_base
from app.database.sqlalchemy import engine
from app.services.rag import get_shared_chroma_vector_store
from app.services.llm.factory import LLMProviderFactory

logger = logging.getLogger(__name__)


async def handle_system_health(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle system.health method — checks all core services concurrently."""
    tasks = []

    run_ollama = settings.default_llm_provider == "ollama"
    if run_ollama:
        tasks.append(_check_ollama_health())

    tasks.append(_check_chromadb_health())
    tasks.append(_check_postgres_health())

    run_redis = bool(settings.use_redis)
    if run_redis:
        tasks.append(_check_redis_health())

    from app.api.ws_methods.kafka_health import check_kafka_health, check_minio_health

    tasks.append(check_kafka_health())
    tasks.append(check_minio_health())

    results = await asyncio.gather(*tasks, return_exceptions=False)
    results_dict = {r["name"]: r for r in results}

    services = []

    # Ollama
    if run_ollama:
        services.append(results_dict["ollama"])
    else:
        services.append({"name": "ollama", "status": "not_initialized"})

    # ChromaDB
    services.append(results_dict["chromadb"])

    # Postgres
    services.append(results_dict["postgres"])

    # Redis
    if run_redis:
        services.append(results_dict["redis"])
    else:
        services.append({"name": "redis", "status": "not_initialized"})

    # Kafka
    services.append(
        results_dict.get("kafka", {"name": "kafka", "status": "not_initialized"})
    )

    # MinIO
    services.append(
        results_dict.get("minio", {"name": "minio", "status": "not_initialized"})
    )

    unhealthy = [
        s for s in services if s.get("status") not in {"healthy", "not_initialized"}
    ]
    overall_status = "healthy" if not unhealthy else "degraded"

    return {
        "status": overall_status,
        "version": "1.0.0",
        "environment": settings.environment,
        "services": services,
        "timestamp": utc_now().isoformat(),
    }


async def handle_system_ready(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle system.ready method."""
    checks = {
        "database": False,
        "chromadb": False,
        "llm_provider": False,
    }
    details: Dict[str, Any] = {}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as exc:
        details["database_error"] = str(exc)
    try:
        store = get_shared_chroma_vector_store()
        await store.initialize()
        checks["chromadb"] = True
    except Exception as exc:
        details["chromadb_error"] = str(exc)
    try:
        provider = await LLMProviderFactory.get_healthy_provider()
        checks["llm_provider"] = provider is not None
    except Exception as exc:
        details["llm_error"] = str(exc)

    if settings.use_redis:
        checks["redis"] = False
        try:
            import redis.asyncio as redis_async

            client = redis_async.from_url(settings.redis_url, decode_responses=True)
            try:
                await client.ping()
                checks["redis"] = True
            finally:
                await client.close()
        except Exception as exc:
            details["redis_error"] = str(exc)

    status = "ready" if all(checks.values()) else "not_ready"
    return {"status": status, "checks": checks, "details": details}


async def handle_system_live(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle system.live method."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "alive"}
    except Exception as exc:
        return {"status": "unhealthy", "error": str(exc)}


async def _check_ollama_health() -> Dict[str, Any]:
    """Check Ollama service health."""
    try:
        import httpx

        start = time.time()
        async with httpx.AsyncClient(timeout=5.0) as client:
            base = _normalize_ollama_api_base(settings.ollama_base_url or "")
            tags_url = f"{base.rstrip('/')}/tags"
            response = await client.get(tags_url)
            latency = (time.time() - start) * 1000
            if response.status_code == 200:
                return {
                    "name": "ollama",
                    "status": "healthy",
                    "latency_ms": round(latency, 2),
                }
            return {
                "name": "ollama",
                "status": "unhealthy",
                "error": f"HTTP {response.status_code}",
            }
    except Exception as e:  # pragma: no cover - external dependency
        logger.warning("Ollama health check failed: %s", e)
        return {"name": "ollama", "status": "unavailable", "error": str(e)}


async def _check_chromadb_health() -> Dict[str, Any]:
    """Check ChromaDB health with timeout."""
    try:
        loop = asyncio.get_event_loop()

        def _check_sync():
            from app.services.rag import get_shared_chroma_vector_store

            start = time.time()
            vector_store = get_shared_chroma_vector_store()
            collection = vector_store.get_collection()
            count = collection.count()
            latency = (time.time() - start) * 1000
            return {
                "name": "chromadb",
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "document_count": count,
            }

        return await asyncio.wait_for(
            loop.run_in_executor(None, _check_sync), timeout=5.0
        )
    except asyncio.TimeoutError:
        logger.warning("ChromaDB health check timed out")
        return {
            "name": "chromadb",
            "status": "unhealthy",
            "error": "Health check timed out after 5 seconds",
        }
    except Exception as e:
        logger.warning("ChromaDB health check failed: %s", e)
        return {"name": "chromadb", "status": "unhealthy", "error": str(e)}


def get_methods() -> Dict[str, Any]:
    """Return all methods from this module"""
    return {
        "system.health": handle_system_health,
        "system.ready": handle_system_ready,
        "system.live": handle_system_live,
    }


async def _check_postgres_health() -> Dict[str, Any]:
    """Check PostgreSQL health via SQLAlchemy."""
    try:
        start = time.time()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        return {
            "name": "postgres",
            "status": "healthy",
            "latency_ms": round(latency, 2),
        }
    except Exception as e:
        logger.warning("Postgres health check failed: %s", e)
        return {"name": "postgres", "status": "unhealthy", "error": str(e)}


async def _check_redis_health() -> Dict[str, Any]:
    """Check Redis health via ping."""
    try:
        import redis.asyncio as redis_async

        start = time.time()
        client = redis_async.from_url(settings.redis_url, decode_responses=True)
        try:
            await client.ping()
            latency = (time.time() - start) * 1000
            return {
                "name": "redis",
                "status": "healthy",
                "latency_ms": round(latency, 2),
            }
        finally:
            await client.close()
    except Exception as e:
        logger.warning("Redis health check failed: %s", e)
        return {"name": "redis", "status": "unavailable", "error": str(e)}
