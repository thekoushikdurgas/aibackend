"""Persisted widget layout (DurgasOS desktop)."""

from __future__ import annotations

import uuid
from typing import Any, Optional, cast

import strawberry
from sqlalchemy import select
from strawberry.scalars import JSON
from strawberry.types import Info

from app.core.response_cache import cache_invalidate_prefix, cached_json_response
from app.database import AsyncSessionLocal
from app.graphql.context import GraphQLContext
from app.graphql.modules.util import require_authenticated_sub, user_from_info
from app.models.durgasos_desktop import WidgetLayoutModel
from app.utils.helpers import utc_now


@strawberry.type
class WidgetLayout:
    id: strawberry.ID
    owner_id: str
    layout_json: JSON
    updated_at: str


def _widget_to_dict(w: Optional[WidgetLayout]) -> Any:
    if w is None:
        return None
    return {
        "id": str(w.id),
        "owner_id": w.owner_id,
        "layout_json": w.layout_json,
        "updated_at": w.updated_at,
    }


def _clamp01(value: Any) -> float:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, n))


def _normalize_layout_json(payload: Any) -> Any:
    """Clamp widget x/y to 0–1 when saving desktop layout."""
    if not isinstance(payload, list):
        return payload
    out: list[Any] = []
    for item in payload:
        if not isinstance(item, dict):
            out.append(item)
            continue
        row = dict(item)
        pos = row.get("position")
        if isinstance(pos, dict):
            row["position"] = {
                "x": _clamp01(pos.get("x")),
                "y": _clamp01(pos.get("y")),
            }
        out.append(row)
    return out


def _widget_from_dict(raw: Any) -> Optional[WidgetLayout]:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    layout_data = raw.get("layout_json")
    if not isinstance(layout_data, (list, dict)):
        layout_data = []
    return WidgetLayout(
        id=strawberry.ID(str(raw.get("id", ""))),
        owner_id=str(raw.get("owner_id", "")),
        layout_json=cast(JSON, layout_data),
        updated_at=str(raw.get("updated_at", "")),
    )


async def _load_widget_layout(owner: str) -> Optional[WidgetLayout]:
    async with AsyncSessionLocal() as db:
        stmt = select(WidgetLayoutModel).where(WidgetLayoutModel.owner_id == owner)
        r = (await db.execute(stmt)).scalar_one_or_none()
    if not r:
        return None
    layout_data: Any = r.layout_json if isinstance(r.layout_json, (list, dict)) else []
    return WidgetLayout(
        id=strawberry.ID(str(r.id)),
        owner_id=str(r.owner_id),
        layout_json=cast(JSON, layout_data),
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


@strawberry.type
class WidgetsQuery:
    @strawberry.field
    async def widget_layout(self, info: Info) -> Optional[WidgetLayout]:
        user = user_from_info(info)
        if not user or not user.get("sub"):
            return None
        owner = str(user["sub"])
        ctx = info.context
        req = ctx.request if isinstance(ctx, GraphQLContext) else None
        if req is None:
            return await _load_widget_layout(owner)
        key = f"gql:widget_layout:v1:{owner}"

        async def _factory() -> Any:
            return _widget_to_dict(await _load_widget_layout(owner))

        blob = await cached_json_response(req, key, 45.0, _factory)
        return _widget_from_dict(blob)


@strawberry.type
class WidgetsMutation:
    @strawberry.mutation
    async def save_widget_layout(self, info: Info, layout_json: JSON) -> WidgetLayout:
        owner = require_authenticated_sub(info)
        raw_payload: Any = layout_json if isinstance(layout_json, (list, dict)) else []
        payload = cast(JSON, _normalize_layout_json(raw_payload))
        now = utc_now()
        async with AsyncSessionLocal() as db:
            stmt = select(WidgetLayoutModel).where(WidgetLayoutModel.owner_id == owner)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                setattr(existing, "layout_json", payload)
                setattr(existing, "updated_at", now)
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
        ctx = info.context
        if isinstance(ctx, GraphQLContext):
            await cache_invalidate_prefix(ctx.request, f"gql:widget_layout:v1:{owner}")
        return WidgetLayout(
            id=strawberry.ID(str(row.id)),
            owner_id=str(row.owner_id),
            layout_json=cast(JSON, row.layout_json),
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
        )
