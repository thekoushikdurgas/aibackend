"""Auth queries and mutations."""

from __future__ import annotations

from typing import Any, Optional, cast

import strawberry
from graphql import GraphQLError
from strawberry.scalars import JSON
from strawberry.types import Info

from app.api.ws_methods import auth as auth_handlers
from app.core.auth import user_claims_from_access_token
from app.core.jsonrpc import JSONRPCError
from app.database.repositories.user_repo import UserRepository
from app.database.sqlalchemy import AsyncSessionLocal
from app.core.response_cache import cached_json_response
from app.graphql.context import GraphQLContext
from app.core.graphql_cookie_middleware import queue_graphql_cookie_applier
from app.core.http_session_cookies import (
    attach_session_cookies_to_response,
    clear_session_cookies_on_response,
)
from app.graphql.errors import raise_jsonrpc_as_graphql
from app.graphql.modules.auth.types import (
    AuthPayload,
    GqlSession,
    GqlUser,
    GqlUserProfile,
    RefreshPayload,
    SessionCookieMutationResult,
)


def _auth_payload_from_dict(raw: dict[str, Any]) -> AuthPayload:
    u = raw.get("user")
    s = raw.get("session")
    user_obj: Optional[GqlUser] = None
    if u:
        user_obj = GqlUser(
            id=str(u.get("id", "")),
            email=u.get("email"),
            user_metadata=cast(JSON, u.get("user_metadata") or {}),
            app_metadata=cast(JSON, u.get("app_metadata") or {}),
            created_at=u.get("created_at"),
            updated_at=u.get("updated_at"),
            is_active=bool(u.get("is_active", True)),
            is_verified=bool(u.get("is_verified", False)),
            profile=None,
        )
    sess_obj: Optional[GqlSession] = None
    if s:
        sess_obj = GqlSession(
            access_token=s["access_token"],
            refresh_token=s["refresh_token"],
            expires_in=int(s.get("expires_in") or 3600),
            expires_at=s.get("expires_at"),
            token_type=str(s.get("token_type") or "bearer"),
        )
    return AuthPayload(
        success=bool(raw.get("success")),
        requires_confirmation=bool(raw.get("requires_confirmation")),
        user=user_obj,
        session=sess_obj,
    )


def _gql_user_to_dict(u: Optional[GqlUser]) -> Any:
    if u is None:
        return None
    prof = u.profile
    prof_dict: Optional[dict[str, Any]] = None
    if prof is not None:
        prof_dict = {
            "username": prof.username,
            "avatar_url": prof.avatar_url,
            "bio": prof.bio,
            "preferences": prof.preferences,
            "created_at": prof.created_at,
            "updated_at": prof.updated_at,
        }
    return {
        "id": u.id,
        "email": u.email,
        "user_metadata": u.user_metadata,
        "app_metadata": u.app_metadata,
        "created_at": u.created_at,
        "updated_at": u.updated_at,
        "is_active": u.is_active,
        "is_verified": u.is_verified,
        "profile": prof_dict,
    }


def _gql_user_from_dict(raw: Any) -> Optional[GqlUser]:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        return None
    pd = raw.get("profile")
    profile: Optional[GqlUserProfile] = None
    if isinstance(pd, dict):
        profile = GqlUserProfile(
            username=pd.get("username"),
            avatar_url=pd.get("avatar_url"),
            bio=pd.get("bio"),
            preferences=cast(JSON, pd.get("preferences") or {}),
            created_at=pd.get("created_at"),
            updated_at=pd.get("updated_at"),
        )
    return GqlUser(
        id=str(raw.get("id", "")),
        email=raw.get("email"),
        user_metadata=cast(JSON, raw.get("user_metadata") or {}),
        app_metadata=cast(JSON, raw.get("app_metadata") or {}),
        created_at=raw.get("created_at"),
        updated_at=raw.get("updated_at"),
        is_active=bool(raw.get("is_active", True)),
        is_verified=bool(raw.get("is_verified", False)),
        profile=profile,
    )


async def _resolve_me_uncached(info: Info, token: str) -> Optional[GqlUser]:
    data = user_claims_from_access_token(token)
    if not data:
        return None
    sub = str(data.get("sub", ""))
    jwt_email = data.get("email")
    jwt_user_meta = cast(JSON, data.get("user_metadata") or {})
    jwt_app_meta = cast(JSON, data.get("app_metadata") or {})

    async with AsyncSessionLocal() as session:
        ur = UserRepository(session)
        row = await ur.get_by_id_with_profile(sub)

    if row is None:
        return GqlUser(
            id=sub,
            email=jwt_email,
            user_metadata=jwt_user_meta,
            app_metadata=jwt_app_meta,
            created_at=None,
            updated_at=None,
            is_active=True,
            is_verified=False,
            profile=None,
        )

    prof: Optional[GqlUserProfile] = None
    if row.profile is not None:
        p = row.profile
        prof = GqlUserProfile(
            username=p.username,
            avatar_url=p.avatar_url,
            bio=p.bio,
            preferences=cast(JSON, p.preferences or {}),
            created_at=p.created_at.isoformat() if p.created_at else None,
            updated_at=p.updated_at.isoformat() if p.updated_at else None,
        )

    return GqlUser(
        id=str(row.id),
        email=str(row.email) if row.email is not None else None,
        user_metadata=cast(JSON, row.user_metadata or {}),
        app_metadata=jwt_app_meta,
        created_at=row.created_at.isoformat() if row.created_at else None,
        updated_at=row.updated_at.isoformat() if row.updated_at else None,
        is_active=bool(row.is_active),
        is_verified=bool(row.is_verified),
        profile=prof,
    )


