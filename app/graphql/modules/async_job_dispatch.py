"""Fire-and-forget WS-backed work with job_status polling."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Coroutine, cast

from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.jobs import job_create, job_update
from app.graphql.modules.util import run_ws

logger = logging.getLogger(__name__)


async def _run_ws_job(
    job_id: str,
    handler: Callable[..., Coroutine[Any, Any, Any]],
    params: dict[str, Any],
    info: Info,
) -> None:
    job_update(job_id, "running")
    try:
        result = await run_ws(handler, params, info)
        job_update(job_id, "done", result=result)
    except Exception as e:
        logger.exception("async job %s failed", job_id)
        job_update(job_id, "error", error=str(e))


def start_ws_job(
    info: Info,
    handler: Callable[..., Coroutine[Any, Any, Any]],
    params: dict[str, Any],
) -> JSON:
    jid = job_create()
    asyncio.create_task(_run_ws_job(jid, handler, params, info))
    return cast(JSON, {"async": True, "job_id": jid, "status": "pending"})
