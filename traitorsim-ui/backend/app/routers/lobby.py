"""Lobby router for game management.

Provides endpoints for:
- Creating game lobbies
- Joining games
- Marking ready
- Starting games
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .websocket import create_session, verify_session_token
from ..websocket.hub import get_hub


logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory lobby storage (use Redis in production)
_lobbies: Dict[str, dict] = {}


class CreateLobbyRequest(BaseModel):
    """Request to create a new game lobby."""
    name: str
    host_display_name: str
    max_players: int = 22
    num_traitors: int = 3
    rule_set: str = "uk"


class JoinLobbyRequest(BaseModel):
    """Request to join a game lobby."""
    display_name: str


class ReadyRequest(BaseModel):
    """Request to mark player as ready."""
    ready: bool


class LobbyResponse(BaseModel):
    """Response with lobby information."""
    game_id: str
    name: str
    host_id: str
    max_players: int
    num_traitors: int
    rule_set: str
    players: List[dict]
    status: str  # "waiting", "starting", "in_progress"


def _generate_game_id() -> str:
    """Generate a unique game ID."""
    return f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{id(object()) % 10000:04x}"


@router.post("/create", response_model=dict)
async def create_lobby(request: CreateLobbyRequest):
    """Create a new game lobby.
    
    Returns:
        Dictionary with game_id, session token, and player_id
    """
    game_id = _generate_game_id()
    host_player_id = f"player_{game_id}_host"
    
    # Create the lobby
    _lobbies[game_id] = {
        "game_id": game_id,
        "name": request.name,
        "host_id": host_player_id,
        "max_players": request.max_players,
        "num_traitors": request.num_traitors,
        "rule_set": request.rule_set,
        "players": {
            host_player_id: {
                "player_id": host_player_id,
                "display_name": request.host_display_name,
                "is_host": True,
                "ready": False,
            }
        },
        "status": "waiting",
        "created_at": datetime.now().isoformat(),
    }
    
    # Create session token for host
    token = create_session(game_id, host_player_id, request.host_display_name, is_host=True)
    
    logger.info(f"Created lobby {game_id} with host {request.host_display_name}")
    
    return {
        "game_id": game_id,
        "token": token,
        "player_id": host_player_id,
        "message": "Lobby created successfully",
    }


@router.post("/{game_id}/join", response_model=dict)
async def join_lobby(game_id: str, request: JoinLobbyRequest):
    """Join an existing game lobby.
    
    Args:
        game_id: Game to join
        request: Join request with display name
        
    Returns:
        Dictionary with session token and player_id
    """
    if game_id not in _lobbies:
        raise HTTPException(status_code=404, detail="Game not found")
    
    lobby = _lobbies[game_id]
    
    if lobby["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Game has already started")
    
    if len(lobby["players"]) >= lobby["max_players"]:
        raise HTTPException(status_code=400, detail="Game is full")
    
    # Generate player ID
    player_id = f"player_{game_id}_{len(lobby['players']):02d}"
    
    # Add player to lobby
    lobby["players"][player_id] = {
        "player_id": player_id,
        "display_name": request.display_name,
        "is_host": False,
        "ready": False,
    }
    
    # Create session token
    token = create_session(game_id, player_id, request.display_name, is_host=False)
    
    logger.info(f"Player {request.display_name} joined lobby {game_id}")
    
    return {
        "game_id": game_id,
        "token": token,
        "player_id": player_id,
        "message": "Joined lobby successfully",
    }


@router.post("/{game_id}/ready")
async def set_ready(game_id: str, request: ReadyRequest, token: str = Query(...)):
    """Mark a player as ready or not ready.
    
    Args:
        game_id: Game identifier
        request: Ready status
        token: Session token
    """
    # Verify session
    session = verify_session_token(token)
    if not session or session.get("game_id") != game_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    if game_id not in _lobbies:
        raise HTTPException(status_code=404, detail="Game not found")
    
    lobby = _lobbies[game_id]
    player_id = session.get("player_id")
    
    if player_id not in lobby["players"]:
        raise HTTPException(status_code=404, detail="Player not in lobby")
    
    # Update ready status
    lobby["players"][player_id]["ready"] = request.ready
    
    logger.info(f"Player {player_id} ready status: {request.ready}")
    
    return {
        "player_id": player_id,
        "ready": request.ready,
    }


@router.get("/{game_id}", response_model=LobbyResponse)
async def get_lobby(game_id: str):
    """Get lobby information.
    
    Args:
        game_id: Game identifier
    """
    if game_id not in _lobbies:
        raise HTTPException(status_code=404, detail="Game not found")
    
    lobby = _lobbies[game_id]
    
    return LobbyResponse(
        game_id=lobby["game_id"],
        name=lobby["name"],
        host_id=lobby["host_id"],
        max_players=lobby["max_players"],
        num_traitors=lobby["num_traitors"],
        rule_set=lobby["rule_set"],
        players=list(lobby["players"].values()),
        status=lobby["status"],
    )


@router.post("/{game_id}/start")
async def start_game(game_id: str, token: str = Query(...)):
    """Start the game (host only).
    
    Args:
        game_id: Game identifier
        token: Host's session token
    """
    # Verify session
    session = verify_session_token(token)
    if not session or session.get("game_id") != game_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    if not session.get("is_host"):
        raise HTTPException(status_code=403, detail="Only host can start the game")
    
    if game_id not in _lobbies:
        raise HTTPException(status_code=404, detail="Game not found")
    
    lobby = _lobbies[game_id]
    
    if lobby["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Game already started")
    
    # Check if all players are ready
    not_ready = [
        p["display_name"]
        for p in lobby["players"].values()
        if not p.get("ready", False)
    ]
    
    if not_ready:
        raise HTTPException(
            status_code=400,
            detail=f"Players not ready: {', '.join(not_ready)}"
        )
    
    # Update lobby status
    lobby["status"] = "starting"
    
    # Initialize PlayableGameEngine
    try:
        import asyncio
        from src.traitorsim.core.config import GameConfig
        from src.traitorsim.core.playable_engine import PlayableGameEngine, HumanPlayerConfig
        from src.traitorsim.core.enums import Role
        from src.traitorsim.core.decision_registry import get_decision_registry
        
        # Create game config
        config = GameConfig(
            total_players=lobby["max_players"],
            num_traitors=lobby["num_traitors"],
            rule_set=lobby["rule_set"],
        )
        
        # Create human player configs
        human_configs = []
        for player_id, player_info in lobby["players"].items():
            human_configs.append(HumanPlayerConfig(
                player_id=player_id,
                display_name=player_info["display_name"],
            ))
        
        # Get the WebSocket hub
        hub = get_hub()
        
        # Create the game engine
        engine = PlayableGameEngine(
            config=config,
            game_id=game_id,
            human_player_configs=human_configs,
            decision_registry=get_decision_registry(),
            broadcast_callback=hub.broadcast_to_game,
            send_to_player_callback=hub.send_to_player,
        )
        
        # Register with hub
        hub.register_game_engine(game_id, engine)
        
        # Start the game in background
        asyncio.create_task(_run_game(engine, lobby))
        
        logger.info(f"Started game {game_id}")
        
        return {
            "status": "started",
            "game_id": game_id,
            "message": "Game started successfully",
        }
        
    except Exception as e:
        logger.error(f"Failed to start game: {e}")
        lobby["status"] = "waiting"
        raise HTTPException(status_code=500, detail=f"Failed to start game: {str(e)}")


async def _run_game(engine: "PlayableGameEngine", lobby: dict):
    """Run the game and update lobby status."""
    try:
        lobby["status"] = "in_progress"
        winner = await engine.run_game()
        lobby["status"] = "completed"
        lobby["winner"] = winner
        logger.info(f"Game {engine.game_id} completed. Winner: {winner}")
    except Exception as e:
        logger.error(f"Game {engine.game_id} error: {e}")
        lobby["status"] = "error"
        lobby["error"] = str(e)
    finally:
        # Clean up
        hub = get_hub()
        hub.unregister_game(engine.game_id)


@router.get("/{game_id}/state")
async def get_game_state(game_id: str, token: str = Query(...)):
    """Get current game state for a player.
    
    Args:
        game_id: Game identifier
        token: Player's session token
    """
    # Verify session
    session = verify_session_token(token)
    if not session or session.get("game_id") != game_id:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    hub = get_hub()
    player_id = session.get("player_id")
    
    # Check if game is active
    if game_id not in hub.active_games:
        # Return lobby state
        if game_id in _lobbies:
            return {
                "status": _lobbies[game_id]["status"],
                "lobby": _lobbies[game_id],
            }
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Return game state from engine
    return hub._build_game_state(hub.active_games[game_id], player_id)
