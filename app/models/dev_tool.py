"""Dev AI toolbox persistence models."""

from __future__ import annotations

import uuid
from typing import Any, Dict

from sqlalchemy import Column, DateTime, String, Text

from app.models.metrics import Base
from app.utils.helpers import utc_now


class DevToolMemoryModel(Base):
    __tablename__ = "dev_tool_memories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(255), index=True, nullable=False)
    type = Column(String(16), nullable=False)  # text | url | file
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "userId": self.owner_id,
            "type": self.type,
            "title": self.title,
            "content": self.content,
            "createdAt": (
                int(self.created_at.timestamp() * 1000) if self.created_at else 0
            ),
        }


class DevToolRegexHistoryModel(Base):
    __tablename__ = "dev_tool_regex_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(255), index=True, nullable=False)
    mode = Column(String(16), nullable=False)  # generate | explain
    input = Column(Text, nullable=False)
    regex = Column(Text, nullable=True)
    explanation = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode,
            "input": self.input,
            "regex": self.regex,
            "explanation": self.explanation,
            "timestamp": (
                int(self.created_at.timestamp() * 1000) if self.created_at else 0
            ),
        }


class DevToolIconHistoryModel(Base):
    __tablename__ = "dev_tool_icon_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(255), index=True, nullable=False)
    source_storage_path = Column(String(2000), nullable=False)
    source_image_url = Column(String(2000), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_image_path": self.source_storage_path,
            "source_image_url": self.source_image_url or "",
            "created_at": self.created_at.isoformat() if self.created_at else "",
        }
