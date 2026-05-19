"""add durgasos_installed_apps

Revision ID: e4f5a6b7c8d9
Revises: d0e1f2a3b4c5
Create Date: 2026-05-16 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "e4f5a6b7c8d9"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("durgasos_installed_apps"):
        op.create_table(
            "durgasos_installed_apps",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("app_ids", sa.JSON(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("owner_id", name="uq_durgasos_installed_apps_owner_id"),
        )


def downgrade() -> None:
    op.drop_table("durgasos_installed_apps")
