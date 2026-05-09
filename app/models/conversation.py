"""
Conversation and Message Database Models
"""

import uuid
import enum
from datetime import datetime
from typing import Dict, Any

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Boolean,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.orm import relationship

from app.models.metrics import Base


class MessageRole(str, enum.Enum):
    """Enum for message roles"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(Base):
    """Conversation/Session model for chat history"""

    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=True, index=True)  # Optional for anonymous users
    title = Column(String(500), nullable=True)
    model = Column(String(100), nullable=True)  # LLM model used
    provider = Column(String(50), nullable=True)  # LLM provider (ollama, gemini, etc.)
    temperature = Column(Integer, default=7)  # 0-10, stored as integer
    max_tokens = Column(Integer, default=2048)
    system_prompt = Column(Text, nullable=True)
    extra_metadata = Column(
        JSON, default={}
    )  # Additional metadata (renamed from 'metadata' - reserved in SQLAlchemy 2.0)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    __table_args__ = (Index("idx_conversations_user_updated", "user_id", "updated_at"),)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "model": self.model,
            "provider": self.provider,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt,
            "metadata": self.extra_metadata or {},
            "is_archived": self.is_archived,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "message_count": len(self.messages) if self.messages else 0,
        }


class Message(Base):
    """Message model for conversations"""

    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(
        String,
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(  # type: ignore[var-annotated]
        SQLEnum(MessageRole), default=MessageRole.USER, nullable=False
    )
    content = Column(Text, nullable=False)
    tokens = Column(Integer, nullable=True)  # Token count
    provider = Column(String(50), nullable=True)  # LLM provider used
    model = Column(String(100), nullable=True)  # Model used
    extra_metadata = Column(
        JSON, default={}
    )  # Store timing, usage stats, etc. (renamed from 'metadata' - reserved in SQLAlchemy 2.0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": (
                self.role.value if isinstance(self.role, MessageRole) else self.role
            ),
            "content": self.content,
            "tokens": self.tokens,
            "provider": self.provider,
            "model": self.model,
            "metadata": self.extra_metadata or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
