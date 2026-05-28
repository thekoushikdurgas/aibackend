"""add scopes_granted to linked_google_accounts

Revision ID: h8i9j0k1l2m3
Revises: f1a2b3c4d5e6
Create Date: 2026-05-18 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "h8i9j0k1l2m3"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("linked_google_accounts"):
        return
    cols = {c["name"] for c in insp.get_columns("linked_google_accounts")}
    if "scopes_granted" not in cols:
        op.add_column(
            "linked_google_accounts",
            sa.Column("scopes_granted", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("linked_google_accounts"):
        return
    cols = {c["name"] for c in insp.get_columns("linked_google_accounts")}
    if "scopes_granted" in cols:
        op.drop_column("linked_google_accounts", "scopes_granted")
