"""GitHub REST API proxy + linked GitHub account persistence."""

from __future__ import annotations

import base64
import uuid
from typing import Any, Dict, Optional, cast
from urllib.parse import quote

import httpx
import strawberry
from graphql import GraphQLError
from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from strawberry.scalars import JSON
from strawberry.types import Info

from app.database import AsyncSessionLocal
from app.graphql.modules.util import require_authenticated_sub, user_from_info
from app.models.durgasos_desktop import LinkedGithubAccountModel
from app.utils.helpers import utc_now

GITHUB_API = "https://api.github.com"
GITHUB_HEADERS_BASE: Dict[str, str] = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "DurgasAI-DurgasOS/1.0",
}


def _row_to_public_dict(row: LinkedGithubAccountModel) -> Dict[str, Any]:
    return {
        "id": str(row.id),
        "githubUserId": str(row.github_user_id),
        "login": row.login or "",
        "email": row.email or "",
        "displayName": row.display_name,
        "photoUrl": row.photo_url,
        "tokenExpiresAt": row.token_expires_at,
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


def _sanitize_username(username: str) -> str:
    u = username.strip()
    if not u or len(u) > 39:
        raise GraphQLError(
            "Invalid GitHub username",
            extensions={"code": "BAD_USER_INPUT"},
        )
    if any(c in u for c in ("/", "\\", "..", "?", "#", "@", " ")):
        raise GraphQLError(
            "Invalid GitHub username",
            extensions={"code": "BAD_USER_INPUT"},
        )
    return u


def _sanitize_sort(sort: Optional[str]) -> str:
    allowed = {"created", "updated", "pushed", "full_name"}
    s = (sort or "updated").strip().lower()
    if s not in allowed:
        return "updated"
    return s


async def _token_for_github_user(
    info: Info, github_user_id: Optional[str]
) -> Optional[str]:
    if github_user_id is None:
        return None
    uid = github_user_id.strip()
    if not uid:
        return None
    user = user_from_info(info)
    if not user or not user.get("sub"):
        return None
    owner = str(user["sub"])
    async with AsyncSessionLocal() as db:
        stmt = select(LinkedGithubAccountModel).where(
            LinkedGithubAccountModel.owner_id == owner,
            LinkedGithubAccountModel.github_user_id == uid,
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
    if not row:
        return None
    return str(row.access_token)


async def _github_get_json(url: str, token: Optional[str]) -> Any:
    headers = {**GITHUB_HEADERS_BASE}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, headers=headers)
    if r.status_code >= 400:
        try:
            err_body = r.json()
        except Exception:
            err_body = {"message": (r.text or "")[:500]}
        raise GraphQLError(
            err_body.get("message", f"GitHub API error ({r.status_code})"),
            extensions={"code": "GITHUB_API", "status": r.status_code},
        )
    return r.json()


@strawberry.type
class GithubQuery:
    @strawberry.field
    async def linked_github_accounts(self, info: Info) -> JSON:
        user = user_from_info(info)
        if not user or not user.get("sub"):
            return cast(JSON, [])
        owner = str(user["sub"])
        async with AsyncSessionLocal() as db:
            stmt = (
                select(LinkedGithubAccountModel)
                .where(LinkedGithubAccountModel.owner_id == owner)
                .order_by(LinkedGithubAccountModel.created_at.asc())
            )
            rows = list((await db.execute(stmt)).scalars().all())
        return cast(JSON, [_row_to_public_dict(r) for r in rows])

    @strawberry.field
    async def github_user(
        self,
        info: Info,
        username: str,
        github_user_id: Optional[str] = None,
    ) -> JSON:
        login = _sanitize_username(username)
        token = await _token_for_github_user(info, github_user_id)
        safe = quote(login, safe="")
        url = f"{GITHUB_API}/users/{safe}"
        data = await _github_get_json(url, token)
        return cast(JSON, data)

    @strawberry.field
    async def github_repos(
        self,
        info: Info,
        username: str,
        sort: Optional[str] = None,
        github_user_id: Optional[str] = None,
    ) -> JSON:
        login = _sanitize_username(username)
        token = await _token_for_github_user(info, github_user_id)
        sort_val = _sanitize_sort(sort)
        safe = quote(login, safe="")
        url = (
            f"{GITHUB_API}/users/{safe}/repos"
            f"?sort={sort_val}&per_page=100&type=owner"
        )
        data = await _github_get_json(url, token)
        return cast(JSON, data)

    @strawberry.field
    async def github_starred(
        self,
        info: Info,
        username: str,
        github_user_id: Optional[str] = None,
    ) -> JSON:
        login = _sanitize_username(username)
        token = await _token_for_github_user(info, github_user_id)
        safe = quote(login, safe="")
        url = f"{GITHUB_API}/users/{safe}/starred?per_page=100"
        data = await _github_get_json(url, token)
        return cast(JSON, data)

    @strawberry.field
    async def github_readme(
        self,
        info: Info,
        username: str,
        github_user_id: Optional[str] = None,
    ) -> JSON:
        login = _sanitize_username(username)
        token = await _token_for_github_user(info, github_user_id)
        owner = quote(login, safe="")
        repo = owner  # profile README: owner/owner
        url = f"{GITHUB_API}/repos/{owner}/{repo}/readme"
        headers = {**GITHUB_HEADERS_BASE}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(url, headers=headers)
        if r.status_code == 404:
            return cast(JSON, {"found": False, "text": None})
        if r.status_code >= 400:
            try:
                err_body = r.json()
            except Exception:
                err_body = {"message": (r.text or "")[:500]}
            raise GraphQLError(
                err_body.get("message", f"GitHub API error ({r.status_code})"),
                extensions={"code": "GITHUB_API", "status": r.status_code},
            )
        body = r.json()
        enc = body.get("encoding")
        content_b64 = body.get("content")
        if enc == "base64" and isinstance(content_b64, str):
            try:
                text = base64.b64decode(content_b64.replace("\n", "")).decode(
                    "utf-8", errors="replace"
                )
            except Exception:
                text = None
        else:
            text = None
        return cast(
            JSON,
            {
                "found": True,
                "name": body.get("name"),
                "path": body.get("path"),
                "text": text,
                "htmlUrl": body.get("html_url"),
            },
        )


@strawberry.type
class GithubMutation:
    @strawberry.mutation
    async def add_linked_github_account(self, info: Info, params: JSON) -> JSON:
        owner = require_authenticated_sub(info)
        p = _normalize_params(params)
        access_token = _str_field(p, "access_token", "accessToken")
        github_uid = _str_field(p, "github_user_id", "githubUserId")
        login = _str_field(p, "login")
        email = _str_field(p, "email") or ""
        display_name = _str_field(p, "display_name", "displayName")
        photo_url = _str_field(p, "photo_url", "photoUrl")
        token_expires_at = _float_field(p, "token_expires_at", "tokenExpiresAt")

        if not access_token:
            raise GraphQLError(
                "access_token is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        if not github_uid:
            raise GraphQLError(
                "github_user_id is required",
                extensions={"code": "BAD_USER_INPUT"},
            )

        now = utc_now()
        row: LinkedGithubAccountModel | None = None
        async with AsyncSessionLocal() as db:
            stmt = select(LinkedGithubAccountModel).where(
                LinkedGithubAccountModel.owner_id == owner,
                LinkedGithubAccountModel.github_user_id == github_uid,
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            row_any = cast(Any, row)
            if row:
                row_any.access_token = access_token
                row_any.login = login
                row_any.email = email or None
                row_any.display_name = display_name
                row_any.photo_url = photo_url
                row_any.token_expires_at = token_expires_at
                row_any.updated_at = now
            else:
                row = LinkedGithubAccountModel(
                    id=str(uuid.uuid4()),
                    owner_id=owner,
                    github_user_id=github_uid,
                    login=login,
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
                "Failed to persist linked GitHub account",
                extensions={"code": "INTERNAL_ERROR"},
            )

        return cast(JSON, _row_to_public_dict(row))

    @strawberry.mutation
    async def remove_linked_github_account(
        self, info: Info, github_user_id: str
    ) -> JSON:
        owner = require_authenticated_sub(info)
        uid = github_user_id.strip()
        if not uid:
            raise GraphQLError(
                "githubUserId is required",
                extensions={"code": "BAD_USER_INPUT"},
            )
        async with AsyncSessionLocal() as db:
            stmt = delete(LinkedGithubAccountModel).where(
                LinkedGithubAccountModel.owner_id == owner,
                LinkedGithubAccountModel.github_user_id == uid,
            )
            result = await db.execute(stmt)
            await db.commit()
        assert isinstance(result, CursorResult)
        rc = result.rowcount
        deleted = rc is not None and rc > 0
        return cast(JSON, {"success": True, "deleted": deleted})
