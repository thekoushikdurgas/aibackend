"""add file_associations to durgasos_installed_apps

Revision ID: f1a2b3c4d5e6
Revises: e4f5a6b7c8d9
Create Date: 2026-05-16 14:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e4f5a6b7c8d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("durgasos_installed_apps"):
        return
    cols = {c["name"] for c in insp.get_columns("durgasos_installed_apps")}
    if "file_associations" not in cols:
        op.add_column(
            "durgasos_installed_apps",
            sa.Column("file_associations", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("durgasos_installed_apps"):
        return
    cols = {c["name"] for c in insp.get_columns("durgasos_installed_apps")}
    if "file_associations" in cols:
        op.drop_column("durgasos_installed_apps", "file_associations")
