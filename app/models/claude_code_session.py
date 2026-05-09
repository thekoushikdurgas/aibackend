"""
SQLAlchemy model for persisting Claude Code agent sessions.
"""

from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, Integer, String

from .metrics import Base


class ClaudeCodeSessionModel(Base):
    __tablename__ = "claude_code_sessions"

    session_id = Column(String(64), primary_key=True)
    messages = Column(JSON, nullable=False, default=list)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
