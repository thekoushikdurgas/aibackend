"""todo_workspaces replaces todo_board_meta (multi-workspace Todo)

Revision ID: m4n5o6p7q8r9
Revises: j0k1l2m3n4o5
Create Date: 2026-05-20 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "m4n5o6p7q8r9"
down_revision: Union[str, None] = "j0k1l2m3n4o5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("todo_workspaces"):
        op.create_table(
            "todo_workspaces",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("google_user_id", sa.String(255), nullable=False),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("backlog_list_id", sa.String(255), nullable=False),
            sa.Column("todo_list_id", sa.String(255), nullable=False),
            sa.Column("doing_list_id", sa.String(255), nullable=False),
            sa.Column("done_list_id", sa.String(255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "owner_id",
                "google_user_id",
                "name",
                name="uq_todo_workspaces_owner_google_name",
            ),
        )
        op.create_index(
            "ix_todo_workspaces_owner_id", "todo_workspaces", ["owner_id"], unique=False
        )
        op.create_index(
            "ix_todo_workspaces_google_user_id",
            "todo_workspaces",
            ["google_user_id"],
            unique=False,
        )

    bind = op.get_bind()
    if insp.has_table("todo_board_meta") and insp.has_table("todo_workspaces"):
        cols = {c["name"] for c in insp.get_columns("todo_workspaces")}
        if "name" in cols:
            bind.execute(
                text(
                    """
                    INSERT INTO todo_workspaces (
                        id, owner_id, google_user_id, name,
                        backlog_list_id, todo_list_id, doing_list_id, done_list_id,
                        created_at, updated_at
                    )
                    SELECT
                        id, owner_id, google_user_id, 'Default',
                        backlog_list_id, todo_list_id, doing_list_id, done_list_id,
                        updated_at, updated_at
                    FROM todo_board_meta
                    WHERE NOT EXISTS (
                        SELECT 1 FROM todo_workspaces tw
                        WHERE tw.owner_id = todo_board_meta.owner_id
                          AND tw.google_user_id = todo_board_meta.google_user_id
                    )
                    """
                )
            )
        op.drop_table("todo_board_meta")


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("todo_workspaces"):
        return
    if insp.has_table("todo_board_meta"):
        return
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
            "owner_id", "google_user_id", name="uq_todo_board_meta_owner_google"
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
    bind = op.get_bind()
    if insp.has_table("todo_workspaces"):
        bind.execute(
            text(
                """
                INSERT INTO todo_board_meta (
                    id, owner_id, google_user_id,
                    backlog_list_id, todo_list_id, doing_list_id, done_list_id, updated_at
                )
                SELECT
                    id, owner_id, google_user_id,
                    backlog_list_id, todo_list_id, doing_list_id, done_list_id, updated_at
                FROM todo_workspaces
                WHERE name = 'Default'
                """
            )
        )
        op.drop_table("todo_workspaces")
