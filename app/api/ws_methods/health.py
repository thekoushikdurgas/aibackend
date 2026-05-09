"""
Health check method handlers.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import text

from app.config import settings
from app.database.sqlalchemy import engine
from app.services.rag import ChromaVectorStore
from app.services.llm.factory import LLMProviderFactory

logger = logging.getLogger(__name__)


async def handle_system_health(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Handle system.health method."""
    services = []

    if settings.default_llm_provider == "ollama":
        services.append(await _check_ollama_health())

    services.append(await _check_chromadb_health())

    unhealthy = [
        s for s in services if s.get("status") not in {"healthy", "not_initialized"}
    ]
    overall_status = "healthy" if not unhealthy else "degraded"

    return {
        "status": overall_status,
        "version": "1.0.0",
        "environment": settings.environment,
        "services": services,
        "timestamp": datetime.utcnow().isoformat(),
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
        store = ChromaVectorStore()
        await store.initialize()
        checks["chromadb"] = True
    except Exception as exc:
        details["chromadb_error"] = str(exc)
    try:
        provider = await LLMProviderFactory.get_healthy_provider()
        checks["llm_provider"] = provider is not None
    except Exception as exc:
        details["llm_error"] = str(exc)
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
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
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
            from app.services.rag import ChromaVectorStore

            start = time.time()
            vector_store = ChromaVectorStore()
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
