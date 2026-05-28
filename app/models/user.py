"""
Application user, profile, and RAG document ORM models (replaces Supabase auth.users + app tables).
"""

import uuid
from typing import Any, Dict

from app.utils.helpers import utc_now
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    BigInteger,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship

from app.models.metrics import Base


class User(Base):
    """Local application user (email/password or future OAuth)."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(320), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    token_version = Column(Integer, default=0, nullable=False)
    user_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    profile = relationship(
        "Profile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    rag_documents = relationship(
        "RAGDocument", back_populates="user", cascade="all, delete-orphan"
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "user_metadata": self.user_metadata or {},
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Profile(Base):
    """User profile row (1:1 with users)."""

    __tablename__ = "profiles"

    id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    username = Column(String(255), unique=True, nullable=True)
    avatar_url = Column(String(1024), nullable=True)
    bio = Column(Text, nullable=True)
    preferences = Column(JSON, default=dict)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="profile")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "avatar_url": self.avatar_url,
            "bio": self.bio,
            "preferences": self.preferences or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RAGDocument(Base):
    """RAG document metadata stored in the primary app database."""

    __tablename__ = "rag_documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(512), nullable=False)
    file_path = Column(String(1024), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    mime_type = Column(String(255), nullable=True)
    storage_path = Column(String(2048), nullable=True)
    vector_ids = Column(JSON, default=list)
    extra_metadata = Column(JSON, default=dict)
    indexed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="rag_documents")

    __table_args__ = (Index("idx_rag_documents_user_created", "user_id", "created_at"),)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "storage_path": self.storage_path,
            "vector_ids": self.vector_ids or [],
            "metadata": self.extra_metadata or {},
            "indexed": self.indexed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
