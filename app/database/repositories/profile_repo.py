"""Profile CRUD."""

from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import Profile


class ProfileRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, user_id: str) -> Optional[Profile]:
        r = await self.session.execute(select(Profile).where(Profile.id == user_id))
        return r.scalar_one_or_none()

    async def create_for_user(self, user_id: str) -> Profile:
        p = Profile(id=user_id)
        self.session.add(p)
        await self.session.flush()
        return p

    async def update(self, user_id: str, data: Dict[str, Any]) -> Optional[Profile]:
        p = await self.get(user_id)
        if p is None:
            return None
        vals: Dict[str, Any] = {}
        if "username" in data and data["username"] is not None:
            vals["username"] = data["username"]
        if "avatar_url" in data and data["avatar_url"] is not None:
            vals["avatar_url"] = data["avatar_url"]
        if "bio" in data and data["bio"] is not None:
            vals["bio"] = data["bio"]
        if "preferences" in data and data["preferences"] is not None:
            vals["preferences"] = data["preferences"]
        if not vals:
            return p
        await self.session.execute(
            update(Profile).where(Profile.id == user_id).values(**vals)
        )
        await self.session.refresh(p)
        return await self.get(user_id)
