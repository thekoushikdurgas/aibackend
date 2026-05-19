"""User CRUD."""

from __future__ import annotations

from typing import Any, Dict, Optional, cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: str) -> Optional[User]:
        r = await self.session.execute(select(User).where(User.id == user_id))
        return r.scalar_one_or_none()

    async def get_by_id_with_profile(self, user_id: str) -> Optional[User]:
        r = await self.session.execute(
            select(User).options(selectinload(User.profile)).where(User.id == user_id)
        )
        return r.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        r = await self.session.execute(
            select(User).where(User.email == email.strip().lower())
        )
        return r.scalar_one_or_none()

    async def create(
        self,
        email: str,
        hashed_password: Optional[str],
        user_metadata: Optional[Dict[str, Any]] = None,
        is_verified: bool = True,
    ) -> User:
        u = User(
            email=email.strip().lower(),
            hashed_password=hashed_password,
            is_verified=is_verified,
            user_metadata=user_metadata or {},
        )
        self.session.add(u)
        await self.session.flush()
        return u

    async def update_password(self, user_id: str, hashed_password: str) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(hashed_password=hashed_password)
        )

    async def increment_token_version(self, user_id: str) -> None:
        u = await self.get_by_id(user_id)
        if u is None:
            return
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(token_version=(u.token_version or 0) + 1)
        )

    async def update_email(self, user_id: str, new_email: str) -> None:
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(email=new_email.strip().lower())
        )

    async def merge_user_metadata(
        self, user_id: str, metadata: Dict[str, Any]
    ) -> Optional[User]:
        u = await self.get_by_id(user_id)
        if u is None:
            return None
        base = cast(Any, u.user_metadata)
        merged = {**(base if isinstance(base, dict) else {}), **metadata}
        await self.session.execute(
            update(User).where(User.id == user_id).values(user_metadata=merged)
        )
        await self.session.flush()
        return await self.get_by_id(user_id)
