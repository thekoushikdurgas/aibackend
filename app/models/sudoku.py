"""
Sudoku database models for leaderboard scores and cloud save profiles.
"""

import uuid
from typing import Any, Dict

from sqlalchemy import Boolean, Column, DateTime, Integer, JSON, String

from app.models.metrics import Base
from app.utils.helpers import utc_now


class SudokuLeaderboardModel(Base):
    """Database model for storing Sudoku solve scores."""

    __tablename__ = "sudoku_leaderboard"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(255), index=True, nullable=True)
    player_name = Column(String(255), nullable=False)
    score = Column(Integer, nullable=False)
    difficulty = Column(String(64), nullable=False)
    time = Column(Integer, nullable=False)  # Solve duration in seconds
    is_daily = Column(Boolean, default=False, nullable=False)
    daily_date_str = Column(String(64), index=True, nullable=True)  # "YYYY-MM-DD"
    created_at = Column(DateTime, default=utc_now, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "player_name": self.player_name,
            "score": self.score,
            "difficulty": self.difficulty,
            "time": self.time,
            "is_daily": bool(self.is_daily),
            "daily_date_str": self.daily_date_str,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class SudokuProfileModel(Base):
    """Database model for storing Sudoku progression (cloud save/stats/achievements)."""

    __tablename__ = "sudoku_profile"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(255), unique=True, index=True, nullable=False)
    player_name = Column(String(255), nullable=False)

    # Single player stats
    single_player_solved = Column(Integer, default=0, nullable=False)
    single_player_total_time = Column(Integer, default=0, nullable=False)
    single_player_average_time = Column(Integer, default=0, nullable=False)
    single_player_best_time = Column(Integer, default=0, nullable=False)

    # Dicts mapping difficulty to counts/times
    by_difficulty = Column(JSON, default=dict, nullable=False)
    total_time_by_difficulty = Column(JSON, default=dict, nullable=False)

    # Multiplayer stats
    multiplayer_wins = Column(Integer, default=0, nullable=False)
    multiplayer_losses = Column(Integer, default=0, nullable=False)
    multiplayer_total_games = Column(Integer, default=0, nullable=False)

    # Achievements and recent scores list
    achievements = Column(JSON, default=list, nullable=False)
    recent_scores = Column(JSON, default=list, nullable=False)

    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "player_name": self.player_name,
            "singlePlayer": {
                "solved": self.single_player_solved,
                "totalTime": self.single_player_total_time,
                "averageTime": self.single_player_average_time,
                "bestTime": self.single_player_best_time,
                "byDifficulty": self.by_difficulty or {},
                "totalTimeByDifficulty": self.total_time_by_difficulty or {},
            },
            "multiplayer": {
                "wins": self.multiplayer_wins,
                "losses": self.multiplayer_losses,
                "totalGames": self.multiplayer_total_games,
            },
            "achievements": self.achievements or [],
            "recentScores": self.recent_scores or [],
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
