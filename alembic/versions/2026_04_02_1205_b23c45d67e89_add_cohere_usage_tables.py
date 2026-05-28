"""add_cohere_usage_tables

Revision ID: b23c45d67e89
Revises: a12b34c56d78
Create Date: 2026-04-02 12:05:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "b23c45d67e89"
down_revision: Union[str, None] = "a12b34c56d78"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = inspect(op.get_bind())

    def has_table(name: str) -> bool:
        return inspect(op.get_bind()).has_table(name)

    if not insp.has_table("cohere_usage"):
        op.create_table(
            "cohere_usage",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("endpoint", sa.String(), nullable=False),
            sa.Column("model", sa.String(), nullable=False),
            sa.Column("input_tokens", sa.Integer(), nullable=True),
            sa.Column("output_tokens", sa.Integer(), nullable=True),
            sa.Column("total_tokens", sa.Integer(), nullable=True),
            sa.Column("request_id", sa.String(), nullable=True),
            sa.Column("success", sa.Boolean(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if has_table("cohere_usage"):
        op.create_index(
            "ix_cohere_usage_id", "cohere_usage", ["id"], unique=False, if_not_exists=True
        )
        op.create_index(
            "idx_cohere_usage_endpoint",
            "cohere_usage",
            ["endpoint"],
            unique=False,
            if_not_exists=True,
        )
        op.create_index(
            "idx_cohere_usage_model",
            "cohere_usage",
            ["model"],
            unique=False,
            if_not_exists=True,
        )
        op.create_index(
            "idx_cohere_usage_created_at",
            "cohere_usage",
            ["created_at"],
            unique=False,
            if_not_exists=True,
        )
        op.create_index(
            "idx_cohere_usage_success",
            "cohere_usage",
            ["success"],
            unique=False,
            if_not_exists=True,
        )

    if not insp.has_table("cohere_connector_logs"):
        op.create_table(
            "cohere_connector_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("connector_id", sa.String(), nullable=False),
            sa.Column("query", sa.Text(), nullable=False),
            sa.Column("documents_retrieved", sa.Integer(), nullable=True),
            sa.Column("success", sa.Boolean(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
    if has_table("cohere_connector_logs"):
        op.create_index(
            "ix_cohere_connector_logs_id",
            "cohere_connector_logs",
            ["id"],
            unique=False,
            if_not_exists=True,
        )
        op.create_index(
            "idx_cohere_connector_logs_connector_id",
            "cohere_connector_logs",
            ["connector_id"],
            unique=False,
            if_not_exists=True,
        )
        op.create_index(
            "idx_cohere_connector_logs_created_at",
            "cohere_connector_logs",
            ["created_at"],
            unique=False,
            if_not_exists=True,
        )
        op.create_index(
            "idx_cohere_connector_logs_success",
            "cohere_connector_logs",
            ["success"],
            unique=False,
            if_not_exists=True,
        )


def downgrade() -> None:
    op.drop_index(
        "idx_cohere_connector_logs_success",
        table_name="cohere_connector_logs",
        if_exists=True,
    )
    op.drop_index(
        "idx_cohere_connector_logs_created_at",
        table_name="cohere_connector_logs",
        if_exists=True,
    )
    op.drop_index(
        "idx_cohere_connector_logs_connector_id",
        table_name="cohere_connector_logs",
        if_exists=True,
    )
    op.drop_index(
        "ix_cohere_connector_logs_id",
        table_name="cohere_connector_logs",
        if_exists=True,
    )
    op.drop_table("cohere_connector_logs")
    op.drop_index(
        "idx_cohere_usage_success", table_name="cohere_usage", if_exists=True
    )
    op.drop_index(
        "idx_cohere_usage_created_at", table_name="cohere_usage", if_exists=True
    )
    op.drop_index(
        "idx_cohere_usage_model", table_name="cohere_usage", if_exists=True
    )
    op.drop_index(
        "idx_cohere_usage_endpoint", table_name="cohere_usage", if_exists=True
    )
    op.drop_index("ix_cohere_usage_id", table_name="cohere_usage", if_exists=True)
    op.drop_table("cohere_usage")
