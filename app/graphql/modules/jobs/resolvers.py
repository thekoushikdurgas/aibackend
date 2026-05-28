"""Async job status query (GraphQL)."""

from __future__ import annotations

from typing import Optional

import strawberry
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.jobs import job_cleanup, job_get


@strawberry.type(name="AsyncJobStatus")
class AsyncJobStatus:
    job_id: str
    status: str
    result: JSON | None
    error: str | None
    updated_at: float


@strawberry.type
class JobsQuery:
    @strawberry.field
    async def job_status(self, info: Info, job_id: str) -> Optional[AsyncJobStatus]:
        job_cleanup()
        row = job_get(job_id.strip())
        if not row:
            return None
        return AsyncJobStatus(
            job_id=job_id.strip(),
            status=str(row.get("status", "pending")),
            result=row.get("result"),
            error=row.get("error"),
            updated_at=float(row.get("updated_at", 0)),
        )
