"""dev_tool tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-29 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("dev_tool_memories"):
        op.create_table(
            "dev_tool_memories",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("type", sa.String(16), nullable=False),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_dev_tool_memories_owner_id", "dev_tool_memories", ["owner_id"]
        )
    if not insp.has_table("dev_tool_regex_history"):
        op.create_table(
            "dev_tool_regex_history",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("mode", sa.String(16), nullable=False),
            sa.Column("input", sa.Text(), nullable=False),
            sa.Column("regex", sa.Text(), nullable=True),
            sa.Column("explanation", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_dev_tool_regex_history_owner_id",
            "dev_tool_regex_history",
            ["owner_id"],
        )
    if not insp.has_table("dev_tool_icon_history"):
        op.create_table(
            "dev_tool_icon_history",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("source_storage_path", sa.String(2000), nullable=False),
            sa.Column("source_image_url", sa.String(2000), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_dev_tool_icon_history_owner_id",
            "dev_tool_icon_history",
            ["owner_id"],
        )


def downgrade() -> None:
    insp = inspect(op.get_bind())
    for table, idx in (
        ("dev_tool_icon_history", "ix_dev_tool_icon_history_owner_id"),
        ("dev_tool_regex_history", "ix_dev_tool_regex_history_owner_id"),
        ("dev_tool_memories", "ix_dev_tool_memories_owner_id"),
    ):
        if insp.has_table(table):
            op.drop_index(idx, table_name=table)
            op.drop_table(table)
