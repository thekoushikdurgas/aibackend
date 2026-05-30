"""library tables (AuraBook)

Revision ID: a1b2c3d4e5f6
Revises: z7a8b9c0d1e2
Create Date: 2026-05-28 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "z7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table("library_books"):
        op.create_table(
            "library_books",
            sa.Column("id", sa.String(128), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("author", sa.String(200), nullable=False),
            sa.Column("isbn", sa.String(32), nullable=True),
            sa.Column("category", sa.String(100), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("cover_url", sa.String(2000), nullable=True),
            sa.Column("borrowing_status", sa.String(16), nullable=False),
            sa.Column("borrower", sa.String(200), nullable=True),
            sa.Column("borrow_date", sa.String(100), nullable=True),
            sa.Column("return_due_date", sa.String(100), nullable=True),
            sa.Column("pdf_attached", sa.Boolean(), nullable=False),
            sa.Column("pdf_storage_path", sa.String(2000), nullable=True),
            sa.Column("pdf_name", sa.String(500), nullable=True),
            sa.Column("pdf_content", sa.Text(), nullable=True),
            sa.Column("pages_total", sa.Integer(), nullable=False),
            sa.Column("pages_read", sa.Integer(), nullable=False),
            sa.Column("rating", sa.Float(), nullable=True),
            sa.Column("published_date", sa.String(100), nullable=True),
            sa.Column("author_info", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_library_books_owner_id", "library_books", ["owner_id"])

    if not insp.has_table("library_notes"):
        op.create_table(
            "library_notes",
            sa.Column("id", sa.String(128), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column("linked_book_ids", sa.JSON(), nullable=True),
            sa.Column("last_saved", sa.String(100), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_library_notes_owner_id", "library_notes", ["owner_id"])

    if not insp.has_table("library_devices"):
        op.create_table(
            "library_devices",
            sa.Column("id", sa.String(128), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("type", sa.String(16), nullable=False),
            sa.Column("last_sync", sa.String(100), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_library_devices_owner_id", "library_devices", ["owner_id"])

    if not insp.has_table("library_notifications"):
        op.create_table(
            "library_notifications",
            sa.Column("id", sa.String(128), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("message", sa.String(1000), nullable=False),
            sa.Column("type", sa.String(16), nullable=False),
            sa.Column("timestamp", sa.String(100), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_library_notifications_owner_id",
            "library_notifications",
            ["owner_id"],
        )


def downgrade() -> None:
    insp = inspect(op.get_bind())
    for table, indexes in (
        ("library_notifications", ["ix_library_notifications_owner_id"]),
        ("library_devices", ["ix_library_devices_owner_id"]),
        ("library_notes", ["ix_library_notes_owner_id"]),
        ("library_books", ["ix_library_books_owner_id"]),
    ):
        if insp.has_table(table):
            for idx in indexes:
                op.drop_index(idx, table_name=table)
            op.drop_table(table)
