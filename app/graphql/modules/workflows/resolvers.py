"""Workflow definitions & runs (DurgasOS desktop)."""

from __future__ import annotations

import uuid
from typing import Any, List, Optional, cast

import strawberry
from sqlalchemy import or_, select
from strawberry.scalars import JSON
from strawberry.types import Info

from app.database import AsyncSessionLocal
from app.graphql.modules.util import require_authenticated_sub, user_from_info
from app.models.durgasos_desktop import WorkflowDefinitionModel, WorkflowRunModel
from app.utils.helpers import utc_now


@strawberry.type
class WorkflowDefinition:
    id: strawberry.ID
    name: str
    owner_id: Optional[str]
    spec: JSON
    created_at: str
    updated_at: str


@strawberry.type
class WorkflowRun:
    id: strawberry.ID
    workflow_id: str
    owner_id: Optional[str]
    status: str
    created_at: str
    updated_at: str


def _wf_row(r: WorkflowDefinitionModel) -> WorkflowDefinition:
    spec_raw: Any = r.spec or {}
    spec_json = spec_raw if isinstance(spec_raw, (dict, list)) else {}
    return WorkflowDefinition(
        id=strawberry.ID(r.id),
        name=r.name,
        owner_id=r.owner_id,
        spec=cast(JSON, spec_json),
        created_at=r.created_at.isoformat() if r.created_at else "",
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


def _run_row(r: WorkflowRunModel) -> WorkflowRun:
    return WorkflowRun(
        id=strawberry.ID(r.id),
        workflow_id=r.workflow_id,
        owner_id=r.owner_id,
        status=r.status,
        created_at=r.created_at.isoformat() if r.created_at else "",
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


@strawberry.type
class WorkflowsQuery:
    @strawberry.field
    async def workflow_definitions(self, info: Info) -> List[WorkflowDefinition]:
        user = user_from_info(info)
        sub = user.get("sub") if user else None
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowDefinitionModel).order_by(
                WorkflowDefinitionModel.created_at.desc()
            )
            if sub:
                stmt = stmt.where(
                    or_(
                        WorkflowDefinitionModel.owner_id == sub,
                        WorkflowDefinitionModel.owner_id.is_(None),
                    )
                )
            else:
                stmt = stmt.where(WorkflowDefinitionModel.owner_id.is_(None))
            rows = (await db.execute(stmt)).scalars().all()
        return [_wf_row(r) for r in rows]

    @strawberry.field
    async def workflow_runs(
        self, info: Info, workflow_id: Optional[str] = None
    ) -> List[WorkflowRun]:
        owner = require_authenticated_sub(info)
        async with AsyncSessionLocal() as db:
            stmt = select(WorkflowRunModel).where(WorkflowRunModel.owner_id == owner)
            if workflow_id:
                stmt = stmt.where(WorkflowRunModel.workflow_id == workflow_id)
            stmt = stmt.order_by(WorkflowRunModel.created_at.desc()).limit(50)
            rows = (await db.execute(stmt)).scalars().all()
        return [_run_row(r) for r in rows]


@strawberry.type
class WorkflowsMutation:
    @strawberry.mutation
    async def create_workflow_definition(
        self, info: Info, name: str, spec: JSON
    ) -> WorkflowDefinition:
        owner = require_authenticated_sub(info)
        wid = str(uuid.uuid4())
        now = utc_now()
        spec_dict = dict(spec) if isinstance(spec, dict) else {}
        row = WorkflowDefinitionModel(
            id=wid,
            owner_id=owner,
            name=name.strip() or "Untitled",
            spec=spec_dict,
            created_at=now,
            updated_at=now,
        )
        async with AsyncSessionLocal() as db:
            db.add(row)
            await db.commit()
            await db.refresh(row)
        return _wf_row(row)

    @strawberry.mutation
    async def start_workflow_run(self, info: Info, workflow_id: str) -> WorkflowRun:
        owner = require_authenticated_sub(info)
        rid = str(uuid.uuid4())
        now = utc_now()
        row = WorkflowRunModel(
            id=rid,
            workflow_id=workflow_id.strip(),
            owner_id=owner,
            status="running",
            events=[],
            created_at=now,
            updated_at=now,
        )
        async with AsyncSessionLocal() as db:
            db.add(row)
            await db.commit()
            await db.refresh(row)
        return _run_row(row)
