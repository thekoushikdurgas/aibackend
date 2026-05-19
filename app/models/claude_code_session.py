"""
SQLAlchemy model for persisting Claude Code agent sessions.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, List

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.helpers import utc_now

from .metrics import Base


class ClaudeCodeSessionModel(Base):
    __tablename__ = "claude_code_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    messages: Mapped[List[Any]] = mapped_column(JSON, nullable=False, default=list)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )
