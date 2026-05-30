"""Kafka and MinIO health check helpers for system health queries."""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def check_kafka_health() -> Dict[str, Any]:
    """Check Kafka broker connectivity."""
    from app.config import settings

    if not settings.kafka_bootstrap_servers:
        return {"name": "kafka", "status": "not_configured", "broker": None}
    try:
        from aiokafka.admin import AIOKafkaAdminClient

        client = AIOKafkaAdminClient(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            request_timeout_ms=3000,
        )
        await client.start()
        topics = await client.list_topics()
        await client.close()
        return {
            "name": "kafka",
            "status": "healthy",
            "broker": settings.kafka_bootstrap_servers,
            "topic_count": len(topics),
        }
    except ImportError:
        return {
            "name": "kafka",
            "status": "aiokafka_not_installed",
            "broker": settings.kafka_bootstrap_servers,
        }
    except Exception as exc:
        return {"name": "kafka", "status": "unhealthy", "error": str(exc)}


async def check_minio_health() -> Dict[str, Any]:
    """Check MinIO connectivity."""
    from app.config import settings

    endpoint = getattr(settings, "minio_endpoint", None)
    if not endpoint:
        return {"name": "minio", "status": "not_configured"}
    try:
        import httpx

        url = f"http{'s' if getattr(settings, 'minio_secure', False) else ''}://{endpoint}/minio/health/live"
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(url)
        return {
            "name": "minio",
            "status": "healthy" if resp.status_code == 200 else "degraded",
            "endpoint": endpoint,
        }
    except Exception as exc:
        return {"name": "minio", "status": "unhealthy", "error": str(exc)}
