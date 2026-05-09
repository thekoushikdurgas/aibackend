"""
Migration script to migrate data from SQLite to Supabase
"""

import asyncio
import logging
import json
from datetime import datetime

from sqlalchemy import text

from app.database import AsyncSessionLocal
from app.database.supabase import get_supabase_db
from app.core.supabase_client import is_supabase_configured

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate_conversations():
    """Migrate conversations from SQLite to Supabase"""
    if not is_supabase_configured():
        logger.error("Supabase not configured")
        return

    db = get_supabase_db(use_admin=True)

    # Read from SQLite
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT * FROM conversations"))
        conversations = result.fetchall()

        logger.info(f"Found {len(conversations)} conversations to migrate")

        migrated = 0
        failed = 0

        for conv_row in conversations:
            try:
                # Convert row to dict
                conv_dict = dict(conv_row._mapping)

                # Convert to Supabase format
                supabase_conv = {
                    "id": str(conv_dict.get("id")),
                    "user_id": conv_dict.get("user_id"),
                    "title": conv_dict.get("title"),
                    "model": conv_dict.get("model"),
                    "provider": conv_dict.get("provider"),
                    "temperature": conv_dict.get("temperature"),
                    "max_tokens": conv_dict.get("max_tokens"),
                    "system_prompt": conv_dict.get("system_prompt"),
                    "metadata": (
                        json.loads(conv_dict.get("extra_metadata", "{}"))
                        if isinstance(conv_dict.get("extra_metadata"), str)
                        else (conv_dict.get("extra_metadata") or {})
                    ),
                    "is_archived": bool(conv_dict.get("is_archived", False)),
                    "created_at": (
                        conv_dict.get("created_at").isoformat()
                        if conv_dict.get("created_at")
                        else datetime.utcnow().isoformat()
                    ),
                    "updated_at": (
                        conv_dict.get("updated_at").isoformat()
                        if conv_dict.get("updated_at")
                        else datetime.utcnow().isoformat()
                    ),
                }

                # Create in Supabase
                created = db.create_conversation(supabase_conv)
                if created:
                    migrated += 1

                    # Migrate messages for this conversation
                    await migrate_messages(str(conv_dict.get("id")), session)
                else:
                    failed += 1
                    logger.warning(
                        f"Failed to migrate conversation {conv_dict.get('id')}"
                    )
            except Exception as e:
                failed += 1
                logger.error(f"Error migrating conversation: {e}")

        logger.info(f"Migrated {migrated} conversations, {failed} failed")


async def migrate_messages(conversation_id: str, session):
    """Migrate messages for a conversation"""
    db = get_supabase_db(use_admin=True)

    result = await session.execute(
        text("SELECT * FROM messages WHERE conversation_id = :conv_id"),
        {"conv_id": conversation_id},
    )
    messages = result.fetchall()

    for msg_row in messages:
        try:
            msg_dict = dict(msg_row._mapping)

            supabase_msg = {
                "id": str(msg_dict.get("id")),
                "conversation_id": str(msg_dict.get("conversation_id")),
                "role": (
                    msg_dict.get("role").value
                    if hasattr(msg_dict.get("role"), "value")
                    else str(msg_dict.get("role"))
                ),
                "content": msg_dict.get("content"),
                "tokens": msg_dict.get("tokens"),
                "provider": msg_dict.get("provider"),
                "model": msg_dict.get("model"),
                "metadata": (
                    json.loads(msg_dict.get("extra_metadata", "{}"))
                    if isinstance(msg_dict.get("extra_metadata"), str)
                    else (msg_dict.get("extra_metadata") or {})
                ),
                "created_at": (
                    msg_dict.get("created_at").isoformat()
                    if msg_dict.get("created_at")
                    else datetime.utcnow().isoformat()
                ),
            }

            db.create_message(supabase_msg)
        except Exception as e:
            logger.error(f"Error migrating message {msg_dict.get('id')}: {e}")


async def main():
    """Main migration function"""
    logger.info("Starting migration from SQLite to Supabase")

    if not is_supabase_configured():
        logger.error(
            "Supabase is not configured. Please set SUPABASE_URL and SUPABASE_ANON_KEY"
        )
        return

    try:
        await migrate_conversations()
        logger.info("Migration completed successfully")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
