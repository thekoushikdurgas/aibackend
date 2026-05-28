"""
Road Rash database models for leaderboard scores, cloud save profiles, and friends.
"""

import uuid
from typing import Any, Dict

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String

from app.models.metrics import Base
from app.utils.helpers import utc_now


class RoadRashLeaderboardModel(Base):
    """Database model for storing individual race results."""

    __tablename__ = "roadrash_leaderboard"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(255), index=True, nullable=True)
    player_name = Column(String(255), nullable=False)
    track_name = Column(String(255), nullable=False)
    race_time = Column(Float, nullable=False)
    points = Column(Integer, nullable=False)
    rank = Column(Integer, nullable=False)
    medal = Column(String(16), nullable=True)
    season_week = Column(Integer, nullable=True, index=True)
    personal_best = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "player_name": self.player_name,
            "track_name": self.track_name,
            "race_time": self.race_time,
            "points": self.points,
            "rank": self.rank,
            "medal": self.medal,
            "season_week": self.season_week,
            "personal_best": bool(self.personal_best),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RoadRashProfileModel(Base):
    """Database model for storing user progression (cloud saves)."""

    __tablename__ = "roadrash_profile"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(255), unique=True, index=True, nullable=False)
    player_name = Column(String(255), nullable=False)
    money = Column(Integer, default=1000, nullable=False)
    current_bike = Column(String(64), default="Diablo", nullable=False)
    unlocked_bikes = Column(JSON, default=list, nullable=False)
    unlocked_tracks = Column(JSON, default=list, nullable=False)
    save_data = Column(JSON, default=dict, nullable=True)
    elo_score = Column(Integer, default=1000, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "player_name": self.player_name,
            "money": self.money,
            "current_bike": self.current_bike,
            "unlocked_bikes": self.unlocked_bikes or ["Diablo"],
            "unlocked_tracks": self.unlocked_tracks or ["mumbai"],
            "save_data": self.save_data or {},
            "elo_score": self.elo_score or 1000,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RoadRashFriendModel(Base):
    """Friend requests and accepted friendships between players."""

    __tablename__ = "roadrash_friends"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    requester_id = Column(String(255), index=True, nullable=False)
    addressee_id = Column(String(255), index=True, nullable=False)
    status = Column(String(32), default="pending", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "requester_id": self.requester_id,
            "addressee_id": self.addressee_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
