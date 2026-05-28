"""
Road Rash WebSocket JSON-RPC 2.0 Method Handlers
"""

import logging
import statistics
import time
import hmac
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, or_, select, update

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.core.ws_auth import require_auth
from app.database.sqlalchemy import AsyncSessionLocal
from app.models.roadrash import (
    RoadRashFriendModel,
    RoadRashLeaderboardModel,
    RoadRashProfileModel,
)
from app.core.connection_manager import connection_manager

logger = logging.getLogger(__name__)

SECRET_KEY = b"roadrash_durgasos_secret_salt_2026"

MEDAL_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "mumbai": {"gold": 45.0, "silver": 60.0, "bronze": 80.0},
    "delhi": {"gold": 60.0, "silver": 80.0, "bronze": 100.0},
    "goa": {"gold": 80.0, "silver": 100.0, "bronze": 130.0},
}

TRACK_DISTANCES: Dict[str, float] = {
    "mumbai": 5000.0,
    "delhi": 7500.0,
    "goa": 10000.0,
}

MIN_POSSIBLE_TIMES: Dict[str, float] = {
    "mumbai": 35.0,
    "delhi": 45.0,
    "goa": 30.0,
}

BIKE_MAX_SPEEDS: Dict[str, float] = {
    "Diablo": 180.0,
    "Pulsar 220": 230.0,
    "Bullet 350": 210.0,
    "Splendor Pro": 260.0,
    "Hayabusa": 320.0,
}

# Matchmaking state in-memory
matchmaking_queue: List[Dict[str, Any]] = []
active_lobbies: Dict[str, Dict[str, Any]] = {}
recent_submissions: Dict[str, List[float]] = {}
weather_reports: Dict[str, Dict[str, Any]] = {}


def _current_season_week() -> int:
    return datetime.now(timezone.utc).isocalendar()[1]


def _compute_medal(track_key: str, race_time: float) -> Optional[str]:
    thresholds = MEDAL_THRESHOLDS.get(track_key, MEDAL_THRESHOLDS["mumbai"])
    if race_time <= thresholds["gold"]:
        return "gold"
    if race_time <= thresholds["silver"]:
        return "silver"
    if race_time <= thresholds["bronze"]:
        return "bronze"
    return None


def _compute_elo_from_time(track_key: str, race_time: float) -> int:
    """Lower race time => higher ELO. Baseline 1000 at bronze threshold."""
    thresholds = MEDAL_THRESHOLDS.get(track_key, MEDAL_THRESHOLDS["mumbai"])
    bronze = thresholds["bronze"]
    gold = thresholds["gold"]
    if race_time <= gold:
        return 1400
    if race_time <= thresholds["silver"]:
        return 1250
    if race_time <= bronze:
        return 1100
    return max(800, int(1000 - (race_time - bronze) * 5))


def _elo_window_for_wait(wait_seconds: float) -> int:
    if wait_seconds >= 30:
        return 9999
    if wait_seconds >= 10:
        return 300
    return 150


def _find_match_candidate(entry: Dict[str, Any], window: int) -> Optional[int]:
    my_elo = entry.get("elo_score", 1000)
    for idx, other in enumerate(matchmaking_queue):
        if other["connection_id"] == entry["connection_id"]:
            continue
        other_elo = other.get("elo_score", 1000)
        if abs(other_elo - my_elo) <= window:
            return idx
    return None


