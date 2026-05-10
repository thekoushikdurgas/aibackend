"""
Conversation Memory Service with Database Persistence
Supports both in-memory (Redis) and database-backed storage.
"""

import logging
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, cast
import json

from sqlalchemy import select, delete, func

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.conversation import (
    Conversation as DBConversation,
    Message as DBMessage,
    MessageRole,
)

logger = logging.getLogger(__name__)


@dataclass
class Message:
    """Single conversation message"""

    role: str  # user, assistant, system
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Optional[Dict] = None


@dataclass
class Conversation:
    """Conversation with history"""

    id: str
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)

    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add a message to the conversation"""
        self.messages.append(Message(role=role, content=content, metadata=metadata))
        self.updated_at = datetime.utcnow()

    def get_history(self, max_messages: int = 20) -> List[Dict[str, str]]:
        """Get conversation history for LLM context"""
        recent = (
            self.messages[-max_messages:]
            if len(self.messages) > max_messages
            else self.messages
        )
        return [{"role": msg.role, "content": msg.content} for msg in recent]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "timestamp": m.timestamp.isoformat(),
                    "metadata": m.metadata,
                }
                for m in self.messages
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class ConversationMemory:
    """
    Conversation storage with multiple backends:
    - In-memory (default, for development)
    - Redis (if configured)
    - Database (PostgreSQL/SQLite, if configured)
    """

    def __init__(
        self,
        max_conversations: int = 1000,
        max_messages_per_conversation: int = 100,
        use_database: Optional[bool] = None,
    ):
        """
        Initialize conversation memory.

        Args:
            max_conversations: Maximum conversations to store (in-memory only)
            max_messages_per_conversation: Maximum messages per conversation
            use_database: Force database usage (auto-detects if None)
        """
        self.max_conversations = max_conversations
        self.max_messages = max_messages_per_conversation
        self._conversations: Dict[str, Conversation] = {}
        self._redis_client = None
        self._use_database = use_database

        # Determine storage backend
        if use_database is None:
            # Auto-detect: prefer database if PostgreSQL URL configured
            self._use_database = bool(
                settings.postgresql_url
                or (
                    hasattr(settings, "database_url")
                    and "postgresql" in settings.database_url.lower()
                )
            )

        # Try to use Redis if configured
        if settings.use_redis and not self._use_database:
            self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            import redis

            self._redis_client = redis.from_url(settings.redis_url)
            self._redis_client.ping()
            logger.info("Redis connection established for conversation memory")
        except Exception as e:
            logger.warning(f"Redis connection failed, using in-memory storage: {e}")
            self._redis_client = None

    async def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Get a conversation by ID"""
        if self._use_database:
            return await self._get_from_database(conversation_id)
        if self._redis_client:
            return self._get_from_redis(conversation_id)
        return self._conversations.get(conversation_id)

    def get_conversation_sync(self, conversation_id: str) -> Optional[Conversation]:
        """Synchronous version for backward compatibility"""
        if self._use_database:
            return self._run_async(self.get_conversation(conversation_id))
        if self._redis_client:
            return self._get_from_redis(conversation_id)
        return self._conversations.get(conversation_id)

    async def create_conversation(
        self,
        conversation_id: str,
        metadata: Optional[Dict] = None,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation"""
        conversation = Conversation(id=conversation_id, metadata=metadata or {})

        if self._use_database:
            await self._save_to_database(conversation, user_id=user_id, title=title)
        elif self._redis_client:
            self._save_to_redis(conversation)
        else:
            self._conversations[conversation_id] = conversation
            self._cleanup_old_conversations()

        logger.debug(f"Created conversation: {conversation_id}")
        return conversation

    def create_conversation_sync(
        self, conversation_id: str, metadata: Optional[Dict] = None
    ) -> Conversation:
        """Synchronous version for backward compatibility"""
        if self._use_database:
            return self._run_async(
                self.create_conversation(conversation_id, metadata=metadata)
            )
        conversation = Conversation(id=conversation_id, metadata=metadata or {})

        if self._redis_client:
            self._save_to_redis(conversation)
        else:
            self._conversations[conversation_id] = conversation
            self._cleanup_old_conversations()

        return conversation

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
        tokens: Optional[int] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Conversation:
        """Add a message to a conversation (creates if doesn't exist)"""
        conversation = await self.get_conversation(conversation_id)

        if conversation is None:
            conversation = await self.create_conversation(conversation_id)

        conversation.add_message(role, content, metadata)

        # Trim old messages
        if len(conversation.messages) > self.max_messages:
            conversation.messages = conversation.messages[-self.max_messages :]

        # Save with enhanced metadata
        if self._use_database:
            await self._save_message_to_database(
                conversation_id=conversation_id,
                role=role,
                content=content,
                metadata=metadata,
                tokens=tokens,
                provider=provider,
                model=model,
            )
        elif self._redis_client:
            self._save_to_redis(conversation)

        return conversation

    def add_message_sync(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> Conversation:
        """Synchronous version for backward compatibility"""
        if self._use_database:
            return self._run_async(
                self.add_message(
                    conversation_id=conversation_id,
                    role=role,
                    content=content,
                    metadata=metadata,
                )
            )
        conversation = self.get_conversation_sync(conversation_id)

        if conversation is None:
            conversation = self.create_conversation_sync(conversation_id)

        conversation.add_message(role, content, metadata)

        # Trim old messages
        if len(conversation.messages) > self.max_messages:
            conversation.messages = conversation.messages[-self.max_messages :]

        # Save
        if self._redis_client:
            self._save_to_redis(conversation)

        return conversation

    async def get_history(
        self, conversation_id: str, max_messages: int = 20
    ) -> List[Dict[str, str]]:
        """Get conversation history for LLM"""
        conversation = await self.get_conversation(conversation_id)
        if conversation is None:
            return []
        return conversation.get_history(max_messages)

    def get_history_sync(
        self, conversation_id: str, max_messages: int = 20
    ) -> List[Dict[str, str]]:
        """Synchronous version for backward compatibility"""
        conversation = self.get_conversation_sync(conversation_id)
        if conversation is None:
            return []
        return conversation.get_history(max_messages)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation"""
        if self._use_database:
            return await self._delete_from_database(conversation_id)
        if self._redis_client:
            return self._delete_from_redis(conversation_id)

        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False

    async def clear_all(self):
        """Clear all conversations"""
        if self._use_database:
            await self._clear_all_from_database()
            logger.info("Cleared all conversations")
            return
        if self._redis_client:
            # Clear Redis keys matching pattern
            keys = self._redis_client.keys("conversation:*")
            if keys:
                self._redis_client.delete(*keys)
        else:
            self._conversations.clear()

        logger.info("Cleared all conversations")

    async def list_conversations(self, limit: int = 50) -> List[Dict]:
        """List recent conversations"""
        if self._use_database:
            return await self._list_from_database(limit)
        if self._redis_client:
            return self._list_from_redis(limit)

        conversations = sorted(
            self._conversations.values(), key=lambda c: c.updated_at, reverse=True
        )[:limit]

        return [
            {
                "id": c.id,
                "message_count": len(c.messages),
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in conversations
        ]

    def _run_async(self, coro):
        """Run async call from sync context."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)
        raise RuntimeError(
            "Synchronous memory API cannot be used from an active event loop"
        )

    def _cleanup_old_conversations(self):
        """Remove oldest conversations if over limit"""
        if len(self._conversations) > self.max_conversations:
            sorted_convos = sorted(
                self._conversations.items(), key=lambda x: x[1].updated_at
            )
            # Remove oldest 10%
            to_remove = len(self._conversations) - int(self.max_conversations * 0.9)
            for conv_id, _ in sorted_convos[:to_remove]:
                del self._conversations[conv_id]
            logger.info(f"Cleaned up {to_remove} old conversations")

    def _get_from_redis(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation from Redis"""
        rc = self._redis_client
        if rc is None:
            return None
        try:
            data = rc.get(f"conversation:{conversation_id}")
            if data:
                conv_dict = json.loads(data)
                conv = Conversation(
                    id=conv_dict["id"],
                    created_at=datetime.fromisoformat(conv_dict["created_at"]),
                    updated_at=datetime.fromisoformat(conv_dict["updated_at"]),
                    metadata=conv_dict.get("metadata", {}),
                )
                for msg in conv_dict["messages"]:
                    conv.messages.append(
                        Message(
                            role=msg["role"],
                            content=msg["content"],
                            timestamp=datetime.fromisoformat(msg["timestamp"]),
                            metadata=msg.get("metadata"),
                        )
                    )
                return conv
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None

    def _save_to_redis(self, conversation: Conversation):
        """Save conversation to Redis"""
        rc = self._redis_client
        if rc is None:
            return
        try:
            rc.setex(
                f"conversation:{conversation.id}",
                86400 * 7,  # 7 day expiry
                json.dumps(conversation.to_dict()),
            )
        except Exception as e:
            logger.error(f"Redis save error: {e}")

    def _delete_from_redis(self, conversation_id: str) -> bool:
        """Delete conversation from Redis"""
        rc = self._redis_client
        if rc is None:
            return False
        try:
            return rc.delete(f"conversation:{conversation_id}") > 0
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False

    def _list_from_redis(self, limit: int) -> List[Dict]:
        """List conversations from Redis"""
        rc = self._redis_client
        if rc is None:
            return []
        try:
            keys = rc.keys("conversation:*")[: limit * 2]
            results = []
            for key in keys:
                data = rc.get(key)
                if data:
                    conv_dict = json.loads(data)
                    results.append(
                        {
                            "id": conv_dict["id"],
                            "message_count": len(conv_dict["messages"]),
                            "created_at": conv_dict["created_at"],
                            "updated_at": conv_dict["updated_at"],
                        }
                    )
            return sorted(results, key=lambda x: x["updated_at"], reverse=True)[:limit]
        except Exception as e:
            logger.error(f"Redis list error: {e}")
            return []

    async def _get_from_database(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation from database"""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(DBConversation).where(DBConversation.id == conversation_id)
                )
                db_conv = result.scalar_one_or_none()

                if not db_conv:
                    return None

                # Load messages
                messages_result = await session.execute(
                    select(DBMessage)
                    .where(DBMessage.conversation_id == conversation_id)
                    .order_by(DBMessage.created_at)
                )
                db_messages = messages_result.scalars().all()

                # Convert to in-memory format
                conversation = Conversation(
                    id=str(db_conv.id),
                    created_at=cast(datetime, db_conv.created_at),
                    updated_at=cast(datetime, db_conv.updated_at),
                    metadata=dict(db_conv.extra_metadata or {}),
                )

                for db_msg in db_messages:
                    role_raw = db_msg.role
                    role_str = (
                        role_raw.value
                        if isinstance(role_raw, MessageRole)
                        else str(role_raw)
                    )
                    conversation.messages.append(
                        Message(
                            role=role_str,
                            content=str(db_msg.content),
                            timestamp=cast(datetime, db_msg.created_at),
                            metadata={
                                **(db_msg.extra_metadata or {}),
                                "tokens": db_msg.tokens,
                                "provider": db_msg.provider,
                                "model": db_msg.model,
                            },
                        )
                    )

                return conversation
        except Exception as e:
            logger.error(f"Database get error: {e}", exc_info=True)
            return None

    async def _save_to_database(
        self,
        conversation: Conversation,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
    ):
        """Save conversation to database"""
        try:
            async with AsyncSessionLocal() as session:
                # Check if exists
                result = await session.execute(
                    select(DBConversation).where(DBConversation.id == conversation.id)
                )
                db_conv = result.scalar_one_or_none()

                if db_conv:
                    # Update existing
                    db_conv.updated_at = datetime.utcnow()  # type: ignore[assignment]
                    if title:
                        db_conv.title = title  # type: ignore[assignment]
                else:
                    # Create new
                    db_conv = DBConversation(
                        id=conversation.id,
                        user_id=user_id,
                        title=title or conversation.metadata.get("title"),
                        extra_metadata=conversation.metadata,
                    )
                    session.add(db_conv)

                await session.commit()
        except Exception as e:
            logger.error(f"Database save error: {e}", exc_info=True)

    async def _save_message_to_database(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
        tokens: Optional[int] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Save a message to database"""
        try:
            async with AsyncSessionLocal() as session:
                # Ensure conversation exists
                result = await session.execute(
                    select(DBConversation).where(DBConversation.id == conversation_id)
                )
                db_conv = result.scalar_one_or_none()

                if not db_conv:
                    db_conv = DBConversation(id=conversation_id)
                    session.add(db_conv)

                # Create message
                db_msg = DBMessage(
                    conversation_id=conversation_id,
                    role=(
                        MessageRole(role)
                        if role in [r.value for r in MessageRole]
                        else MessageRole.USER
                    ),
                    content=content,
                    tokens=tokens,
                    provider=provider,
                    model=model,
                    extra_metadata=metadata or {},
                )
                session.add(db_msg)

                # Update conversation timestamp
                db_conv.updated_at = datetime.utcnow()  # type: ignore[assignment]

                await session.commit()
        except Exception as e:
            logger.error(f"Database message save error: {e}", exc_info=True)

    async def _delete_from_database(self, conversation_id: str) -> bool:
        """Delete conversation and associated messages from database."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    delete(DBConversation).where(DBConversation.id == conversation_id)
                )
                await session.commit()
                return int(cast(Any, result).rowcount or 0) > 0
        except Exception as e:
            logger.error(f"Database delete error: {e}", exc_info=True)
            return False

    async def _clear_all_from_database(self) -> None:
        """Delete all conversations from database."""
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(delete(DBConversation))
                await session.commit()
        except Exception as e:
            logger.error(f"Database clear-all error: {e}", exc_info=True)

    async def _list_from_database(self, limit: int = 50) -> List[Dict]:
        """List recent conversations from database."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    select(DBConversation)
                    .order_by(DBConversation.updated_at.desc())
                    .limit(limit)
                )
                conversations = result.scalars().all()
                rows: List[Dict] = []
                for conv in conversations:
                    count_result = await session.execute(
                        select(func.count(DBMessage.id)).where(
                            DBMessage.conversation_id == conv.id
                        )
                    )
                    rows.append(
                        {
                            "id": conv.id,
                            "message_count": int(count_result.scalar() or 0),
                            "created_at": (
                                conv.created_at.isoformat() if conv.created_at else None
                            ),
                            "updated_at": (
                                conv.updated_at.isoformat() if conv.updated_at else None
                            ),
                        }
                    )
                return rows
        except Exception as e:
            logger.error(f"Database list error: {e}", exc_info=True)
            return []


# Global memory instance
_conversation_memory: Optional[ConversationMemory] = None


def get_conversation_memory() -> ConversationMemory:
    """Get global conversation memory instance"""
    global _conversation_memory
    if _conversation_memory is None:
        _conversation_memory = ConversationMemory()
    return _conversation_memory
