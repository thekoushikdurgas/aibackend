"""
Pydantic schemas for app data models (profiles, conversations, RAG metadata).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


def _empty_dict() -> Dict[str, Any]:
    return {}


def _empty_str_list() -> List[str]:
    return []


class MessageRole(str, Enum):
    """Message role enum"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ===================
# Profile Schemas
# ===================


class ProfileBase(BaseModel):
    """Base profile schema"""

    username: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = Field(default_factory=_empty_dict)


class ProfileCreate(ProfileBase):
    """Profile creation schema"""

    id: str  # User ID (same as users.id)


class ProfileUpdate(BaseModel):
    """Profile update schema"""

    username: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None


class Profile(ProfileBase):
    """Profile response schema"""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================
# Conversation Schemas
# ===================


class ConversationBase(BaseModel):
    """Base conversation schema"""

    user_id: str
    title: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    temperature: Optional[int] = Field(default=7, ge=0, le=10)
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=8192)
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=_empty_dict)
    is_archived: bool = False


class ConversationCreate(ConversationBase):
    """Conversation creation schema"""

    pass


class ConversationUpdate(BaseModel):
    """Conversation update schema"""

    title: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    temperature: Optional[int] = Field(None, ge=0, le=10)
    max_tokens: Optional[int] = Field(None, ge=1, le=8192)
    system_prompt: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    is_archived: Optional[bool] = None


class Conversation(ConversationBase):
    """Conversation response schema"""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================
# Message Schemas
# ===================


class MessageBase(BaseModel):
    """Base message schema"""

    conversation_id: str
    role: MessageRole
    content: str
    tokens: Optional[int] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=_empty_dict)


class MessageCreate(MessageBase):
    """Message creation schema"""

    pass


class Message(MessageBase):
    """Message response schema"""

    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ===================
# RAG Document Schemas
# ===================


class RAGDocumentBase(BaseModel):
    """Base RAG document schema"""

    user_id: str
    title: str
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    storage_path: Optional[str] = None
    vector_ids: Optional[List[str]] = Field(default_factory=_empty_str_list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=_empty_dict)
    indexed: bool = False


class RAGDocumentCreate(RAGDocumentBase):
    """RAG document creation schema"""

    pass


class RAGDocumentUpdate(BaseModel):
    """RAG document update schema"""

    title: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    storage_path: Optional[str] = None
    vector_ids: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    indexed: Optional[bool] = None


class RAGDocument(RAGDocumentBase):
    """RAG document response schema"""

    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
