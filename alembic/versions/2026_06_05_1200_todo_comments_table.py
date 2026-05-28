"""todo_comments table

Revision ID: y1z2a3b4c5d6
Revises: n5o6p7q8r9s0
Create Date: 2026-06-05 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "y1z2a3b4c5d6"
down_revision: Union[str, None] = "n5o6p7q8r9s0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("todo_comments"):
        op.create_table(
            "todo_comments",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("task_id", sa.String(255), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_todo_comments_task_id", "todo_comments", ["task_id"], unique=False)
        op.create_index("ix_todo_comments_owner_id", "todo_comments", ["owner_id"], unique=False)


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if insp.has_table("todo_comments"):
        op.drop_index("ix_todo_comments_owner_id", table_name="todo_comments")
        op.drop_index("ix_todo_comments_task_id", table_name="todo_comments")
        op.drop_table("todo_comments")
