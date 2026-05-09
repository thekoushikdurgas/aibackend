"""
Supabase database operations wrapper
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.core.supabase_client import get_supabase_client, get_supabase_admin_client

logger = logging.getLogger(__name__)


class SupabaseDB:
    """Wrapper for Supabase database operations"""

    def __init__(self, use_admin: bool = False):
        """
        Initialize Supabase database wrapper

        Args:
            use_admin: Use admin client (bypasses RLS)
        """
        self.use_admin = use_admin
        self.client = (
            get_supabase_admin_client() if use_admin else get_supabase_client()
        )

    def _get_table(self, table_name: str):
        """Get Supabase table reference"""
        if not self.client:
            raise RuntimeError("Supabase client not initialized")
        return self.client.table(table_name)

    # ===================
    # Profile Operations
    # ===================

    def get_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile"""
        try:
            response = (
                self._get_table("profiles").select("*").eq("id", user_id).execute()
            )
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting profile for user {user_id}: {e}")
            return None

    def create_profile(
        self, user_id: str, profile_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create user profile"""
        try:
            data = {
                "id": user_id,
                **profile_data,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            response = self._get_table("profiles").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating profile for user {user_id}: {e}")
            return None

    def update_profile(
        self, user_id: str, profile_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update user profile"""
        try:
            data = {**profile_data, "updated_at": datetime.utcnow().isoformat()}
            response = (
                self._get_table("profiles").update(data).eq("id", user_id).execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating profile for user {user_id}: {e}")
            return None

    # ===================
    # Conversation Operations
    # ===================

    def create_conversation(
        self, conversation_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create a new conversation"""
        try:
            data = {
                **conversation_data,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            response = self._get_table("conversations").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating conversation: {e}")
            return None

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID"""
        try:
            response = (
                self._get_table("conversations")
                .select("*")
                .eq("id", conversation_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting conversation {conversation_id}: {e}")
            return None

    def get_user_conversations(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        archived: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Get conversations for a user"""
        try:
            query = self._get_table("conversations").select("*").eq("user_id", user_id)

            if archived is not None:
                query = query.eq("is_archived", archived)

            response = (
                query.order("updated_at", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting conversations for user {user_id}: {e}")
            return []

    def update_conversation(
        self, conversation_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update conversation"""
        try:
            data = {**updates, "updated_at": datetime.utcnow().isoformat()}
            response = (
                self._get_table("conversations")
                .update(data)
                .eq("id", conversation_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating conversation {conversation_id}: {e}")
            return None

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete conversation"""
        try:
            self._get_table("conversations").delete().eq(
                "id", conversation_id
            ).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            return False

    # ===================
    # Message Operations
    # ===================

    def create_message(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a new message"""
        try:
            data = {**message_data, "created_at": datetime.utcnow().isoformat()}
            response = self._get_table("messages").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating message: {e}")
            return None

    def get_conversation_messages(
        self, conversation_id: str, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get messages for a conversation"""
        try:
            response = (
                self._get_table("messages")
                .select("*")
                .eq("conversation_id", conversation_id)
                .order("created_at", desc=False)
                .limit(limit)
                .offset(offset)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(
                f"Error getting messages for conversation {conversation_id}: {e}"
            )
            return []

    def delete_message(self, message_id: str) -> bool:
        """Delete message"""
        try:
            self._get_table("messages").delete().eq("id", message_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting message {message_id}: {e}")
            return False

    # ===================
    # RAG Document Operations
    # ===================

    def create_rag_document(
        self, document_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create RAG document metadata"""
        try:
            data = {
                **document_data,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            response = self._get_table("rag_documents").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error creating RAG document: {e}")
            return None

    def get_user_rag_documents(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get RAG documents for a user"""
        try:
            response = (
                self._get_table("rag_documents")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .offset(offset)
                .execute()
            )
            return response.data or []
        except Exception as e:
            logger.error(f"Error getting RAG documents for user {user_id}: {e}")
            return []

    def get_rag_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get RAG document by ID"""
        try:
            response = (
                self._get_table("rag_documents")
                .select("*")
                .eq("id", document_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error getting RAG document {document_id}: {e}")
            return None

    def update_rag_document(
        self, document_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update RAG document"""
        try:
            data = {**updates, "updated_at": datetime.utcnow().isoformat()}
            response = (
                self._get_table("rag_documents")
                .update(data)
                .eq("id", document_id)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Error updating RAG document {document_id}: {e}")
            return None

    def delete_rag_document(self, document_id: str) -> bool:
        """Delete RAG document"""
        try:
            self._get_table("rag_documents").delete().eq("id", document_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error deleting RAG document {document_id}: {e}")
            return False


# Convenience function to get database instance
def get_supabase_db(use_admin: bool = False) -> SupabaseDB:
    """Get Supabase database instance"""
    return SupabaseDB(use_admin=use_admin)
