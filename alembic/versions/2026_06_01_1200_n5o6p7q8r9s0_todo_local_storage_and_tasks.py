"""todo_workspaces storage + todo_tasks for local Kanban

Revision ID: n5o6p7q8r9s0
Revises: m4n5o6p7q8r9
Create Date: 2026-06-01 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision: str = "n5o6p7q8r9s0"
down_revision: Union[str, None] = "m4n5o6p7q8r9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    tw_cols = {c["name"] for c in insp.get_columns("todo_workspaces")}
    has_storage = "storage" in tw_cols
    has_tasks = insp.has_table("todo_tasks")

    if has_storage and has_tasks:
        return

    if not has_storage:
        op.drop_constraint(
            "uq_todo_workspaces_owner_google_name",
            "todo_workspaces",
            type_="unique",
        )

        op.add_column(
            "todo_workspaces",
            sa.Column("storage", sa.String(16), nullable=False, server_default="google"),
        )

        op.alter_column(
            "todo_workspaces",
            "backlog_list_id",
            existing_type=sa.String(255),
            nullable=True,
        )
        op.alter_column(
            "todo_workspaces",
            "todo_list_id",
            existing_type=sa.String(255),
            nullable=True,
        )
        op.alter_column(
            "todo_workspaces",
            "doing_list_id",
            existing_type=sa.String(255),
            nullable=True,
        )
        op.alter_column(
            "todo_workspaces",
            "done_list_id",
            existing_type=sa.String(255),
            nullable=True,
        )

        op.create_unique_constraint(
            "uq_todo_workspaces_owner_storage_google_name",
            "todo_workspaces",
            ["owner_id", "storage", "google_user_id", "name"],
        )

    if not has_tasks:
        op.create_table(
            "todo_tasks",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("workspace_id", sa.String(36), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("board_column", sa.String(32), nullable=False),
            sa.Column("title", sa.String(512), nullable=False),
            sa.Column("sort_order", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["workspace_id"],
                ["todo_workspaces.id"],
                ondelete="CASCADE",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_todo_tasks_workspace_column_sort",
            "todo_tasks",
            ["workspace_id", "board_column", "sort_order"],
            unique=False,
        )
        op.create_index("ix_todo_tasks_owner_id", "todo_tasks", ["owner_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    if insp.has_table("todo_tasks"):
        op.drop_index("ix_todo_tasks_owner_id", table_name="todo_tasks")
        op.drop_index("ix_todo_tasks_workspace_column_sort", table_name="todo_tasks")
        op.drop_table("todo_tasks")

    if not insp.has_table("todo_workspaces"):
        return

    cols = {c["name"] for c in insp.get_columns("todo_workspaces")}
    if "storage" not in cols:
        return

    bind.execute(text("DELETE FROM todo_workspaces WHERE storage = 'local'"))

    op.drop_constraint(
        "uq_todo_workspaces_owner_storage_google_name",
        "todo_workspaces",
        type_="unique",
    )

    bind.execute(
        text(
            """
            UPDATE todo_workspaces SET
                backlog_list_id = COALESCE(NULLIF(TRIM(backlog_list_id), ''), 'legacy'),
                todo_list_id = COALESCE(NULLIF(TRIM(todo_list_id), ''), 'legacy'),
                doing_list_id = COALESCE(NULLIF(TRIM(doing_list_id), ''), 'legacy'),
                done_list_id = COALESCE(NULLIF(TRIM(done_list_id), ''), 'legacy')
            """
        )
    )

    op.alter_column(
        "todo_workspaces",
        "backlog_list_id",
        existing_type=sa.String(255),
        nullable=False,
    )
    op.alter_column(
        "todo_workspaces",
        "todo_list_id",
        existing_type=sa.String(255),
        nullable=False,
    )
    op.alter_column(
        "todo_workspaces",
        "doing_list_id",
        existing_type=sa.String(255),
        nullable=False,
    )
    op.alter_column(
        "todo_workspaces",
        "done_list_id",
        existing_type=sa.String(255),
        nullable=False,
    )

    op.drop_column("todo_workspaces", "storage")

    op.create_unique_constraint(
        "uq_todo_workspaces_owner_google_name",
        "todo_workspaces",
        ["owner_id", "google_user_id", "name"],
    )
