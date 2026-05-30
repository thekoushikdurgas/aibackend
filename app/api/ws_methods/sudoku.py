"""
Sudoku WebSocket JSON-RPC 2.0 Method Handlers
"""

import json
import logging
import random
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.core.ws_auth import require_auth
from app.database.sqlalchemy import AsyncSessionLocal
from app.models.sudoku import SudokuLeaderboardModel, SudokuProfileModel
from app.core.connection_manager import connection_manager
from app.services.llm import get_llm_provider, LLMConfig

logger = logging.getLogger(__name__)

# In-memory multiplayer room storage
# Structure: { room_id: { "creatorId": str, "players": [...], "status": "waiting"|"playing"|"finished", "board": [[...]], "solution": [[...]], "difficulty": str, "currentTurnPlayerId": str, "messages": [...] } }
active_sudoku_rooms: Dict[str, Dict[str, Any]] = {}


# --- SUDOKU CORE ENGINE (PYTHON PORT OF sudoku.ts) ---


def create_empty_board() -> List[List[int]]:
    return [[0] * 9 for _ in range(9)]


def is_valid(board: List[List[int]], row: int, col: int, num: int) -> bool:
    for x in range(9):
        if board[row][x] == num:
            return False
        if board[x][col] == num:
            return False
        box_row = 3 * (row // 3) + x // 3
        box_col = 3 * (col // 3) + x % 3
        if board[box_row][box_col] == num:
            return False
    return True


def solve(board: List[List[int]], shuffle: bool = True) -> bool:
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                nums = list(range(1, 10))
                if shuffle:
                    random.shuffle(nums)
                for num in nums:
                    if is_valid(board, r, c, num):
                        board[r][c] = num
                        if solve(board, shuffle):
                            return True
                        board[r][c] = 0
                return False
    return True


def count_solutions(board: List[List[int]], limit: int = 2) -> int:
    count = 0

    def solve_and_count(grid: List[List[int]]) -> None:
        nonlocal count
        if count >= limit:
            return

        row, col = -1, -1
        is_empty = False

        for i in range(9):
            for j in range(9):
                if grid[i][j] == 0:
                    row, col = i, j
                    is_empty = True
                    break
            if is_empty:
                break

        if not is_empty:
            count += 1
            return

        for num in range(1, 10):
            if is_valid(grid, row, col, num):
                grid[row][col] = num
                solve_and_count(grid)
                grid[row][col] = 0

    grid_copy = [row[:] for row in board]
    solve_and_count(grid_copy)
    return count


def generate_full_board() -> List[List[int]]:
    board = create_empty_board()
    solve(board, shuffle=True)
    return board


def generate_puzzle_local(difficulty: str) -> Tuple[List[List[int]], List[List[int]]]:
    """Generates a unique Sudoku board locally."""
    solution = generate_full_board()
    puzzle = [row[:] for row in solution]

    target_cells_to_remove = {
        "Very Easy": 26,
        "Easy": 36,
        "Medium": 46,
        "Hard": 52,
        "Expert": 58,
    }.get(difficulty, 46)

    # Gather all cell coordinates and shuffle them
    cells = [(r, c) for r in range(9) for c in range(9)]
    random.shuffle(cells)

    removed_count = 0
    for r, c in cells:
        if removed_count >= target_cells_to_remove:
            break

        backup = puzzle[r][c]
        puzzle[r][c] = 0

        # Ensure unique solution
        if count_solutions(puzzle) != 1:
            puzzle[r][c] = backup
        else:
            removed_count += 1

    return puzzle, solution


def validate_full_sudoku_grid(
    solution: List[List[int]], puzzle: List[List[int]]
) -> bool:
    """Validates 9x9 grid coordinates."""
    if len(solution) != 9 or len(puzzle) != 9:
        return False

    for r in range(9):
        if len(solution[r]) != 9 or len(puzzle[r]) != 9:
            return False

        for c in range(9):
            s_val = solution[r][c]
            p_val = puzzle[r][c]
            if not isinstance(s_val, int) or s_val < 1 or s_val > 9:
                return False
            if not isinstance(p_val, int) or p_val < 0 or p_val > 9:
                return False
            if p_val != 0 and p_val != s_val:
                return False

    # Check solution rows
    for r in range(9):
        if len(set(solution[r])) != 9:
            return False

    # Check solution cols
    for c in range(9):
        col_vals = [solution[r][c] for r in range(9)]
        if len(set(col_vals)) != 9:
            return False

    # Check solution 3x3 blocks
    for b in range(9):
        box_vals = []
        start_row = (b // 3) * 3
        start_col = (b % 3) * 3
        for r in range(3):
            for c in range(3):
                box_vals.append(solution[start_row + r][start_col + c])
        if len(set(box_vals)) != 9:
            return False

    return True


# --- WEBSOCKET HANDLERS ---


async def handle_sudoku_profile_get(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = await require_auth(user, "sudoku.profile.get")
    user_id = user.get("sub") or user.get("id")

    async with AsyncSessionLocal() as session:
        stmt = select(SudokuProfileModel).where(SudokuProfileModel.owner_id == user_id)
        result = await session.execute(stmt)
        profile = result.scalars().first()

        if not profile:
            profile = SudokuProfileModel(
                owner_id=user_id,
                player_name=user.get("email", "Player").split("@")[0],
                single_player_solved=0,
                single_player_total_time=0,
                single_player_average_time=0,
                single_player_best_time=0,
                by_difficulty={
                    "Very Easy": 0,
                    "Easy": 0,
                    "Medium": 0,
                    "Hard": 0,
                    "Expert": 0,
                },
                total_time_by_difficulty={
                    "Very Easy": 0,
                    "Easy": 0,
                    "Medium": 0,
                    "Hard": 0,
                    "Expert": 0,
                },
                multiplayer_wins=0,
                multiplayer_losses=0,
                multiplayer_total_games=0,
                achievements=[
                    {
                        "id": "1",
                        "title": "First Steps",
                        "description": "Solve your first Sudoku puzzle.",
                        "icon": "🏆",
                    },
                    {
                        "id": "2",
                        "title": "Speed Demon",
                        "description": "Solve a puzzle in under 5 minutes.",
                        "icon": "⚡",
                    },
                    {
                        "id": "3",
                        "title": "Expert Solver",
                        "description": "Solve an Expert difficulty puzzle.",
                        "icon": "🧠",
                    },
                    {
                        "id": "4",
                        "title": "Social Butterfly",
                        "description": "Play your first multiplayer game.",
                        "icon": "🦋",
                    },
                ],
                recent_scores=[],
            )
            session.add(profile)
            await session.commit()
            await session.refresh(profile)

        return profile.to_dict()


async def handle_sudoku_profile_save(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = await require_auth(user, "sudoku.profile.save")
    user_id = user.get("sub") or user.get("id")

    async with AsyncSessionLocal() as session:
        stmt = select(SudokuProfileModel).where(SudokuProfileModel.owner_id == user_id)
        result = await session.execute(stmt)
        profile = result.scalars().first()

        if not profile:
            raise JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, "Profile not found")

        if "player_name" in params:
            profile.player_name = params["player_name"]
        if "singlePlayer" in params:
            sp = params["singlePlayer"]
            profile.single_player_solved = sp.get(
                "solved", profile.single_player_solved
            )
            profile.single_player_total_time = sp.get(
                "totalTime", profile.single_player_total_time
            )
            profile.single_player_average_time = sp.get(
                "averageTime", profile.single_player_average_time
            )
            profile.single_player_best_time = sp.get(
                "bestTime", profile.single_player_best_time
            )
            if "byDifficulty" in sp:
                profile.by_difficulty = sp["byDifficulty"]
            if "totalTimeByDifficulty" in sp:
                profile.total_time_by_difficulty = sp["totalTimeByDifficulty"]
        if "multiplayer" in params:
            mp = params["multiplayer"]
            profile.multiplayer_wins = mp.get("wins", profile.multiplayer_wins)
            profile.multiplayer_losses = mp.get("losses", profile.multiplayer_losses)
            profile.multiplayer_total_games = mp.get(
                "totalGames", profile.multiplayer_total_games
            )
        if "achievements" in params:
            profile.achievements = params["achievements"]
        if "recentScores" in params:
            profile.recent_scores = params["recentScores"]

        await session.commit()
        await session.refresh(profile)
        return profile.to_dict()


async def handle_sudoku_leaderboard_submit(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user_id = user.get("sub") or user.get("id") if user else "anonymous"

    player_name = params.get("player_name", "Guest")
    score = int(params.get("score", 0))
    difficulty = params.get("difficulty", "Medium")
    duration = int(params.get("time", 0))
    is_daily = bool(params.get("is_daily", False))
    daily_date_str = params.get("daily_date_str")

    async with AsyncSessionLocal() as session:
        # Create leaderboard record
        leaderboard_entry = SudokuLeaderboardModel(
            owner_id=user_id if user_id != "anonymous" else None,
            player_name=player_name,
            score=score,
            difficulty=difficulty,
            time=duration,
            is_daily=is_daily,
            daily_date_str=daily_date_str,
        )
        session.add(leaderboard_entry)
        await session.commit()
        await session.refresh(leaderboard_entry)
        return {"success": True, "entry": leaderboard_entry.to_dict()}


async def handle_sudoku_leaderboard_get(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    difficulty = params.get("difficulty")
    limit = int(params.get("limit", 50))

    async with AsyncSessionLocal() as session:
        stmt = select(SudokuLeaderboardModel)
        if difficulty:
            stmt = stmt.where(SudokuLeaderboardModel.difficulty == difficulty)
        # Order by score DESC, duration ASC
        stmt = stmt.order_by(
            SudokuLeaderboardModel.score.desc(), SudokuLeaderboardModel.time.asc()
        ).limit(limit)

        result = await session.execute(stmt)
        scores = result.scalars().all()
        return {"scores": [s.to_dict() for s in scores]}


async def handle_sudoku_leaderboard_daily(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    date_str = params.get("date_str")
    if not date_str:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "date_str required")

    async with AsyncSessionLocal() as session:
        stmt = (
            select(SudokuLeaderboardModel)
            .where(
                SudokuLeaderboardModel.is_daily.is_(True),
                SudokuLeaderboardModel.daily_date_str == date_str,
            )
            .order_by(
                SudokuLeaderboardModel.score.desc(), SudokuLeaderboardModel.time.asc()
            )
            .limit(50)
        )

        result = await session.execute(stmt)
        scores = result.scalars().all()
        return {"date_str": date_str, "scores": [s.to_dict() for s in scores]}


# --- REAL-TIME MULTIPLAYER LOBBY HANDLERS ---


async def handle_sudoku_room_create(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not connection_id:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "connection_id required")

    name = params.get("player_name", "Creator")
    difficulty = params.get("difficulty", "Medium")

    # Generate a random 6-character uppercase room code
    room_id = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=6))

    # Generate local board puzzle as baseline
    puzzle, solution = generate_puzzle_local(difficulty)

    player_self = {
        "id": (
            user.get("sub") or user.get("id") if user else f"guest_{connection_id[:8]}"
        ),
        "connection_id": connection_id,
        "name": name,
        "avatar": (user or {}).get("photo_url")
        or f"https://picsum.photos/40/40?seed={connection_id}",
        "progress": 0,
        "isReady": True,
    }

    room_data = {
        "roomId": room_id,
        "status": "playing",  # Auto-start for quick gameplay
        "creatorId": player_self["id"],
        "difficulty": difficulty,
        "board": puzzle,
        "initialBoard": [row[:] for row in puzzle],
        "solution": solution,
        "players": [player_self],
        "currentTurnPlayerId": player_self["id"],
        "messages": [
            {
                "id": str(uuid.uuid4()),
                "sender": "System",
                "text": f"Room created! Code: {room_id}. Waiting for challenger...",
                "timestamp": int(time.time() * 1000),
                "isSystem": True,
            }
        ],
    }

    active_sudoku_rooms[room_id] = room_data
    return room_data


async def handle_sudoku_room_join(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    if not connection_id:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "connection_id required")

    room_id = params.get("room_id", "").upper().strip()
    name = params.get("player_name", "Challenger")

    if room_id not in active_sudoku_rooms:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Room not found")

    room = active_sudoku_rooms[room_id]
    if len(room["players"]) >= 4:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Room is full")

    player_self = {
        "id": (
            user.get("sub") or user.get("id") if user else f"guest_{connection_id[:8]}"
        ),
        "connection_id": connection_id,
        "name": name,
        "avatar": (user or {}).get("photo_url")
        or f"https://picsum.photos/40/40?seed={connection_id}",
        "progress": 0,
        "isReady": True,
    }

    room["players"].append(player_self)

    # Notify all room players of user joining
    join_msg = {
        "id": str(uuid.uuid4()),
        "sender": "System",
        "text": f"🎮 {name} has joined the room!",
        "timestamp": int(time.time() * 1000),
        "isSystem": True,
    }
    room["messages"].append(join_msg)

    # Broadcast updated room state to all players in the room
    for player in room["players"]:
        conn_id = player["connection_id"]
        if conn_id != connection_id:
            try:
                await connection_manager.send_json(
                    conn_id,
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "result": {
                            "type": "sudoku.room.update",
                            "room": {
                                "id": room["roomId"],
                                "status": room["status"],
                                "players": room["players"],
                                "creatorId": room["creatorId"],
                                "currentTurnPlayerId": room["currentTurnPlayerId"],
                                "messages": room["messages"],
                                "board": room["board"],
                            },
                        },
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to notify player {conn_id} of join: {e}")

    return room


async def handle_sudoku_room_leave(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    room_id = params.get("room_id", "").upper().strip()
    if room_id not in active_sudoku_rooms:
        return {"success": True}

    room = active_sudoku_rooms[room_id]
    room["players"] = [
        p for p in room["players"] if p["connection_id"] != connection_id
    ]

    if not room["players"]:
        # Room is empty, delete it
        del active_sudoku_rooms[room_id]
        return {"success": True}

    leave_msg = {
        "id": str(uuid.uuid4()),
        "sender": "System",
        "text": "A player has left the match.",
        "timestamp": int(time.time() * 1000),
        "isSystem": True,
    }
    room["messages"].append(leave_msg)

    # If the creator left, reassign creator
    if room["creatorId"] not in [p["id"] for p in room["players"]]:
        room["creatorId"] = room["players"][0]["id"]

    # Rotate turn if it was the leaving player's turn
    if room["currentTurnPlayerId"] not in [p["id"] for p in room["players"]]:
        room["currentTurnPlayerId"] = room["players"][0]["id"]

    # Broadcast updated room state
    for player in room["players"]:
        try:
            await connection_manager.send_json(
                player["connection_id"],
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "result": {
                        "type": "sudoku.room.update",
                        "room": {
                            "id": room["roomId"],
                            "status": room["status"],
                            "players": room["players"],
                            "creatorId": room["creatorId"],
                            "currentTurnPlayerId": room["currentTurnPlayerId"],
                            "messages": room["messages"],
                            "board": room["board"],
                        },
                    },
                },
            )
        except Exception:
            pass

    return {"success": True}


async def handle_sudoku_room_send_message(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    room_id = params.get("room_id", "").upper().strip()
    text = params.get("text", "")

    if room_id not in active_sudoku_rooms:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Room not found")

    room = active_sudoku_rooms[room_id]
    sender_name = "Player"
    for p in room["players"]:
        if p["connection_id"] == connection_id:
            sender_name = p["name"]
            break

    msg = {
        "id": str(uuid.uuid4()),
        "sender": sender_name,
        "text": text,
        "timestamp": int(time.time() * 1000),
        "isSystem": False,
    }
    room["messages"].append(msg)

    # Broadcast message to all
    for player in room["players"]:
        try:
            await connection_manager.send_json(
                player["connection_id"],
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "result": {
                        "type": "sudoku.room.update",
                        "room": {
                            "id": room["roomId"],
                            "status": room["status"],
                            "players": room["players"],
                            "creatorId": room["creatorId"],
                            "currentTurnPlayerId": room["currentTurnPlayerId"],
                            "messages": room["messages"],
                            "board": room["board"],
                        },
                    },
                },
            )
        except Exception:
            pass

    return {"success": True}


async def handle_sudoku_room_make_move(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    room_id = params.get("room_id", "").upper().strip()
    row = int(params.get("row", 0))
    col = int(params.get("col", 0))
    value = int(params.get("value", 0))

    if room_id not in active_sudoku_rooms:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Room not found")

    room = active_sudoku_rooms[room_id]
    my_player = None
    for p in room["players"]:
        if p["connection_id"] == connection_id:
            my_player = p
            break

    if not my_player:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Player not in room")

    # Turn checks
    if room["currentTurnPlayerId"] != my_player["id"]:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Not your turn")

    # Update board values
    room["board"][row][col] = value

    # Check if solved
    is_won = True
    for r in range(9):
        for c in range(9):
            if room["board"][r][c] != room["solution"][r][c]:
                is_won = False
                break
        if not is_won:
            break

    if is_won:
        room["status"] = "finished"

    # Turn rotation logic
    next_turn_id = my_player["id"]
    if len(room["players"]) > 1:
        current_idx = next(
            i for i, p in enumerate(room["players"]) if p["id"] == my_player["id"]
        )
        next_idx = (current_idx + 1) % len(room["players"])
        next_turn_id = room["players"][next_idx]["id"]

    room["currentTurnPlayerId"] = next_turn_id

    # Add turn system message
    next_player_name = next(
        (p["name"] for p in room["players"] if p["id"] == next_turn_id), "someone"
    )
    move_text = f"🎯 {my_player['name']} correctly placed a {value} at Row {row+1}, Column {col+1}! Turn passes to {next_player_name}."
    if is_won:
        move_text = (
            f"🏆 {my_player['name']} placed the final digit {value} and WON the match!"
        )

    sys_msg = {
        "id": str(uuid.uuid4()),
        "sender": "System",
        "text": move_text,
        "timestamp": int(time.time() * 1000),
        "isSystem": True,
    }
    room["messages"].append(sys_msg)

    # Broadcast board and message
    for player in room["players"]:
        try:
            await connection_manager.send_json(
                player["connection_id"],
                {
                    "jsonrpc": "2.0",
                    "id": None,
                    "result": {
                        "type": "sudoku.room.update",
                        "room": {
                            "id": room["roomId"],
                            "status": room["status"],
                            "players": room["players"],
                            "creatorId": room["creatorId"],
                            "currentTurnPlayerId": room["currentTurnPlayerId"],
                            "messages": room["messages"],
                            "board": room["board"],
                        },
                    },
                },
            )
        except Exception:
            pass

    return room


async def handle_sudoku_room_update_progress(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    room_id = params.get("room_id", "").upper().strip()
    progress = int(params.get("progress", 0))

    if room_id not in active_sudoku_rooms:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Room not found")

    room = active_sudoku_rooms[room_id]
    for p in room["players"]:
        if p["connection_id"] == connection_id:
            p["progress"] = progress
            break

    # Broadcast updated progress to other players
    for player in room["players"]:
        if player["connection_id"] != connection_id:
            try:
                await connection_manager.send_json(
                    player["connection_id"],
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "result": {
                            "type": "sudoku.room.update",
                            "room": {
                                "id": room["roomId"],
                                "status": room["status"],
                                "players": room["players"],
                                "creatorId": room["creatorId"],
                                "currentTurnPlayerId": room["currentTurnPlayerId"],
                                "messages": room["messages"],
                                "board": room["board"],
                            },
                        },
                    },
                )
            except Exception:
                pass

    return {"success": True}


# --- GEMINI AI PROXY SERVICES ---


async def handle_sudoku_game_generate(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    difficulty = params.get("difficulty", "Medium")

    # 1. Ask Gemini to generate a mathematically sound grid
    prompt = f"""
    You are a professional Sudoku Mathematician and high-performance Generator.
    Your task is to generate a mathematically perfect 9x9 Sudoku puzzle of "{difficulty}" difficulty.
    
    Requirements:
    1. "solution" MUST be a fully solved 9x9 board with numbers 1 to 9. Every row, column, and 3x3 block must sum to 45 and contain digits 1 through 9 exactly once without repeats.
    2. "puzzle" MUST be a masked version of the "solution" grid with some numbers replaced by 0 (blank cells).
    3. The number of non-zero numbers in "puzzle" must match the targeted difficulty:
       - Since difficulty is {difficulty}, please construct a board with:
         * Very Easy: at least 52 starting clues (about 20-29 blank cells with value 0)
         * Easy: at least 42 starting clues (about 35-39 blank cells with value 0)
         * Medium: around 32-35 starting clues (about 46-49 blank cells with value 0)
         * Hard: around 26-29 starting clues (about 52-55 blank cells with value 0)
         * Expert: around 21-23 starting clues (about 58-60 blank cells with value 0)
    4. Ensure the puzzle holds a logical structure and is valid. All non-zero cells in "puzzle" MUST match the corresponding coordinate in "solution" exactly.
    5. Invent a highly imaginative, design-forward theme name for this puzzle (e.g. "Cosmic Whirlpool", "Spiral of Fibonacci", "The Symmetric Monolith"). We will display this name proudly in the game UI.
    6. List 2 to 4 prominent analytical techniques required to solve this board (e.g. "Pointing Pairs", "X-Wing", "Naked Singles").
    
    Format the response strictly as JSON.
    """

    try:
        provider = get_llm_provider("gemini")
        config = LLMConfig(
            model=provider.default_model,
            response_mime_type="application/json",
            temperature=0.4,
        )

        response = await provider.generate(prompt=prompt, config=config)
        data = json.loads(response.text)

        solution = data.get("solution")
        puzzle = data.get("puzzle")
        theme_name = data.get("themeName", f"Zen Mind #{random.randint(100, 999)}")
        techniques = data.get("techniques", ["Analytical Scanning"])

        if solution and puzzle and validate_full_sudoku_grid(solution, puzzle):
            return {
                "solution": solution,
                "puzzle": puzzle,
                "themeName": theme_name,
                "techniques": techniques,
                "generatorType": "ai",
            }
        else:
            logger.warning(
                "Gemini generated an mathematically invalid Sudoku board. Falling back."
            )
    except Exception as e:
        logger.warning(
            f"AI Sudoku Generation failed: {e}. Falling back to local solver."
        )

    # Fallback to local puzzle generator
    puzzle, solution = generate_puzzle_local(difficulty)
    return {
        "solution": solution,
        "puzzle": puzzle,
        "themeName": "Classical Balance (Local)",
        "techniques": ["Analytical Scanning"],
        "generatorType": "local",
    }


async def handle_sudoku_game_hint(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    board_data = params.get("board")
    difficulty = params.get("difficulty", "Medium")

    if not board_data:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Missing parameter: board")

    # Format board to string
    board_str = "\n".join(" ".join(str(val) for val in row) for row in board_data)

    prompt = f"""
    You are a world-class Sudoku Coach and Grandmaster.
    Here is the current board state (0 represents empty):
    {board_str}
    
    The difficulty is {difficulty}.
    Analyze the board state to find the next logical move.
    
    Your goal is to TEACH the user, not just solve it.
    Tailor your explanation to the difficulty level:
    - Very Easy / Easy: Focus on simple scanning and immediate placements. Explain very simply.
    - Medium: Introduce basic candidates (naked/hidden singles).
    - Hard: Explain intermediate techniques (pairs, triples, pointing tuples).
    - Expert: Explain advanced logic (X-Wing, Y-Wing, Swordfish) concisely.

    1. Identify the specific Sudoku strategy required.
    2. Provide a detailed, natural language explanation of the logic.
       - Start by directing the user's attention to the specific region (row, column, or box).
       - Explain the logic clearly: "Since 5 is already in row 1 and row 2, it must go here..." or "These two cells can only be 3 and 7..."
       - Conclude with the specific action (placing a number or eliminating a candidate).
       - Keep the tone encouraging and helpful.
    
    Format the response strictly as JSON with properties:
    row (0-indexed integer), col (0-indexed integer), value (integer), strategy (string), explanation (string)
    """

    try:
        provider = get_llm_provider("gemini")
        config = LLMConfig(
            model=provider.default_model,
            response_mime_type="application/json",
            temperature=0.3,
        )
        response = await provider.generate(prompt=prompt, config=config)
        data = json.loads(response.text)
        return {
            "row": int(data.get("row", 0)),
            "col": int(data.get("col", 0)),
            "value": int(data.get("value", 0)),
            "strategy": data.get("strategy", "Scanning"),
            "explanation": data.get(
                "explanation", "Scan rows and columns to place a digit."
            ),
        }
    except Exception as e:
        logger.error(f"Gemini hint generation failed: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Hint generation failed: {e}"
        )


async def handle_sudoku_game_analyze(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    mistakes = int(params.get("mistakes", 0))
    time_seconds = int(params.get("time", 0))
    difficulty = params.get("difficulty", "Medium")

    prompt = f"""
    You are a Sudoku Coach analyzing a player's recent game.
    
    Game Details:
    - Difficulty: {difficulty}
    - Time Taken: {time_seconds // 60}m {time_seconds % 60}s
    - Mistakes Made: {mistakes}
    
    Provide a performance analysis in 3 parts:
    1. **Performance Summary**: Rate their speed and accuracy based on the difficulty. (e.g., "Excellent speed for Hard difficulty", "Good accuracy but slow").
    2. **Key Insight**: 
       - If mistakes > 0: Explain that mistakes usually happen due to rushing or missing hidden candidates. Suggest a specific habit to fix this (e.g., "Double-check columns before placing").
       - If mistakes == 0: Praise their consistency and suggest trying a harder difficulty or speed-running.
    3. **Next Step**: A specific technique to practice next (e.g., "Practice X-Wings" or "Focus on scanning speed").

    Keep the tone professional yet encouraging. Limit to 150 words.
    """

    try:
        provider = get_llm_provider("gemini")
        config = LLMConfig(
            model=provider.default_model,
            temperature=0.7,
        )
        response = await provider.generate(prompt=prompt, config=config)
        return {"analysis": response.text}
    except Exception as e:
        logger.error(f"Gemini post-match analysis failed: {e}")
        return {
            "analysis": "Great job finishing the puzzle! Keep practicing to improve your speed and accuracy."
        }


# --- REGISTRY EXPORT ---


def get_methods() -> Dict[str, Any]:
    return {
        "sudoku.profile.get": handle_sudoku_profile_get,
        "sudoku.profile.save": handle_sudoku_profile_save,
        "sudoku.leaderboard.submit": handle_sudoku_leaderboard_submit,
        "sudoku.leaderboard.get": handle_sudoku_leaderboard_get,
        "sudoku.leaderboard.daily": handle_sudoku_leaderboard_daily,
        "sudoku.room.create": handle_sudoku_room_create,
        "sudoku.room.join": handle_sudoku_room_join,
        "sudoku.room.leave": handle_sudoku_room_leave,
        "sudoku.room.send_message": handle_sudoku_room_send_message,
        "sudoku.room.make_move": handle_sudoku_room_make_move,
        "sudoku.room.update_progress": handle_sudoku_room_update_progress,
        "sudoku.game.generate": handle_sudoku_game_generate,
        "sudoku.game.hint": handle_sudoku_game_hint,
        "sudoku.game.analyze": handle_sudoku_game_analyze,
    }
