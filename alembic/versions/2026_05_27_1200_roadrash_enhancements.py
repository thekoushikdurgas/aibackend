"""roadrash enhancements: medals, friends, elo

Revision ID: z7a8b9c0d1e2
Revises: y1z2a3b4c5d6
Create Date: 2026-05-27 12:00:00.000000+00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "z7a8b9c0d1e2"
down_revision: Union[str, None] = "y1z2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    insp = inspect(op.get_bind())
    if not insp.has_table(table):
        return
    existing = {c["name"] for c in insp.get_columns(table)}
    if column.name not in existing:
        op.add_column(table, column)


def upgrade() -> None:
    insp = inspect(op.get_bind())

    if not insp.has_table("roadrash_leaderboard"):
        op.create_table(
            "roadrash_leaderboard",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=True),
            sa.Column("player_name", sa.String(255), nullable=False),
            sa.Column("track_name", sa.String(255), nullable=False),
            sa.Column("race_time", sa.Float(), nullable=False),
            sa.Column("points", sa.Integer(), nullable=False),
            sa.Column("rank", sa.Integer(), nullable=False),
            sa.Column("medal", sa.String(16), nullable=True),
            sa.Column("season_week", sa.Integer(), nullable=True),
            sa.Column("personal_best", sa.Boolean(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_roadrash_leaderboard_owner_id", "roadrash_leaderboard", ["owner_id"])
        op.create_index(
            "ix_roadrash_leaderboard_season_week", "roadrash_leaderboard", ["season_week"]
        )
    else:
        _add_column_if_missing("roadrash_leaderboard", sa.Column("medal", sa.String(16), nullable=True))
        _add_column_if_missing(
            "roadrash_leaderboard", sa.Column("season_week", sa.Integer(), nullable=True)
        )
        _add_column_if_missing(
            "roadrash_leaderboard",
            sa.Column("personal_best", sa.Boolean(), nullable=False, server_default="0"),
        )

    if not insp.has_table("roadrash_profile"):
        op.create_table(
            "roadrash_profile",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("owner_id", sa.String(255), nullable=False),
            sa.Column("player_name", sa.String(255), nullable=False),
            sa.Column("money", sa.Integer(), nullable=False, server_default="1000"),
            sa.Column("current_bike", sa.String(64), nullable=False, server_default="Diablo"),
            sa.Column("unlocked_bikes", sa.JSON(), nullable=False),
            sa.Column("unlocked_tracks", sa.JSON(), nullable=False),
            sa.Column("save_data", sa.JSON(), nullable=True),
            sa.Column("elo_score", sa.Integer(), nullable=False, server_default="1000"),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("owner_id", name="uq_roadrash_profile_owner_id"),
        )
    else:
        _add_column_if_missing(
            "roadrash_profile",
            sa.Column("elo_score", sa.Integer(), nullable=False, server_default="1000"),
        )

    if not insp.has_table("roadrash_friends"):
        op.create_table(
            "roadrash_friends",
            sa.Column("id", sa.String(36), nullable=False),
            sa.Column("requester_id", sa.String(255), nullable=False),
            sa.Column("addressee_id", sa.String(255), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_roadrash_friends_requester_id", "roadrash_friends", ["requester_id"])
        op.create_index("ix_roadrash_friends_addressee_id", "roadrash_friends", ["addressee_id"])


def downgrade() -> None:
    insp = inspect(op.get_bind())
    if insp.has_table("roadrash_friends"):
        op.drop_table("roadrash_friends")
    if insp.has_table("roadrash_profile"):
        for col in ("elo_score",):
            existing = {c["name"] for c in insp.get_columns("roadrash_profile")}
            if col in existing:
                op.drop_column("roadrash_profile", col)
    if insp.has_table("roadrash_leaderboard"):
        for col in ("medal", "season_week", "personal_best"):
            existing = {c["name"] for c in insp.get_columns("roadrash_leaderboard")}
            if col in existing:
                op.drop_column("roadrash_leaderboard", col)
