"""JSON-RPC streaming: workflow.run and system.feed."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncGenerator, Dict, Optional
from uuid import uuid4

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.kafka import publish_json
from app.services.kafka.topics import (
    SYSTEM_FEED,
    WORKFLOW_RUN_EVENT,
    WORKFLOW_RUN_REQUESTED,
)

logger = logging.getLogger(__name__)


async def handle_workflow_run(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    p = params or {}
    workflow_id = str(p.get("workflow_id") or p.get("id") or "").strip()
    if not workflow_id:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing workflow_id")

    owner = None
    if user and user.get("sub"):
        owner = str(user["sub"])
    run_id = str(uuid4())

    await publish_json(
        WORKFLOW_RUN_REQUESTED,
        {
            "run_id": run_id,
            "workflow_id": workflow_id,
            "owner_id": owner,
            "connection_id": connection_id,
        },
        key=run_id,
    )
    yield {"type": "started", "run_id": run_id, "workflow_id": workflow_id}

    try:
        for step in range(5):
            await asyncio.sleep(0.12)
            evt: Dict[str, Any] = {
                "type": "event",
                "run_id": run_id,
                "step": step,
                "message": f"Step {step + 1}/5",
            }
            await publish_json(WORKFLOW_RUN_EVENT, evt, key=run_id)
            yield evt
        yield {"type": "done", "run_id": run_id, "workflow_id": workflow_id}
    except asyncio.CancelledError:
        logger.info("workflow.run cancelled run_id=%s", run_id)
        raise


async def handle_system_feed(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    p = params or {}
    topic = str(p.get("topic") or "default")
    owner = user.get("sub") if user else None

    for i in range(6):
        await asyncio.sleep(0.1)
        line: Dict[str, Any] = {
            "type": "event",
            "topic": topic,
            "seq": i,
            "message": f"[{topic}] tick {i + 1}",
        }
        await publish_json(
            SYSTEM_FEED,
            {"connection_id": connection_id, "owner_id": owner, **line},
            key=connection_id or "anon",
        )
        yield line

    yield {"type": "done", "topic": topic}


def get_methods() -> Dict[str, Any]:
    return {
        "workflow.run": handle_workflow_run,
        "system.feed": handle_system_feed,
    }
