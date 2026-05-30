"""Kafka async producer — publishes structured OS events to Apache Kafka."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_producer = None


async def _get_producer():
    """Lazy-initialize aiokafka producer on first use."""
    global _producer
    if _producer is not None:
        return _producer
    if not settings.kafka_bootstrap_servers:
        return None
    try:
        from aiokafka import AIOKafkaProducer  # type: ignore[import]
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            enable_idempotence=True,
            max_batch_size=16384,
            compression_type="gzip",
        )
        await _producer.start()
        logger.info("Kafka producer connected to %s", settings.kafka_bootstrap_servers)
    except ImportError:
        logger.warning("aiokafka not installed — Kafka producer is a no-op stub")
        _producer = None
    except Exception as exc:
        logger.warning("Kafka producer startup failed (%s) — falling back to stub", exc)
        _producer = None
    return _producer


async def publish_json(
    topic: str, payload: Dict[str, Any], key: Optional[str] = None
) -> None:
    """Publish a JSON payload to a Kafka topic. No-ops gracefully when Kafka is unavailable."""
    producer = await _get_producer()
    if producer is None:
        logger.debug(
            "kafka_stub topic=%s key=%s payload=%s",
            topic,
            key,
            json.dumps(payload, default=str)[:500],
        )
        return
    try:
        await producer.send_and_wait(topic, value=payload, key=key)
        logger.debug("kafka_sent topic=%s key=%s", topic, key)
        try:
            from app.core.metrics import KAFKA_PUBLISHED_EVENTS_TOTAL
            KAFKA_PUBLISHED_EVENTS_TOTAL.labels(topic=topic).inc()
        except Exception:
            pass
    except Exception as exc:
        logger.warning("kafka_send_failed topic=%s error=%s", topic, exc)


async def close_producer() -> None:
    """Gracefully stop the Kafka producer on app shutdown."""
    global _producer
    if _producer is not None:
        try:
            await _producer.stop()
            logger.info("Kafka producer stopped")
        except Exception as exc:
            logger.warning("Kafka producer stop error: %s", exc)
        finally:
            _producer = None
