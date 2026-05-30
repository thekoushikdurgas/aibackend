"""
Pokémon WebSocket JSON-RPC 2.0 Method Handlers
"""

import json
import logging
import random
import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.core.ws_auth import require_auth
from app.database.sqlalchemy import AsyncSessionLocal
from app.models.pokemon import PokemonLeaderboardModel, PokemonProfileModel
from app.services.llm import get_llm_provider, LLMConfig

logger = logging.getLogger(__name__)


# --- PROFILE METHODS ---


async def handle_pokemon_profile_get(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = await require_auth(user, "pokemon.profile.get")
    user_id = user.get("sub") or user.get("id")

    async with AsyncSessionLocal() as session:
        stmt = select(PokemonProfileModel).where(
            PokemonProfileModel.owner_id == user_id
        )
        result = await session.execute(stmt)
        profile = result.scalars().first()

        if not profile:
            profile = PokemonProfileModel(
                owner_id=user_id,
                player_name=user.get("email", "Player").split("@")[0],
                battles_total=0,
                battles_won=0,
                battles_lost=0,
                current_streak=0,
                highest_streak=0,
                custom_pokemon=[],
                achievements=[
                    {
                        "id": "p1",
                        "title": "First Encounter",
                        "description": "Complete your first battle.",
                        "icon": "⚔️",
                        "unlockedAt": None,
                    },
                    {
                        "id": "p2",
                        "title": "Gym Leader",
                        "description": "Win 3 battles in a row.",
                        "icon": "🏅",
                        "unlockedAt": None,
                    },
                    {
                        "id": "p3",
                        "title": "Geneticist",
                        "description": "Create a custom team using AI.",
                        "icon": "🔬",
                        "unlockedAt": None,
                    },
                    {
                        "id": "p4",
                        "title": "Champion",
                        "description": "Defeat the Hard AI opponent.",
                        "icon": "🏆",
                        "unlockedAt": None,
                    },
                ],
            )
            session.add(profile)
            await session.commit()
            await session.refresh(profile)

        return profile.to_dict()


async def handle_pokemon_profile_save(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user = await require_auth(user, "pokemon.profile.save")
    user_id = user.get("sub") or user.get("id")

    async with AsyncSessionLocal() as session:
        stmt = select(PokemonProfileModel).where(
            PokemonProfileModel.owner_id == user_id
        )
        result = await session.execute(stmt)
        profile = result.scalars().first()

        if not profile:
            raise JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, "Profile not found")

        if "player_name" in params:
            profile.player_name = params["player_name"]

        if "stats" in params:
            stats = params["stats"]
            profile.battles_total = stats.get("battlesTotal", profile.battles_total)
            profile.battles_won = stats.get("battlesWon", profile.battles_won)
            profile.battles_lost = stats.get("battlesLost", profile.battles_lost)
            profile.current_streak = stats.get("currentStreak", profile.current_streak)
            profile.highest_streak = stats.get("highestStreak", profile.highest_streak)

        if "customPokemon" in params:
            profile.custom_pokemon = params["customPokemon"]

        if "achievements" in params:
            profile.achievements = params["achievements"]

        await session.commit()
        await session.refresh(profile)
        return profile.to_dict()


# --- LEADERBOARD METHODS ---


async def handle_pokemon_leaderboard_submit(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    user_id = user.get("sub") or user.get("id") if user else None

    player_name = params.get("player_name", "Guest")
    score = int(params.get("score", 0))
    turns_taken = int(params.get("turns_taken", 0))
    remaining_hp = int(params.get("remaining_hp", 0))
    difficulty = params.get("difficulty", "Medium")

    async with AsyncSessionLocal() as session:
        leaderboard_entry = PokemonLeaderboardModel(
            owner_id=user_id,
            player_name=player_name,
            score=score,
            turns_taken=turns_taken,
            remaining_hp=remaining_hp,
            difficulty=difficulty,
        )
        session.add(leaderboard_entry)
        await session.commit()
        await session.refresh(leaderboard_entry)
        return {"success": True, "entry": leaderboard_entry.to_dict()}


async def handle_pokemon_leaderboard_get(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    difficulty = params.get("difficulty")
    limit = int(params.get("limit", 50))

    async with AsyncSessionLocal() as session:
        stmt = select(PokemonLeaderboardModel)
        if difficulty:
            stmt = stmt.where(PokemonLeaderboardModel.difficulty == difficulty)

        stmt = stmt.order_by(
            PokemonLeaderboardModel.score.desc(),
            PokemonLeaderboardModel.turns_taken.asc(),
        ).limit(limit)

        result = await session.execute(stmt)
        scores = result.scalars().all()
        return {"scores": [s.to_dict() for s in scores]}


# --- GEMINI AI BATTLE SERVICES ---


async def handle_pokemon_game_generate_team(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Generates a custom creative team of 3 Pokémon based on a prompt theme using Gemini."""
    theme = params.get("theme", "Cosmic Space")

    prompt = f"""
    You are an imaginative game developer and Pokémon designer.
    Your task is to generate a custom team of 3 highly creative and thematic Pokémon based on the theme: "{theme}".
    
    Each Pokémon MUST have:
    1. A unique name (e.g. "Nebulon", "Cyberchomp").
    2. One or two elemental types (e.g., "Psychic", "Steel", "Fire", "Electric", etc.).
    3. Stats summing exactly to approximately 600 points total.
       - HP (between 50 and 250)
       - Attack (between 40 and 190)
       - Defense (between 40 and 190)
       - Sp. Atk (between 40 and 190)
       - Sp. Def (between 40 and 190)
       - Speed (between 40 and 190)
    4. Exactly 4 moves, each with:
       - Name (e.g. "Cosmic Ray", "Binary Blast")
       - Base Power (0 for status moves, 40 to 120 for damage moves)
       - Type (should match the Pokémon's type or make thematic sense)
       - Category ("Physical", "Special", or "Status")
       - Description (brief explanation of what it does)
    5. A short, immersive description of the Pokémon's appearance and origin.
    
    Return your response strictly as a JSON object with a single "team" key containing an array of 3 Pokémon objects.
    JSON structure example:
    {{
      "team": [
        {{
          "name": "Astralock",
          "types": ["Psychic", "Steel"],
          "stats": {{ "hp": 100, "atk": 90, "def": 120, "spAtk": 110, "spDef": 110, "speed": 70 }},
          "moves": [
            {{ "name": "Nebula Pulse", "power": 80, "type": "Psychic", "category": "Special", "description": "Fires a pulse of star dust." }},
            ...
          ],
          "description": "Harnesses gravitational energy inside its metal shell."
        }},
        ...
      ]
    }}
    """

    try:
        provider = get_llm_provider("gemini")
        config = LLMConfig(
            model=provider.default_model,
            response_mime_type="application/json",
            temperature=0.7,
        )

        response = await provider.generate(prompt=prompt, config=config)
        data = json.loads(response.text)

        team = data.get("team", [])
        if len(team) == 3:
            return {"team": team}
        else:
            logger.warning("Gemini generated an invalid team count. Falling back.")
    except Exception as e:
        logger.error(f"Gemini team generation failed: {e}")

    # Fallback team
    fallback_team = [
        {
            "name": "Astra Flare",
            "types": ["Fire", "Psychic"],
            "stats": {
                "hp": 80,
                "atk": 70,
                "def": 75,
                "spAtk": 145,
                "spDef": 100,
                "speed": 130,
            },
            "moves": [
                {
                    "name": "Nova Blast",
                    "power": 110,
                    "type": "Fire",
                    "category": "Special",
                    "description": "A fiery supernova explosion.",
                },
                {
                    "name": "Psy-Shield",
                    "power": 0,
                    "type": "Psychic",
                    "category": "Status",
                    "description": "Boosts Special Defense by 1 stage.",
                },
                {
                    "name": "Starlight Beam",
                    "power": 80,
                    "type": "Psychic",
                    "category": "Special",
                    "description": "Fires a concentrated beam of star power.",
                },
                {
                    "name": "Ember Spark",
                    "power": 40,
                    "type": "Fire",
                    "category": "Special",
                    "description": "A quick spark of embers.",
                },
            ],
            "description": "A cosmic fox born in the heart of a stellar nebula. Its fur radiates intense heat.",
        },
        {
            "name": "Cyber Shell",
            "types": ["Water", "Steel"],
            "stats": {
                "hp": 130,
                "atk": 85,
                "def": 150,
                "spAtk": 70,
                "spDef": 115,
                "speed": 50,
            },
            "moves": [
                {
                    "name": "Iron Shell",
                    "power": 0,
                    "type": "Steel",
                    "category": "Status",
                    "description": "Drastically raises Defense.",
                },
                {
                    "name": "Hydro Cannon",
                    "power": 120,
                    "type": "Water",
                    "category": "Special",
                    "description": "Blasts a massive wave of pressurized water.",
                },
                {
                    "name": "Metal Claw",
                    "power": 50,
                    "type": "Steel",
                    "category": "Physical",
                    "description": "Claws the target with hard steel.",
                },
                {
                    "name": "Aqua Jet",
                    "power": 40,
                    "type": "Water",
                    "category": "Physical",
                    "description": "Strikes first with supersonic water speed.",
                },
            ],
            "description": "An ancient turtle upgraded with mechanical cybernetics. Its shell can withstand orbital re-entry.",
        },
        {
            "name": "Geo Titan",
            "types": ["Ground", "Fighting"],
            "stats": {
                "hp": 110,
                "atk": 140,
                "def": 110,
                "spAtk": 45,
                "spDef": 85,
                "speed": 110,
            },
            "moves": [
                {
                    "name": "Earthquake",
                    "power": 100,
                    "type": "Ground",
                    "category": "Physical",
                    "description": "Causes a devastating earthquake.",
                },
                {
                    "name": "Focus Punch",
                    "power": 120,
                    "type": "Fighting",
                    "category": "Physical",
                    "description": "A slow but extremely heavy punch.",
                },
                {
                    "name": "Rock Slide",
                    "power": 75,
                    "type": "Rock",
                    "category": "Physical",
                    "description": "Hurls large boulders at the enemy.",
                },
                {
                    "name": "Bulldoze",
                    "power": 60,
                    "type": "Ground",
                    "category": "Physical",
                    "description": "Tamples the ground, reducing foe's Speed.",
                },
            ],
            "description": "A titan carved from solid bedrock. Every punch vibrates the tectonic plates.",
        },
    ]
    return {"team": fallback_team}


async def handle_pokemon_ai_select_move(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Uses Gemini to decide the AI's move and generate dynamic commentator battle speech."""
    player_active = params.get("playerActive", {})
    ai_active = params.get("aiActive", {})
    ai_team = params.get("aiTeam", [])
    weather = params.get("weather", "None")
    terrain = params.get("terrain", "None")
    battle_log = params.get("battleLog", [])
    difficulty = params.get("difficulty", "Medium")

    prompt = f"""
    You are the AI opponent in a competitive turn-based Pokémon battle. 
    You must play strategically to win, based on the difficulty setting: "{difficulty}".
    
    Current Battle State:
    - AI Active Pokémon: {ai_active.get('name')} (HP: {ai_active.get('hp')}/{ai_active.get('maxHp')}, Types: {ai_active.get('types')})
      Moves Available: {', '.join([m.get('name') for m in ai_active.get('moves', [])])}
    - Player Active Pokémon: {player_active.get('name')} (HP: {player_active.get('hp')}/{player_active.get('maxHp')}, Types: {player_active.get('types')})
    - Field Effects: Weather = {weather}, Terrain = {terrain}
    - Recent Battle History: {json.dumps(battle_log[-4:])}
    
    Difficulty Behavior:
    - Easy: Choose moves mostly randomly. Write funny, silly comments.
    - Medium: Make logical moves, check type matchups. Write confident comments.
    - Hard: Play highly competitively. Predict switches, use setup moves, exploit type weaknesses. Write dramatic, competitive commentator statements.
    
    Choose exactly one move from the AI Active Pokémon's moves.
    Also generate a brief, exciting commentator commentary describing this move execution (max 15 words).
    
    Format response strictly as JSON with keys:
    "moveName" (exact name from the moves list)
    "commentary" (string)
    """

    try:
        provider = get_llm_provider("gemini")
        config = LLMConfig(
            model=provider.default_model,
            response_mime_type="application/json",
            temperature=0.7 if difficulty == "Easy" else 0.4,
        )

        response = await provider.generate(prompt=prompt, config=config)
        data = json.loads(response.text)

        move_name = data.get("moveName")
        commentary = data.get(
            "commentary", f"{ai_active.get('name')} prepares its next attack!"
        )

        # Verify the move belongs to the active pokemon, else select a random one
        available_move_names = [m.get("name") for m in ai_active.get("moves", [])]
        if move_name not in available_move_names:
            move_name = random.choice(available_move_names)

        return {"moveName": move_name, "commentary": commentary}
    except Exception as e:
        logger.error(f"Gemini AI move selection failed: {e}")

    # Default fallback
    moves = ai_active.get("moves", [])
    selected_move = random.choice(moves) if moves else {"name": "Struggle"}
    return {
        "moveName": selected_move.get("name"),
        "commentary": f"{ai_active.get('name')} lunges forward with a strike!",
    }


async def handle_pokemon_coach_analyze(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Provides professional coaching analysis after a battle completes."""
    battle_log = params.get("battleLog", [])
    player_team = params.get("playerTeam", [])
    ai_team = params.get("aiTeam", [])
    result_status = params.get("result", "won")  # "won" or "lost"

    prompt = f"""
    You are a professional Pokémon VGC Coach and strategic analyst.
    A player has just finished a battle and {result_status} the match.
    
    Match Details:
    - Player Team: {', '.join([p.get('name') for p in player_team])}
    - AI Opponent Team: {', '.join([a.get('name') for a in ai_team])}
    - Full Battle Log: {json.dumps(battle_log)}
    
    Provide a performance coaching critique in 3 sections:
    1. **Performance Summary**: Rate their key plays and decisions (e.g. switching at the right time, picking type advantages).
    2. **Key Battle Interaction**: Highlight a specific turn or interaction (like weather damage, a critical hit, or a super-effective hit) and explain why it was pivotal.
    3. **Strategy Recommendation**: Provide 1 or 2 concrete improvement suggestions for their move layout or team composition.
    
    Keep the tone encouraging, analytical, and professional. Limit to 150 words.
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
        logger.error(f"Gemini coach analysis failed: {e}")
        return {
            "analysis": "Congratulations on finishing the battle! A solid game overall. To improve, work on managing type advantages and keeping weather/terrain conditions in your favor."
        }


# --- REGISTRY EXPORT ---


def get_methods() -> Dict[str, Any]:
    return {
        "pokemon.profile.get": handle_pokemon_profile_get,
        "pokemon.profile.save": handle_pokemon_profile_save,
        "pokemon.leaderboard.submit": handle_pokemon_leaderboard_submit,
        "pokemon.leaderboard.get": handle_pokemon_leaderboard_get,
        "pokemon.game.generate_team": handle_pokemon_game_generate_team,
        "pokemon.ai.select_move": handle_pokemon_ai_select_move,
        "pokemon.coach.analyze": handle_pokemon_coach_analyze,
    }
