"""
Pokémon database models for leaderboard scores and cloud save profiles.
"""

import uuid
from typing import Any, Dict

from sqlalchemy import Column, DateTime, Integer, JSON, String

from app.models.metrics import Base
from app.utils.helpers import utc_now


class PokemonLeaderboardModel(Base):
    """Database model for storing Pokémon battle victories/scores."""

    __tablename__ = "pokemon_leaderboard"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(255), index=True, nullable=True)
    player_name = Column(String(255), nullable=False)
    score = Column(Integer, nullable=False)
    turns_taken = Column(Integer, nullable=False)
    remaining_hp = Column(Integer, nullable=False)
    difficulty = Column(
        String(64), nullable=False, default="Medium"
    )  # Medium, Hard, Custom AI
    created_at = Column(DateTime, default=utc_now, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "player_name": self.player_name,
            "score": self.score,
            "turns_taken": self.turns_taken,
            "remaining_hp": self.remaining_hp,
            "difficulty": self.difficulty,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PokemonProfileModel(Base):
    """Database model for storing user progression, custom generated teams, and stats."""

    __tablename__ = "pokemon_profile"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    owner_id = Column(String(255), unique=True, index=True, nullable=False)
    player_name = Column(String(255), nullable=False)

    # General Stats
    battles_total = Column(Integer, default=0, nullable=False)
    battles_won = Column(Integer, default=0, nullable=False)
    battles_lost = Column(Integer, default=0, nullable=False)
    current_streak = Column(Integer, default=0, nullable=False)
    highest_streak = Column(Integer, default=0, nullable=False)

    # Custom generated Pokémon details from Gemini
    custom_pokemon = Column(JSON, default=list, nullable=False)
    achievements = Column(JSON, default=list, nullable=False)

    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "owner_id": self.owner_id,
            "player_name": self.player_name,
            "stats": {
                "battlesTotal": self.battles_total,
                "battlesWon": self.battles_won,
                "battlesLost": self.battles_lost,
                "currentStreak": self.current_streak,
                "highestStreak": self.highest_streak,
            },
            "customPokemon": self.custom_pokemon or [],
            "achievements": self.achievements or [],
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
