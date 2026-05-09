"""GraphQL types for authentication."""

from __future__ import annotations

from typing import Optional

import strawberry
from strawberry.scalars import JSON


@strawberry.type
class GqlSession:
    access_token: str
    refresh_token: str
    expires_in: int
    expires_at: Optional[float] = None
    token_type: str


@strawberry.type
class GqlUser:
    id: str
    email: Optional[str]
    user_metadata: JSON
    app_metadata: JSON
    created_at: Optional[str] = None


@strawberry.type
class AuthPayload:
    success: bool
    requires_confirmation: bool = False
    user: Optional[GqlUser] = None
    session: Optional[GqlSession] = None


@strawberry.type
class RefreshPayload:
    success: bool
    session: Optional[GqlSession] = None