async def handle_roadrash_profile_get(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = await require_auth(user, "roadrash.profile.get")
    user_id = user.get("sub") or user.get("id")

    async with AsyncSessionLocal() as session:
        stmt = select(RoadRashProfileModel).where(
            RoadRashProfileModel.owner_id == user_id
        )
        result = await session.execute(stmt)
        profile = result.scalars().first()

        if not profile:
            profile = RoadRashProfileModel(
                owner_id=user_id,
                player_name=user.get("email", "Rider").split("@")[0],
                money=1000,
                current_bike="Diablo",
                unlocked_bikes=["Diablo"],
                unlocked_tracks=["mumbai"],
                save_data={},
                elo_score=1000,
            )
            session.add(profile)
            await session.commit()
            await session.refresh(profile)

        return profile.to_dict()


async def handle_roadrash_profile_save(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = await require_auth(user, "roadrash.profile.save")
    user_id = user.get("sub") or user.get("id")

    async with AsyncSessionLocal() as session:
        stmt = select(RoadRashProfileModel).where(
            RoadRashProfileModel.owner_id == user_id
        )
        result = await session.execute(stmt)
        profile = result.scalars().first()

        if not profile:
            profile = RoadRashProfileModel(
                owner_id=user_id,
                player_name=params.get("player_name", "Rider"),
            )
            session.add(profile)

        if "player_name" in params:
            profile.player_name = params["player_name"]
        if "money" in params:
            profile.money = params["money"]
        if "current_bike" in params:
            profile.current_bike = params["current_bike"]
        if "unlocked_bikes" in params:
            profile.unlocked_bikes = params["unlocked_bikes"]
        if "unlocked_tracks" in params:
            profile.unlocked_tracks = params["unlocked_tracks"]
        if "save_data" in params:
            setattr(profile, "save_data", params["save_data"])
        if "elo_score" in params:
            setattr(profile, "elo_score", params["elo_score"])

        await session.commit()
        await session.refresh(profile)
        return profile.to_dict()


def _rate_limit_ok(user_id: str) -> bool:
    now = time.time()
    history = recent_submissions.get(user_id, [])
    history = [t for t in history if now - t < 3600]
    recent_submissions[user_id] = history
    return len(history) < 3


def _record_submission(user_id: str) -> None:
    recent_submissions.setdefault(user_id, []).append(time.time())


def _validate_replay_token(
    race_time: float, track_key: str, samples: Optional[List[float]]
) -> bool:
    if not samples or len(samples) < 2:
        return True
    total_z = max(samples) - min(samples)
    if total_z <= 0:
        return False
    avg_velocity = total_z / race_time
    max_bike = max(BIKE_MAX_SPEEDS.values()) / 3.6
    return avg_velocity <= max_bike * 55 * 1.15


async def handle_roadrash_leaderboard_submit(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user_id = str(user.get("sub") or user.get("id") if user else "anonymous")

    player_name = params.get("player_name", "Anonymous")
    track_name = params.get("track_name", "Mumbai")
    race_time = float(params.get("race_time", 0.0))
    points = int(params.get("points", 0))
    rank = int(params.get("rank", 1))
    hash_val = params.get("hash", "")
    bike_name = params.get("bike", "Diablo")
    replay_samples = params.get("replay_samples")

    track_key = track_name.lower()

    if track_key in MIN_POSSIBLE_TIMES and race_time < MIN_POSSIBLE_TIMES[track_key]:
        logger.warning(
            "Anti-cheat: race_time %s too low for track %s by user %s",
            race_time,
            track_name,
            user_id,
        )
        return {"success": False, "reason": "Cheat detected: invalid race time"}

    if not _rate_limit_ok(user_id):
        return {"success": False, "reason": "Rate limit: max 3 submissions per hour"}

    message = f"{user_id}:{track_name}:{race_time:.2f}:{points}".encode()
    expected_hash = hmac.new(SECRET_KEY, message, hashlib.sha256).hexdigest()
    if hash_val != expected_hash:
        alt_message = f"{user_id}:{track_name}:{race_time}:{points}".encode()
        alt_expected_hash = hmac.new(
            SECRET_KEY, alt_message, hashlib.sha256
        ).hexdigest()
        if hash_val != alt_expected_hash:
            return {"success": False, "reason": "Cheat detected: signature mismatch"}

    track_distance = TRACK_DISTANCES.get(track_key, 5000.0)
    bike_max = BIKE_MAX_SPEEDS.get(bike_name, BIKE_MAX_SPEEDS["Diablo"])
    if race_time > 0:
        avg_speed_kmh = (track_distance / race_time) * 3.6
        if avg_speed_kmh > bike_max * 1.05:
            return {"success": False, "reason": "Cheat detected: impossible speed"}

    if not _validate_replay_token(race_time, track_key, replay_samples):
        return {"success": False, "reason": "Cheat detected: replay mismatch"}

    medal = _compute_medal(track_key, race_time)
    season_week = _current_season_week()

    async with AsyncSessionLocal() as session:
        top_stmt = (
            select(RoadRashLeaderboardModel.race_time)
            .where(RoadRashLeaderboardModel.track_name == track_name)
            .order_by(RoadRashLeaderboardModel.race_time.asc())
            .limit(10)
        )
        top_result = await session.execute(top_stmt)
        top_times = [row[0] for row in top_result.all()]
        if len(top_times) >= 3:
            mean = statistics.mean(top_times)
            stdev = statistics.stdev(top_times) if len(top_times) > 1 else 0.0
            if stdev > 0 and race_time < mean - 3 * stdev:
                prof_stmt = select(RoadRashProfileModel).where(
                    RoadRashProfileModel.owner_id == user_id
                )
                prof_result = await session.execute(prof_stmt)
                prof = prof_result.scalars().first()
                if prof:
                    existing_save = prof.save_data
                    save: Dict[str, Any] = (
                        dict(existing_save) if isinstance(existing_save, dict) else {}
                    )
                    save["flagged"] = True
                    save["flag_reason"] = "outlier_time"
                    setattr(prof, "save_data", save)

        await session.execute(
            update(RoadRashLeaderboardModel)
            .where(
                and_(
                    RoadRashLeaderboardModel.owner_id == user_id,
                    RoadRashLeaderboardModel.track_name == track_name,
                    RoadRashLeaderboardModel.personal_best.is_(True),
                )
            )
            .values(personal_best=False)
        )

        best_stmt = (
            select(RoadRashLeaderboardModel)
            .where(
                and_(
                    RoadRashLeaderboardModel.owner_id == user_id,
                    RoadRashLeaderboardModel.track_name == track_name,
                )
            )
            .order_by(RoadRashLeaderboardModel.race_time.asc())
            .limit(1)
        )
        best_result = await session.execute(best_stmt)
        previous_best = best_result.scalars().first()
        is_personal_best = previous_best is None or race_time < previous_best.race_time

        score = RoadRashLeaderboardModel(
            owner_id=user_id,
            player_name=player_name,
            track_name=track_name,
            race_time=race_time,
            points=points,
            rank=rank,
            medal=medal,
            season_week=season_week,
            personal_best=is_personal_best,
        )
        session.add(score)

        prof_stmt = select(RoadRashProfileModel).where(
            RoadRashProfileModel.owner_id == user_id
        )
        prof_result = await session.execute(prof_stmt)
        prof = prof_result.scalars().first()
        if prof:
            setattr(
                prof,
                "elo_score",
                _compute_elo_from_time(track_key, race_time),
            )

        await session.commit()
        _record_submission(user_id)
        return {
            "success": True,
            "medal": medal,
            "personal_best": is_personal_best,
            "season_week": season_week,
        }


async def handle_roadrash_leaderboard_get(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    track_name = params.get("track_name", "Mumbai")

    async with AsyncSessionLocal() as session:
        stmt = (
            select(RoadRashLeaderboardModel)
            .where(RoadRashLeaderboardModel.track_name == track_name)
            .order_by(RoadRashLeaderboardModel.race_time.asc())
            .limit(50)
        )
        result = await session.execute(stmt)
        scores = result.scalars().all()
        return {"scores": [s.to_dict() for s in scores]}


async def handle_roadrash_leaderboard_personal_best(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = await require_auth(user, "roadrash.leaderboard.personal_best")
    user_id = user.get("sub") or user.get("id")
    track_name = params.get("track_name")

    async with AsyncSessionLocal() as session:
        stmt = select(RoadRashLeaderboardModel).where(
            and_(
                RoadRashLeaderboardModel.owner_id == user_id,
                RoadRashLeaderboardModel.personal_best.is_(True),
            )
        )
        if track_name:
            stmt = stmt.where(RoadRashLeaderboardModel.track_name == track_name)
        result = await session.execute(stmt)
        scores = result.scalars().all()
        return {"scores": [s.to_dict() for s in scores]}


async def handle_roadrash_leaderboard_friends(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = await require_auth(user, "roadrash.leaderboard.friends")
    user_id = user.get("sub") or user.get("id")
    track_name = params.get("track_name", "Mumbai")

    async with AsyncSessionLocal() as session:
        friend_stmt = select(RoadRashFriendModel).where(
            and_(
                RoadRashFriendModel.status == "accepted",
                or_(
                    RoadRashFriendModel.requester_id == user_id,
                    RoadRashFriendModel.addressee_id == user_id,
                ),
            )
        )
        friend_result = await session.execute(friend_stmt)
        friend_ids = {user_id}
        for f in friend_result.scalars().all():
            if f.requester_id == user_id:
                friend_ids.add(f.addressee_id)
            else:
                friend_ids.add(f.requester_id)

        stmt = (
            select(RoadRashLeaderboardModel)
            .where(
                and_(
                    RoadRashLeaderboardModel.track_name == track_name,
                    RoadRashLeaderboardModel.owner_id.in_(list(friend_ids)),
                )
            )
            .order_by(RoadRashLeaderboardModel.race_time.asc())
            .limit(50)
        )
        result = await session.execute(stmt)
        return {"scores": [s.to_dict() for s in result.scalars().all()]}


async def handle_roadrash_leaderboard_season(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    track_name = params.get("track_name", "Mumbai")
    season_week = params.get("season_week", _current_season_week())

    async with AsyncSessionLocal() as session:
        stmt = (
            select(RoadRashLeaderboardModel)
            .where(
                and_(
                    RoadRashLeaderboardModel.track_name == track_name,
                    RoadRashLeaderboardModel.season_week == season_week,
                )
            )
            .order_by(RoadRashLeaderboardModel.race_time.asc())
            .limit(50)
        )
        result = await session.execute(stmt)
        return {
            "season_week": season_week,
            "scores": [s.to_dict() for s in result.scalars().all()],
        }


async def handle_roadrash_friends_add(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = await require_auth(user, "roadrash.friends.add")
    user_id = user.get("sub") or user.get("id")
    target_name = params.get("player_name", "").strip()
    if not target_name:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "player_name required")

    async with AsyncSessionLocal() as session:
        target_stmt = select(RoadRashProfileModel).where(
            RoadRashProfileModel.player_name == target_name
        )
        target_result = await session.execute(target_stmt)
        target = target_result.scalars().first()
        if not target:
            return {"success": False, "reason": "Player not found"}
        if target.owner_id == user_id:
            return {"success": False, "reason": "Cannot add yourself"}

        existing_stmt = select(RoadRashFriendModel).where(
            or_(
                and_(
                    RoadRashFriendModel.requester_id == user_id,
                    RoadRashFriendModel.addressee_id == target.owner_id,
                ),
                and_(
                    RoadRashFriendModel.requester_id == target.owner_id,
                    RoadRashFriendModel.addressee_id == user_id,
                ),
            )
        )
        existing_result = await session.execute(existing_stmt)
        if existing_result.scalars().first():
            return {"success": False, "reason": "Request already exists"}

        req = RoadRashFriendModel(
            requester_id=user_id,
            addressee_id=target.owner_id,
            status="pending",
        )
        session.add(req)
        await session.commit()
        return {"success": True, "request": req.to_dict()}


async def handle_roadrash_friends_accept(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = await require_auth(user, "roadrash.friends.accept")
    user_id = user.get("sub") or user.get("id")
    request_id = params.get("request_id")
    if not request_id:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "request_id required")

    async with AsyncSessionLocal() as session:
        stmt = select(RoadRashFriendModel).where(RoadRashFriendModel.id == request_id)
        result = await session.execute(stmt)
        req = result.scalars().first()
        if not req or req.addressee_id != user_id:
            return {"success": False, "reason": "Request not found"}
        setattr(req, "status", "accepted")
        await session.commit()
        return {"success": True, "friend": req.to_dict()}


async def handle_roadrash_friends_list(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = await require_auth(user, "roadrash.friends.list")
    user_id = user.get("sub") or user.get("id")
    track_name = params.get("track_name", "Mumbai")

    async with AsyncSessionLocal() as session:
        stmt = select(RoadRashFriendModel).where(
            and_(
                RoadRashFriendModel.status == "accepted",
                or_(
                    RoadRashFriendModel.requester_id == user_id,
                    RoadRashFriendModel.addressee_id == user_id,
                ),
            )
        )
        result = await session.execute(stmt)
        friends_out: List[Dict[str, Any]] = []
        pending_out: List[Dict[str, Any]] = []

        pending_stmt = select(RoadRashFriendModel).where(
            and_(
                RoadRashFriendModel.status == "pending",
                RoadRashFriendModel.addressee_id == user_id,
            )
        )
        pending_result = await session.execute(pending_stmt)
        for p in pending_result.scalars().all():
            prof_stmt = select(RoadRashProfileModel).where(
                RoadRashProfileModel.owner_id == p.requester_id
            )
            prof = (await session.execute(prof_stmt)).scalars().first()
            pending_out.append(
                {
                    **p.to_dict(),
                    "player_name": prof.player_name if prof else "Unknown",
                }
            )

        for f in result.scalars().all():
            friend_id = f.addressee_id if f.requester_id == user_id else f.requester_id
            prof_stmt = select(RoadRashProfileModel).where(
                RoadRashProfileModel.owner_id == friend_id
            )
            prof = (await session.execute(prof_stmt)).scalars().first()
            best_stmt = (
                select(RoadRashLeaderboardModel)
                .where(
                    and_(
                        RoadRashLeaderboardModel.owner_id == friend_id,
                        RoadRashLeaderboardModel.track_name == track_name,
                        RoadRashLeaderboardModel.personal_best.is_(True),
                    )
                )
                .limit(1)
            )
            best = (await session.execute(best_stmt)).scalars().first()
            friends_out.append(
                {
                    "friend_id": friend_id,
                    "player_name": prof.player_name if prof else "Unknown",
                    "elo_score": prof.elo_score if prof else 1000,
                    "best_time": best.race_time if best else None,
                    "best_medal": best.medal if best else None,
                }
            )

        return {"friends": friends_out, "pending": pending_out}


async def handle_roadrash_friends_challenge(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = await require_auth(user, "roadrash.friends.challenge")
    user_id = user.get("sub") or user.get("id")
    friend_id = params.get("friend_id")
    track_name = params.get("track_name", "mumbai")
    if not friend_id:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "friend_id required")

    async with AsyncSessionLocal() as session:
        prof_stmt = select(RoadRashProfileModel).where(
            RoadRashProfileModel.owner_id == user_id
        )
        prof = (await session.execute(prof_stmt)).scalars().first()
        challenger_name = prof.player_name if prof else "Rider"

    for conn_id in connection_manager.active_connections:
        conn_user = connection_manager.get_user(conn_id)
        if conn_user and (conn_user.get("sub") or conn_user.get("id")) == friend_id:
            await connection_manager.send_json(
                conn_id,
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "result": {
                        "type": "roadrash.friends.challenge",
                        "challenger_id": user_id,
                        "challenger_name": challenger_name,
                        "track_name": track_name,
                    },
                },
            )
            return {"success": True}

    return {"success": False, "reason": "Friend is offline"}


async def handle_roadrash_weather_report(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user_id = str(user.get("sub") or user.get("id") if user else "anonymous")
    weather_reports[user_id] = {
        "weather": params.get("weather"),
        "track": params.get("track_name"),
        "timestamp": time.time(),
    }
    return {"success": True}


async def _create_lobby(
    p1: Dict[str, Any], p2: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    lobby_id = f"lobby_{int(time.time())}_{p1['connection_id'][:8]}"
    lobby_data = {
        "players": [p1["connection_id"], p2["connection_id"]],
        "ready": {},
        "started_at": None,
        "state_snapshot": None,
        "track": p1.get("track", "mumbai"),
    }
    active_lobbies[lobby_id] = lobby_data
    return lobby_id, lobby_data


async def _notify_match(
    p1: Dict[str, Any],
    p2: Dict[str, Any],
    lobby_id: str,
    needs_ready: bool = True,
) -> None:
    for player, opponent in ((p1, p2), (p2, p1)):
        await connection_manager.send_json(
            player["connection_id"],
            {
                "jsonrpc": "2.0",
                "id": None,
                "result": {
                    "type": "roadrash.matchmaking.matched",
                    "lobby_id": lobby_id,
                    "opponent_connection_id": opponent["connection_id"],
                    "opponent": {
                        "player_name": opponent["player_name"],
                        "bike": opponent["bike"],
                    },
                    "needs_ready": needs_ready,
                },
            },
        )


async def handle_roadrash_matchmaking_join(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not connection_id:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "connection_id is required")

    global matchmaking_queue
    player_name = params.get("player_name", "Rider")
    bike = params.get("bike", "Diablo")
    track = params.get("track", "mumbai")
    elo_score = int(params.get("elo_score", 1000))

    matchmaking_queue = [
        item for item in matchmaking_queue if item["connection_id"] != connection_id
    ]

    entry = {
        "connection_id": connection_id,
        "user_id": user.get("sub") if user else "anonymous",
        "player_name": player_name,
        "bike": bike,
        "track": track,
        "elo_score": elo_score,
        "joined_at": time.time(),
    }
    matchmaking_queue.append(entry)

    wait_seconds = 0.0
    candidate_idx = _find_match_candidate(entry, _elo_window_for_wait(wait_seconds))
    if candidate_idx is not None:
        opponent = matchmaking_queue.pop(candidate_idx)
        matchmaking_queue = [
            item for item in matchmaking_queue if item["connection_id"] != connection_id
        ]
        lobby_id, _ = await _create_lobby(entry, opponent)
        await _notify_match(entry, opponent, lobby_id)
        return {"status": "matched", "lobby_id": lobby_id, "needs_ready": True}

    queued_entry = next(
        (q for q in matchmaking_queue if q["connection_id"] == connection_id), None
    )
    if queued_entry:
        wait_seconds = time.time() - queued_entry["joined_at"]
        window = _elo_window_for_wait(wait_seconds)
        match_idx = _find_match_candidate(queued_entry, window)
        if match_idx is not None:
            opponent = matchmaking_queue.pop(match_idx)
            matchmaking_queue = [
                item
                for item in matchmaking_queue
                if item["connection_id"] != connection_id
            ]
            lobby_id, _ = await _create_lobby(queued_entry, opponent)
            await _notify_match(queued_entry, opponent, lobby_id)
            return {"status": "matched", "lobby_id": lobby_id, "needs_ready": True}

    return {"status": "queued", "queue_length": len(matchmaking_queue)}


async def handle_roadrash_matchmaking_ready(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    lobby_id = params.get("lobby_id")
    if not lobby_id or lobby_id not in active_lobbies:
        return {"success": False, "reason": "Lobby not found"}

    lobby = active_lobbies[lobby_id]
    if connection_id:
        lobby["ready"][connection_id] = time.time()

    if len(lobby["ready"]) >= 2:
        lobby["started_at"] = time.time()
        for pid in lobby["players"]:
            await connection_manager.send_json(
                pid,
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "result": {
                        "type": "roadrash.matchmaking.start",
                        "lobby_id": lobby_id,
                        "track": lobby.get("track", "mumbai"),
                    },
                },
            )
        return {"success": True, "status": "starting"}

    return {
        "success": True,
        "status": "waiting_ready",
        "ready_count": len(lobby["ready"]),
    }


async def handle_roadrash_game_sync(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    lobby_id = params.get("lobby_id")
    opponent_id = params.get("opponent_connection_id")

    if lobby_id and lobby_id in active_lobbies:
        lobby = active_lobbies[lobby_id]
        lobby["state_snapshot"] = {
            "position": params.get("position"),
            "offset": params.get("offset"),
            "speed": params.get("speed"),
            "action": params.get("action"),
            "from": connection_id,
            "timestamp": time.time(),
        }

    if not opponent_id and lobby_id in active_lobbies:
        players = active_lobbies[lobby_id]["players"]
        for p in players:
            if p != connection_id:
                opponent_id = p
                break

    if opponent_id:
        await connection_manager.send_json(
            opponent_id,
            {
                "jsonrpc": "2.0",
                "id": None,
                "result": {
                    "type": "roadrash.game.opponent_sync",
                    "position": params.get("position"),
                    "offset": params.get("offset"),
                    "speed": params.get("speed"),
                    "action": params.get("action"),
                },
            },
        )
        return {"success": True}

    return {"success": False, "error": "Opponent not connected"}


async def handle_roadrash_game_rejoin(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    lobby_id = params.get("lobby_id")
    if not lobby_id or lobby_id not in active_lobbies:
        return {"success": False, "reason": "Lobby not found"}

    lobby = active_lobbies[lobby_id]
    if lobby.get("started_at") and time.time() - lobby["started_at"] > 60:
        return {"success": False, "reason": "Rejoin window expired"}

    snapshot = lobby.get("state_snapshot")
    return {"success": True, "state_snapshot": snapshot}


def get_methods() -> Dict[str, Any]:
    return {
        "roadrash.profile.get": handle_roadrash_profile_get,
        "roadrash.profile.save": handle_roadrash_profile_save,
        "roadrash.leaderboard.submit": handle_roadrash_leaderboard_submit,
        "roadrash.leaderboard.get": handle_roadrash_leaderboard_get,
        "roadrash.leaderboard.personal_best": handle_roadrash_leaderboard_personal_best,
        "roadrash.leaderboard.friends": handle_roadrash_leaderboard_friends,
        "roadrash.leaderboard.season": handle_roadrash_leaderboard_season,
        "roadrash.friends.add": handle_roadrash_friends_add,
        "roadrash.friends.accept": handle_roadrash_friends_accept,
        "roadrash.friends.list": handle_roadrash_friends_list,
        "roadrash.friends.challenge": handle_roadrash_friends_challenge,
        "roadrash.weather.report": handle_roadrash_weather_report,
        "roadrash.matchmaking.join": handle_roadrash_matchmaking_join,
        "roadrash.matchmaking.ready": handle_roadrash_matchmaking_ready,
        "roadrash.game.sync": handle_roadrash_game_sync,
        "roadrash.game.rejoin": handle_roadrash_game_rejoin,
    }