@strawberry.type
class AuthQuery:
    @strawberry.field
    async def me(self, info: Info) -> Optional[GqlUser]:
        ctx = info.context
        if not isinstance(ctx, GraphQLContext) or not ctx.auth_token:
            return None
        tok = ctx.auth_token
        data = user_claims_from_access_token(tok)
        if not data:
            return None
        sub = str(data.get("sub", ""))
        req = ctx.request

        if req is None:
            return await _resolve_me_uncached(info, tok)

        key = f"gql:me:v1:{sub}"

        async def _factory() -> Any:
            return _gql_user_to_dict(await _resolve_me_uncached(info, tok))

        blob = await cached_json_response(req, key, 25.0, _factory)
        return _gql_user_from_dict(blob)

    @strawberry.field
    async def email_registered(self, email: str) -> bool:
        """Whether an account exists for this email (welcome flow; enables enumeration)."""
        normalized = email.strip().lower()
        if not normalized:
            return False
        async with AsyncSessionLocal() as session:
            ur = UserRepository(session)
            u = await ur.get_by_email(normalized)
            return u is not None


@strawberry.type
class AuthMutation:
    @strawberry.mutation
    async def sign_up(
        self,
        email: str,
        password: str,
        metadata: Optional[JSON] = None,
    ) -> AuthPayload:
        params: dict[str, Any] = {
            "email": email,
            "password": password,
            "metadata": metadata or {},
        }
        try:
            raw = await auth_handlers.handle_auth_signup(params, None)
        except JSONRPCError as e:
            raise_jsonrpc_as_graphql(e)
        return _auth_payload_from_dict(raw)

    @strawberry.mutation
    async def sign_in(self, email: str, password: str) -> AuthPayload:
        params = {"email": email, "password": password}
        try:
            raw = await auth_handlers.handle_auth_signin(params, None)
        except JSONRPCError as e:
            raise_jsonrpc_as_graphql(e)
        return _auth_payload_from_dict(raw)

    @strawberry.mutation
    async def refresh_session(
        self, refresh_token: Optional[str] = None
    ) -> RefreshPayload:
        params: dict[str, Any] = {}
        if refresh_token:
            params["refresh_token"] = refresh_token
        try:
            raw = await auth_handlers.handle_auth_refresh(params, None)
        except JSONRPCError as e:
            raise_jsonrpc_as_graphql(e)
        sess = raw.get("session")
        if not sess:
            raise GraphQLError(
                "No session returned from refresh",
                extensions={"code": "INTERNAL"},
            )
        return RefreshPayload(
            success=bool(raw.get("success")),
            session=GqlSession(
                access_token=sess["access_token"],
                refresh_token=sess["refresh_token"],
                expires_in=int(sess.get("expires_in") or 3600),
                expires_at=sess.get("expires_at"),
                token_type=str(sess.get("token_type") or "bearer"),
            ),
        )

    @strawberry.mutation
    async def establish_session(
        self,
        info: Info,
        access_token: str,
        refresh_token: str,
        expires_in: Optional[int] = None,
    ) -> SessionCookieMutationResult:
        """Persist httpOnly session cookies (replaces ``POST /api/auth/session``)."""
        ctx = info.context
        if not isinstance(ctx, GraphQLContext):
            return SessionCookieMutationResult(ok=False, error="Invalid context")
        access = access_token.strip()
        refresh = refresh_token.strip()
        if not access or not refresh:
            return SessionCookieMutationResult(
                ok=False, error="accessToken and refreshToken required"
            )
        max_age = max(60, expires_in or 3600)
        queue_graphql_cookie_applier(
            ctx.request,
            lambda resp: attach_session_cookies_to_response(
                resp, access, refresh, max_age
            ),
        )
        return SessionCookieMutationResult(ok=True)

    @strawberry.mutation
    async def clear_session(self, info: Info) -> SessionCookieMutationResult:
        """Clear httpOnly session cookies (replaces ``DELETE /api/auth/session``)."""
        ctx = info.context
        if not isinstance(ctx, GraphQLContext):
            return SessionCookieMutationResult(ok=False, error="Invalid context")
        queue_graphql_cookie_applier(
            ctx.request,
            clear_session_cookies_on_response,
        )
        return SessionCookieMutationResult(ok=True)
