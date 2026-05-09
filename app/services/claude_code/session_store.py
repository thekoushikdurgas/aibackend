"""
Persist Claude Code sessions using SQLAlchemy (PostgreSQL or SQLite).
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, List, Optional, cast

from sqlalchemy import CursorResult, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ClaudeCodeSessionModel
from .models import StoredSession

logger = logging.getLogger(__name__)


async def save_session(session: StoredSession, db: AsyncSession) -> str:
    row = await db.get(ClaudeCodeSessionModel, session.session_id)
    now = datetime.utcnow()
    if row is None:
        row = ClaudeCodeSessionModel(
            session_id=session.session_id,
            messages=list(session.messages),
            input_tokens=session.input_tokens,
            output_tokens=session.output_tokens,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    else:
        row.messages = list(session.messages)  # type: ignore[assignment]
        row.input_tokens = session.input_tokens  # type: ignore[assignment]
        row.output_tokens = session.output_tokens  # type: ignore[assignment]
        row.updated_at = now  # type: ignore[assignment]
    await db.flush()
    return session.session_id


async def load_session_db(session_id: str, db: AsyncSession) -> Optional[StoredSession]:
    result = await db.execute(
        select(ClaudeCodeSessionModel).where(
            ClaudeCodeSessionModel.session_id == session_id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    raw_messages: List[Any] = list(row.messages or [])
    if not isinstance(raw_messages, list):
        raw_messages = list(raw_messages) if raw_messages else []
    return StoredSession(
        session_id=str(row.session_id),
        messages=tuple(str(m) for m in raw_messages),
        input_tokens=int(row.input_tokens or 0),
        output_tokens=int(row.output_tokens or 0),
    )


async def delete_session(session_id: str, db: AsyncSession) -> bool:
    res = cast(
        CursorResult[Any],
        await db.execute(
            delete(ClaudeCodeSessionModel).where(
                ClaudeCodeSessionModel.session_id == session_id
            )
        ),
    )
    return (res.rowcount or 0) > 0
