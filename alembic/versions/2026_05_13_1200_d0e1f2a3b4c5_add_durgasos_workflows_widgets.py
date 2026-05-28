"""add workflow_definitions workflow_runs widget_layouts

Revision ID: d0e1f2a3b4c5
Revises: c7d8e9f0a1b2
Create Date: 2026-05-13 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("workflow_definitions"):
        op.create_table(
            "workflow_definitions",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("spec", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_workflow_definitions_owner_id", "workflow_definitions", ["owner_id"], unique=False
        )

    if not insp.has_table("workflow_runs"):
        op.create_table(
            "workflow_runs",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("workflow_id", sa.String(36), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=True),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("events", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_workflow_runs_workflow_id", "workflow_runs", ["workflow_id"], unique=False)
        op.create_index("ix_workflow_runs_owner_id", "workflow_runs", ["owner_id"], unique=False)

    if not insp.has_table("widget_layouts"):
        op.create_table(
            "widget_layouts",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("layout_json", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("owner_id", name="uq_widget_layouts_owner_id"),
        )


def downgrade() -> None:
    op.drop_table("widget_layouts")
    op.drop_table("workflow_runs")
    op.drop_table("workflow_definitions")
