"""Kafka async consumer — background task processing OS events."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class KafkaConsumerGroup:
    """Manages an async Kafka consumer subscribed to multiple topics."""

    def __init__(
        self,
        topics: List[str],
        group_id: str,
        handler: Callable,
    ) -> None:
        self.topics = topics
        self.group_id = group_id
        self.handler = handler
        self._consumer = None
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the consumer background task."""
        if not settings.kafka_bootstrap_servers:
            logger.info("Kafka not configured — consumer '%s' is a no-op", self.group_id)
            return
        try:
            from aiokafka import AIOKafkaConsumer  # type: ignore[import]
            self._consumer = AIOKafkaConsumer(
                *self.topics,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset="latest",
                enable_auto_commit=True,
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
            )
            await self._consumer.start()
            self._running = True
            self._task = asyncio.create_task(self._consume_loop())
            logger.info(
                "Kafka consumer '%s' started — topics: %s",
                self.group_id,
                self.topics,
            )
        except ImportError:
            logger.warning("aiokafka not installed — consumer '%s' is a no-op", self.group_id)
        except Exception as exc:
            logger.warning("Kafka consumer '%s' startup failed: %s", self.group_id, exc)

    async def _consume_loop(self) -> None:
        """Main message processing loop."""
        while self._running:
            try:
                async for msg in self._consumer:
                    try:
                        await self.handler(
                            topic=msg.topic,
                            partition=msg.partition,
                            offset=msg.offset,
                            key=msg.key,
                            payload=msg.value,
                        )
                        try:
                            from app.core.metrics import KAFKA_CONSUMED_EVENTS_TOTAL
                            KAFKA_CONSUMED_EVENTS_TOTAL.labels(topic=msg.topic, group_id=self.group_id).inc()
                        except Exception:
                            pass
                    except Exception as exc:
                        logger.error(
                            "Kafka handler error topic=%s offset=%s: %s",
                            msg.topic,
                            msg.offset,
                            exc,
                        )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Kafka consumer loop error: %s — retrying in 5s", exc)
                await asyncio.sleep(5)

    async def stop(self) -> None:
        """Stop the consumer and background task."""
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._consumer is not None:
            try:
                await self._consumer.stop()
            except Exception as exc:
                logger.warning("Kafka consumer stop error: %s", exc)
        logger.info("Kafka consumer '%s' stopped", self.group_id)
