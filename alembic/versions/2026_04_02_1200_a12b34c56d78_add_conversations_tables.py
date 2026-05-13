"""add_conversations_tables

Revision ID: a12b34c56d78
Revises: 1e3305a06ba4
Create Date: 2026-04-02 12:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text


# revision identifiers, used by Alembic.
revision: str = "a12b34c56d78"
down_revision: Union[str, None] = "1e3305a06ba4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = inspect(op.get_bind())

    def has_table(name: str) -> bool:
        return inspect(op.get_bind()).has_table(name)

    if not insp.has_table("conversations"):
        op.create_table(
            "conversations",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("user_id", sa.String(), nullable=True),
            sa.Column("title", sa.String(length=500), nullable=True),
            sa.Column("model", sa.String(length=100), nullable=True),
            sa.Column("provider", sa.String(length=50), nullable=True),
            sa.Column("temperature", sa.Integer(), nullable=True),
            sa.Column("max_tokens", sa.Integer(), nullable=True),
            sa.Column("system_prompt", sa.Text(), nullable=True),
            sa.Column("extra_metadata", sa.JSON(), nullable=True),
            sa.Column("is_archived", sa.Boolean(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )
    if has_table("conversations"):
        op.create_index(
            "ix_conversations_user_id",
            "conversations",
            ["user_id"],
            unique=False,
            if_not_exists=True,
        )
        op.create_index(
            "ix_conversations_created_at",
            "conversations",
            ["created_at"],
            unique=False,
            if_not_exists=True,
        )
        op.create_index(
            "idx_conversations_user_updated",
            "conversations",
            ["user_id", "updated_at"],
            unique=False,
            if_not_exists=True,
        )

    if not insp.has_table("messages"):
        op.execute(
            text(
                """
DO $$ BEGIN
    CREATE TYPE messagerole AS ENUM ('USER', 'ASSISTANT', 'SYSTEM');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;
"""
            )
        )
        op.create_table(
            "messages",
            sa.Column("id", sa.String(), nullable=False),
            sa.Column("conversation_id", sa.String(), nullable=False),
            sa.Column(
                "role",
                sa.Enum(
                    "USER",
                    "ASSISTANT",
                    "SYSTEM",
                    name="messagerole",
                    create_type=False,
                ),
                nullable=False,
            ),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("tokens", sa.Integer(), nullable=True),
            sa.Column("provider", sa.String(length=50), nullable=True),
            sa.Column("model", sa.String(length=100), nullable=True),
            sa.Column("extra_metadata", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    if has_table("messages"):
        op.create_index(
            "ix_messages_conversation_id",
            "messages",
            ["conversation_id"],
            unique=False,
            if_not_exists=True,
        )
        op.create_index(
            "ix_messages_created_at",
            "messages",
            ["created_at"],
            unique=False,
            if_not_exists=True,
        )


def downgrade() -> None:
    op.drop_index(
        "ix_messages_created_at", table_name="messages", if_exists=True
    )
    op.drop_index(
        "ix_messages_conversation_id", table_name="messages", if_exists=True
    )
    op.drop_table("messages")
    op.drop_index(
        "idx_conversations_user_updated", table_name="conversations", if_exists=True
    )
    op.drop_index(
        "ix_conversations_created_at", table_name="conversations", if_exists=True
    )
    op.drop_index(
        "ix_conversations_user_id", table_name="conversations", if_exists=True
    )
    op.drop_table("conversations")
    op.execute("DROP TYPE IF EXISTS messagerole")
