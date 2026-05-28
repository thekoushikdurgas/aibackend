"""Persist and manage linked Google accounts per authenticated OS user."""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional, cast

import strawberry
from graphql import GraphQLError
from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from strawberry.scalars import JSON
from strawberry.types import Info

from app.database import AsyncSessionLocal
from app.graphql.modules.util import require_authenticated_sub, user_from_info
from app.models.durgasos_desktop import LinkedGoogleAccountModel
from app.utils.helpers import utc_now


def _row_to_public_dict(row: LinkedGoogleAccountModel) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "googleUserId": str(row.google_user_id),
        "email": row.email or "",
        "displayName": row.display_name,
        "photoUrl": row.photo_url,
        "tokenExpiresAt": row.token_expires_at,
        "scopesGranted": row.scopes_granted,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
    }


def _normalize_params(params: Any) -> Dict[str, Any]:
    if not isinstance(params, dict):
        return {}
    return cast(Dict[str, Any], params)


def _str_field(p: Dict[str, Any], *keys: str) -> Optional[str]:
    for k in keys:
        v = p.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def _float_field(p: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = p.get(k)
        if v is None:
            continue
        try:
            return float(v)
        except (TypeError, ValueError):
            continue
    return None


def _scopes_granted_from_params(p: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """Whether the client sent scopes fields, and normalized value (None = clear)."""
    for k in ("scopes_granted", "scopesGranted"):
        if k in p:
            v = p.get(k)
            if v is None:
                return True, None
            s = str(v).strip()
            return True, s or None
    return False, None


async def _verify_google_token(access_token: str) -> None:
    """Verify that the Google access token is valid."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": access_token.strip()},
            )
            if res.status_code != 200:
                raise GraphQLError(
                    f"Google access token verification failed: {res.text}",
                    extensions={"code": "INVALID_TOKEN"},
                )
    except httpx.RequestError as e:
        import logging

        logging.getLogger(__name__).warning(
            "Could not reach Google tokeninfo endpoint: %s", e
        )


@strawberry.type
class LinkedAccountsQuery:
    @strawberry.field
    async def linked_google_accounts(self, info: Info) -> JSON:
        user = user_from_info(info)
        if not user or not user.get("sub"):
            return cast(JSON, [])
        owner = str(user["sub"])
        async with AsyncSessionLocal() as db:
            stmt = (
                select(LinkedGoogleAccountModel)
                .where(LinkedGoogleAccountModel.owner_id == owner)
                .order_by(LinkedGoogleAccountModel.created_at.asc())
            )
            rows = list((await db.execute(stmt)).scalars().all())
        return cast(JSON, [_row_to_public_dict(r) for r in rows])

    @strawberry.field
    async def get_linked_google_account_token(
        self, info: Info, google_user_id: str
    ) -> JSON:
        owner = require_authenticated_sub(info)
        uid = google_user_id.strip()
        if not uid:
            raise GraphQLError(
                "googleUserId is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        async with AsyncSessionLocal() as db:
            stmt = select(LinkedGoogleAccountModel).where(
                LinkedGoogleAccountModel.owner_id == owner,
                LinkedGoogleAccountModel.google_user_id == uid,
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
        if not row:
            raise GraphQLError(
                "Linked Google account not found",
                extensions={"code": "NOT_FOUND"},
            )
        return cast(
            JSON,
            {
                "accessToken": row.access_token,
                "tokenExpiresAt": row.token_expires_at,
                "googleUserId": row.google_user_id,
            },
        )


@strawberry.type
class LinkedAccountsMutation:
    @strawberry.mutation
    async def add_linked_google_account(self, info: Info, params: JSON) -> JSON:
        owner = require_authenticated_sub(info)
        p = _normalize_params(params)
        access_token = _str_field(p, "access_token", "accessToken")
        google_uid = _str_field(p, "google_user_id", "googleUserId")
        email = _str_field(p, "email") or ""
        display_name = _str_field(p, "display_name", "displayName")
        photo_url = _str_field(p, "photo_url", "photoUrl")
        token_expires_at = _float_field(p, "token_expires_at", "tokenExpiresAt")
        scopes_provided, scopes_val = _scopes_granted_from_params(p)

        if not access_token:
            raise GraphQLError(
                "access_token is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        if not google_uid:
            raise GraphQLError(
                "google_user_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )

        # Verify Google OAuth access token
        await _verify_google_token(access_token)

        now = utc_now()
        row: LinkedGoogleAccountModel | None = None
        async with AsyncSessionLocal() as db:
            stmt = select(LinkedGoogleAccountModel).where(
                LinkedGoogleAccountModel.owner_id == owner,
                LinkedGoogleAccountModel.google_user_id == google_uid,
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            row_any = cast(Any, row)
            if row:
                row_any.access_token = access_token
                row_any.email = email or None
                row_any.display_name = display_name
                row_any.photo_url = photo_url
                row_any.token_expires_at = token_expires_at
                row_any.updated_at = now
            else:
                row = LinkedGoogleAccountModel(
                    id=str(uuid.uuid4()),
                    owner_id=owner,
                    google_user_id=google_uid,
                    email=email or None,
                    display_name=display_name,
                    photo_url=photo_url,
                    access_token=access_token,
                    token_expires_at=token_expires_at,
                    created_at=now,
                    updated_at=now,
                )
                db.add(row)
            await db.commit()
            if row is not None:
                await db.refresh(row)

        if row is None:
            raise GraphQLError(
                "Failed to persist linked Google account",
                extensions={"code": "INTERNAL_ERROR"},
            )

        out = _row_to_public_dict(row)
        out["accessToken"] = access_token
        return cast(JSON, out)

    @strawberry.mutation
    async def remove_linked_google_account(
        self, info: Info, google_user_id: str
    ) -> JSON:
        owner = require_authenticated_sub(info)
        uid = google_user_id.strip()
        if not uid:
            raise GraphQLError(
                "googleUserId is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        async with AsyncSessionLocal() as db:
            stmt = delete(LinkedGoogleAccountModel).where(
                LinkedGoogleAccountModel.owner_id == owner,
                LinkedGoogleAccountModel.google_user_id == uid,
            )
            result = await db.execute(stmt)
            await db.commit()
        assert isinstance(result, CursorResult)
        rc = result.rowcount
        deleted = rc is not None and rc > 0
        return cast(JSON, {"success": True, "deleted": deleted})

    @strawberry.mutation
    async def refresh_linked_google_account_token(
        self,
        info: Info,
        google_user_id: str,
        access_token: str,
        expires_at: float,
        scopes_granted: str | None = None,
    ) -> JSON:
        owner = require_authenticated_sub(info)
        uid = google_user_id.strip()
        token = access_token.strip()
        if not uid or not token:
            raise GraphQLError(
                "googleUserId and accessToken are required",
                extensions={"code": "BAD_USER_INPUT"},
            )

        # Verify Google OAuth access token
        await _verify_google_token(token)

        now = utc_now()
        async with AsyncSessionLocal() as db:
            stmt = select(LinkedGoogleAccountModel).where(
                LinkedGoogleAccountModel.owner_id == owner,
                LinkedGoogleAccountModel.google_user_id == uid,
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if not row:
                raise GraphQLError(
                    "Linked Google account not found",
                    extensions={"code": "NOT_FOUND"},
                )
            row_any = cast(Any, row)
            row_any.access_token = token
            row_any.token_expires_at = expires_at
            if scopes_granted is not None:
                s = scopes_granted.strip()
                row_any.scopes_granted = s or None
            row_any.updated_at = now
            await db.commit()
            await db.refresh(row)
        return cast(JSON, _row_to_public_dict(row))
