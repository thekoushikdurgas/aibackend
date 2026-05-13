"""Optional Kafka producer stub — logs structured events; wire aiokafka later if needed."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def publish_json(topic: str, payload: Dict[str, Any], key: Optional[str] = None) -> None:
    """Publish JSON to Kafka when a client is configured; otherwise DEBUG log (stub)."""
    logger.debug(
        "kafka stub topic=%s key=%s payload=%s",
        topic,
        key,
        json.dumps(payload, default=str)[:4000],
    )
