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
from app.graphql.context import GraphQLContext
from app.graphql.errors import raise_jsonrpc_as_graphql
from app.graphql.modules.auth.types import (
    AuthPayload,
    GqlSession,
    GqlUser,
    RefreshPayload,
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


@strawberry.type
class AuthQuery:
    @strawberry.field
    def me(self, info: Info) -> Optional[GqlUser]:
        ctx = info.context
        if not isinstance(ctx, GraphQLContext) or not ctx.auth_token:
            return None
        data = user_claims_from_access_token(ctx.auth_token)
        if not data:
            return None
        return GqlUser(
            id=str(data.get("sub", "")),
            email=data.get("email"),
            user_metadata=cast(JSON, data.get("user_metadata") or {}),
            app_metadata=cast(JSON, data.get("app_metadata") or {}),
            created_at=None,
        )

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
