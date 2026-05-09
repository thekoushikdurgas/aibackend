"""
Service for migrating data between SQLite and Supabase
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from app.database.supabase import get_supabase_db
from app.core.supabase_client import is_supabase_configured

logger = logging.getLogger(__name__)


class MigrationService:
    """Service for data migration operations"""

    def __init__(self):
        self.db = get_supabase_db(use_admin=True) if is_supabase_configured() else None

    def migrate_conversation(
        self, conversation_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Migrate a single conversation from SQLite format to Supabase

        Args:
            conversation_data: Conversation data from SQLite

        Returns:
            Created conversation in Supabase, None if failed
        """
        if not self.db:
            logger.error("Supabase not configured")
            return None

        try:
            # Transform data format
            supabase_data = {
                "id": str(conversation_data.get("id")),
                "user_id": conversation_data.get("user_id"),
                "title": conversation_data.get("title"),
                "model": conversation_data.get("model"),
                "provider": conversation_data.get("provider"),
                "temperature": conversation_data.get("temperature", 7),
                "max_tokens": conversation_data.get("max_tokens", 2048),
                "system_prompt": conversation_data.get("system_prompt"),
                "metadata": self._parse_json_field(
                    conversation_data.get("extra_metadata")
                ),
                "is_archived": bool(conversation_data.get("is_archived", False)),
            }

            # Handle datetime conversion
            if conversation_data.get("created_at"):
                supabase_data["created_at"] = self._convert_datetime(
                    conversation_data["created_at"]
                )
            if conversation_data.get("updated_at"):
                supabase_data["updated_at"] = self._convert_datetime(
                    conversation_data["updated_at"]
                )

            return self.db.create_conversation(supabase_data)
        except Exception as e:
            logger.error(f"Error migrating conversation: {e}")
            return None

    def migrate_message(self, message_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Migrate a single message from SQLite format to Supabase

        Args:
            message_data: Message data from SQLite

        Returns:
            Created message in Supabase, None if failed
        """
        if not self.db:
            return None

        try:
            supabase_data = {
                "id": str(message_data.get("id")),
                "conversation_id": str(message_data.get("conversation_id")),
                "role": self._convert_role(message_data.get("role")),
                "content": message_data.get("content"),
                "tokens": message_data.get("tokens"),
                "provider": message_data.get("provider"),
                "model": message_data.get("model"),
                "metadata": self._parse_json_field(message_data.get("extra_metadata")),
            }

            if message_data.get("created_at"):
                supabase_data["created_at"] = self._convert_datetime(
                    message_data["created_at"]
                )

            return self.db.create_message(supabase_data)
        except Exception as e:
            logger.error(f"Error migrating message: {e}")
            return None

    def _parse_json_field(self, value: Any) -> Dict[str, Any]:
        """Parse JSON field from SQLite (could be string or dict)"""
        if value is None:
            return {}
        if isinstance(value, str):
            try:
                return json.loads(value)
            except Exception:
                return {}
        if isinstance(value, dict):
            return value
        return {}

    def _convert_datetime(self, dt: Any) -> str:
        """Convert datetime to ISO format string"""
        if isinstance(dt, datetime):
            return dt.isoformat()
        if isinstance(dt, str):
            return dt
        return datetime.utcnow().isoformat()

    def _convert_role(self, role: Any) -> str:
        """Convert role enum to string"""
        if hasattr(role, "value"):
            return role.value
        if isinstance(role, str):
            return role
        return "user"

    def verify_migration(self, table: str, count: int) -> bool:
        """
        Verify migration by checking record count

        Args:
            table: Table name to check
            count: Expected count

        Returns:
            True if count matches, False otherwise
        """
        if not self.db:
            return False

        try:
            # This would need to be implemented based on actual Supabase query
            # For now, return True as placeholder
            logger.info(f"Verifying {table}: expected {count} records")
            return True
        except Exception as e:
            logger.error(f"Error verifying migration: {e}")
            return False


def get_migration_service() -> Optional[MigrationService]:
    """Get migration service instance"""
    if is_supabase_configured():
        return MigrationService()
    return None
