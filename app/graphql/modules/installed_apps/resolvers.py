"""Persisted list of installed DurgasOS application ids per authenticated user."""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, cast

import strawberry
from sqlalchemy import select
from strawberry.scalars import JSON
from strawberry.types import Info

from app.database import AsyncSessionLocal
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


@strawberry.type
class InstalledAppsQuery:
    @strawberry.field
    async def installed_apps(self, info: Info) -> Optional[InstalledApps]:
        user = user_from_info(info)
        if not user or not user.get("sub"):
            return None
        owner = str(user["sub"])
        async with AsyncSessionLocal() as db:
            stmt = select(DurgasOSInstalledAppsModel).where(
                DurgasOSInstalledAppsModel.owner_id == owner
            )
            r = (await db.execute(stmt)).scalar_one_or_none()
        if not r:
            return None
        raw = r.app_ids
        ids: List[str]
        if isinstance(raw, list):
            ids = [str(x) for x in raw]
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
        return InstalledApps(
            id=strawberry.ID(str(row.id)),
            owner_id=str(row.owner_id),
            app_ids=out_ids,
            file_associations=cast(JSON, assoc),
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
        )
