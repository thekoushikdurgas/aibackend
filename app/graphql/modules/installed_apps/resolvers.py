"""Persisted list of installed DurgasOS application ids per authenticated user."""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, cast

import strawberry
from sqlalchemy import select
from strawberry.scalars import JSON
from strawberry.types import Info

from app.core.response_cache import cache_invalidate_prefix, cached_json_response
from app.database import AsyncSessionLocal
from app.graphql.context import GraphQLContext
from app.graphql.modules.util import require_authenticated_sub, user_from_info
from app.models.durgasos_desktop import DurgasOSInstalledAppsModel
from app.utils.helpers import utc_now

_MANDATORY_APP_IDS = frozenset({"explorer", "settings", "apps-manager"})

_KNOWN_APP_IDS = frozenset(
    {
        "explorer",
        "settings",
        "terminal",
        "browser",
        "gallery",
        "chat",
        "rag",
        "storage",
        "metrics",
        "vision",
        "multimodal",
        "council",
        "apps-manager",
        "volumes",
        "archiver",
        "player",
        "remote",
        "docs",
        "sheets",
        "transfer",
        "workflow",
        "vectordb",
        "resume",
        "void-ide",
        "viewer",
        "sudoku",
    }
)

_EXT_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9+]{0,15}$")


def _merge_with_mandatory(app_ids: List[str]) -> List[str]:
    merged = set(app_ids) | set(_MANDATORY_APP_IDS)
    return sorted(merged)


def _coerce_file_associations(raw: Any) -> Dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in raw.items():
        ek = str(k).lower().strip().lstrip(".")
        if not ek or not _EXT_KEY_RE.match(ek):
            continue
        app = str(v).strip()
        if app in _KNOWN_APP_IDS:
            out[ek] = app
    return out


def _normalize_incoming_associations(payload: Any) -> Dict[str, str]:
    return _coerce_file_associations(payload)


@strawberry.type
class InstalledApps:
    id: strawberry.ID
    owner_id: str
    app_ids: List[str]
    file_associations: JSON
    updated_at: str


def _installed_to_dict(i: Optional[InstalledApps]) -> Any:
    if i is None:
        return None
    return {
        "id": str(i.id),
        "owner_id": i.owner_id,
        "app_ids": list(i.app_ids),
        "file_associations": i.file_associations,
        "updated_at": i.updated_at,
    }


def _installed_from_dict(raw: Any) -> Optional[InstalledApps]:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    raw_ids = raw.get("app_ids")
    ids: List[str] = [str(x) for x in raw_ids] if isinstance(raw_ids, list) else []
    return InstalledApps(
        id=strawberry.ID(str(raw.get("id", ""))),
        owner_id=str(raw.get("owner_id", "")),
        app_ids=ids,
        file_associations=cast(JSON, raw.get("file_associations") or {}),
        updated_at=str(raw.get("updated_at", "")),
    )


async def _load_installed_apps(owner: str) -> Optional[InstalledApps]:
    async with AsyncSessionLocal() as db:
        stmt = select(DurgasOSInstalledAppsModel).where(
            DurgasOSInstalledAppsModel.owner_id == owner
        )
        r = (await db.execute(stmt)).scalar_one_or_none()
    if not r:
        return None
    raw_ids = r.app_ids
    ids: List[str]
    if isinstance(raw_ids, list):
        ids = [str(x) for x in raw_ids]
    else:
        ids = []
    assoc = _coerce_file_associations(getattr(r, "file_associations", None))
    return InstalledApps(
        id=strawberry.ID(str(r.id)),
        owner_id=str(r.owner_id),
        app_ids=ids,
        file_associations=cast(JSON, assoc),
        updated_at=r.updated_at.isoformat() if r.updated_at else "",
    )


@strawberry.type
class InstalledAppsQuery:
    @strawberry.field
    async def installed_apps(self, info: Info) -> Optional[InstalledApps]:
        user = user_from_info(info)
        if not user or not user.get("sub"):
            return None
        owner = str(user["sub"])
        ctx = info.context
        req = ctx.request if isinstance(ctx, GraphQLContext) else None
        if req is None:
            return await _load_installed_apps(owner)
        key = f"gql:installed_apps:v1:{owner}"

        async def _factory() -> Any:
            return _installed_to_dict(await _load_installed_apps(owner))

        blob = await cached_json_response(req, key, 60.0, _factory)
        return _installed_from_dict(blob)


@strawberry.type
class InstalledAppsMutation:
    @strawberry.mutation
    async def save_installed_apps(
        self, info: Info, app_ids: List[str]
    ) -> InstalledApps:
        owner = require_authenticated_sub(info)
        payload: Any = _merge_with_mandatory(app_ids)
        now = utc_now()
        async with AsyncSessionLocal() as db:
            stmt = select(DurgasOSInstalledAppsModel).where(
                DurgasOSInstalledAppsModel.owner_id == owner
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                setattr(existing, "app_ids", payload)
                setattr(existing, "updated_at", now)
                await db.commit()
                await db.refresh(existing)
                row = existing
            else:
                row = DurgasOSInstalledAppsModel(
                    id=str(uuid.uuid4()),
                    owner_id=owner,
                    app_ids=payload,
                    file_associations={},
                    updated_at=now,
                )
                db.add(row)
                await db.commit()
                await db.refresh(row)
        out_ids = cast(List[str], row.app_ids if isinstance(row.app_ids, list) else [])
        assoc = _coerce_file_associations(getattr(row, "file_associations", None))
        ctx = info.context
        if isinstance(ctx, GraphQLContext):
            await cache_invalidate_prefix(ctx.request, f"gql:installed_apps:v1:{owner}")
        return InstalledApps(
            id=strawberry.ID(str(row.id)),
            owner_id=str(row.owner_id),
            app_ids=out_ids,
            file_associations=cast(JSON, assoc),
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
        )

    @strawberry.mutation
    async def save_file_associations(
        self, info: Info, associations: JSON
    ) -> InstalledApps:
        owner = require_authenticated_sub(info)
        normalized = _normalize_incoming_associations(associations)
        now = utc_now()
        async with AsyncSessionLocal() as db:
            stmt = select(DurgasOSInstalledAppsModel).where(
                DurgasOSInstalledAppsModel.owner_id == owner
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                setattr(existing, "file_associations", normalized)
                setattr(existing, "updated_at", now)
                await db.commit()
                await db.refresh(existing)
                row = existing
            else:
                merged_ids = _merge_with_mandatory([])
                row = DurgasOSInstalledAppsModel(
                    id=str(uuid.uuid4()),
                    owner_id=owner,
                    app_ids=merged_ids,
                    file_associations=normalized,
                    updated_at=now,
                )
                db.add(row)
                await db.commit()
                await db.refresh(row)
        out_ids = cast(List[str], row.app_ids if isinstance(row.app_ids, list) else [])
        assoc = _coerce_file_associations(getattr(row, "file_associations", None))
        ctx = info.context
        if isinstance(ctx, GraphQLContext):
            await cache_invalidate_prefix(ctx.request, f"gql:installed_apps:v1:{owner}")
        return InstalledApps(
            id=strawberry.ID(str(row.id)),
            owner_id=str(row.owner_id),
            app_ids=out_ids,
            file_associations=cast(JSON, assoc),
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
        )
