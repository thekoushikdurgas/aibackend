"""add todo_board_meta for DurgasOS Kanban Google Tasks list ids

Revision ID: j0k1l2m3n4o5
Revises: h8i9j0k1l2m3
Create Date: 2026-05-19 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "j0k1l2m3n4o5"
down_revision: Union[str, None] = "h8i9j0k1l2m3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("todo_board_meta"):
        op.create_table(
            "todo_board_meta",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("google_user_id", sa.String(255), nullable=False),
            sa.Column("backlog_list_id", sa.String(255), nullable=False),
            sa.Column("todo_list_id", sa.String(255), nullable=False),
            sa.Column("doing_list_id", sa.String(255), nullable=False),
            sa.Column("done_list_id", sa.String(255), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "owner_id",
                "google_user_id",
                name="uq_todo_board_meta_owner_google",
            ),
        )
        op.create_index(
            "ix_todo_board_meta_owner_id", "todo_board_meta", ["owner_id"], unique=False
        )
        op.create_index(
            "ix_todo_board_meta_google_user_id",
            "todo_board_meta",
            ["google_user_id"],
            unique=False,
        )


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if insp.has_table("todo_board_meta"):
        op.drop_table("todo_board_meta")
