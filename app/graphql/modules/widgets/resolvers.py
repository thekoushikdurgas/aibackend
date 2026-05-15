"""Persisted widget layout (DurgasOS desktop)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import strawberry
from sqlalchemy import select
from strawberry.scalars import JSON
from strawberry.types import Info

from app.database import AsyncSessionLocal
from app.graphql.modules.util import require_authenticated_sub, user_from_info
from app.models.durgasos_desktop import WidgetLayoutModel


@strawberry.type
class WidgetLayout:
    id: strawberry.ID
    owner_id: str
    layout_json: JSON
    updated_at: str


@strawberry.type
class WidgetsQuery:
    @strawberry.field
    async def widget_layout(self, info: Info) -> Optional[WidgetLayout]:
        user = user_from_info(info)
        if not user or not user.get("sub"):
            return None
        owner = str(user["sub"])
        async with AsyncSessionLocal() as db:
            stmt = select(WidgetLayoutModel).where(WidgetLayoutModel.owner_id == owner)
            r = (await db.execute(stmt)).scalar_one_or_none()
        if not r:
            return None
        return WidgetLayout(
            id=strawberry.ID(r.id),
            owner_id=r.owner_id,
            layout_json=(
                r.layout_json if isinstance(r.layout_json, (list, dict)) else []
            ),
            updated_at=r.updated_at.isoformat() if r.updated_at else "",
        )


@strawberry.type
class WidgetsMutation:
    @strawberry.mutation
    async def save_widget_layout(self, info: Info, layout_json: JSON) -> WidgetLayout:
        owner = require_authenticated_sub(info)
        payload: JSON = layout_json if isinstance(layout_json, (list, dict)) else []
        now = datetime.utcnow()
        async with AsyncSessionLocal() as db:
            stmt = select(WidgetLayoutModel).where(WidgetLayoutModel.owner_id == owner)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                existing.layout_json = payload
                existing.updated_at = now
                await db.commit()
                await db.refresh(existing)
                row = existing
            else:
                row = WidgetLayoutModel(
                    id=str(uuid.uuid4()),
                    owner_id=owner,
                    layout_json=payload,
                    updated_at=now,
                )
                db.add(row)
                await db.commit()
                await db.refresh(row)
        return WidgetLayout(
            id=strawberry.ID(row.id),
            owner_id=row.owner_id,
            layout_json=row.layout_json,
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
        )
