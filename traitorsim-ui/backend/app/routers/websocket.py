"""WebSocket router for live game connections.

Provides WebSocket endpoints for human players to connect to live games.
"""

import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException

from ..websocket.hub import GameConnection, get_hub


logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory session store (in production, use Redis or database)
# Maps session tokens to player info
_session_store = {}


def verify_session_token(token: str) -> Optional[dict]:
    """Verify a session token and return session info.
    
    In production, this should validate against a database or cache.
    For now, we use a simple in-memory store.
    """
    return _session_store.get(token)


def create_session(game_id: str, player_id: str, display_name: str, is_host: bool = False) -> str:
    """Create a new session for a player.
    
    Args:
        game_id: Game identifier
        player_id: Player identifier
        display_name: Player's display name
        is_host: Whether this player is the host
        
    Returns:
        Session token
    """
    import secrets
    token = secrets.token_urlsafe(32)
    
    _session_store[token] = {
        "game_id": game_id,
        "player_id": player_id,
        "display_name": display_name,
        "is_host": is_host,
    }
    
    return token


@router.websocket("/ws/game/{game_id}")
async def game_websocket(
    websocket: WebSocket,
    game_id: str,
    token: str = Query(...),
):
    """WebSocket endpoint for human players in live games.
    
    This endpoint allows human players to:
    - Connect to a live game
    - Receive game state updates
    - Get decision requests
    - Submit decisions/actions
    
    Args:
        websocket: WebSocket connection
        game_id: Game identifier from URL path
        token: Session token from query parameter
    """
    # Verify session token
    session = verify_session_token(token)
    if not session:
        await websocket.close(code=4001, reason="Invalid session token")
        return
    
    if session.get("game_id") != game_id:
        await websocket.close(code=4001, reason="Session not valid for this game")
        return
    
    player_id = session.get("player_id")
    display_name = session.get("display_name", "Unknown")
    
    # Accept the WebSocket connection
    await websocket.accept()
    logger.info(f"WebSocket accepted for player {player_id} in game {game_id}")
    
    # Register with WebSocket hub
    hub = get_hub()
    connection = GameConnection(
        websocket=websocket,
        player_id=player_id,
        game_id=game_id,
    )
    await hub.connect(connection)
    
    try:
        # Send initial game state if game is active
        if game_id in hub.active_games:
            await hub._send_game_state(game_id, player_id)
        else:
            # Game not started yet
            await websocket.send_json({
                "type": "waiting",
                "message": "Waiting for game to start...",
            })
        
        # Main message loop
        while True:
            try:
                # Receive message from client
                message = await websocket.receive_json()
                
                # Handle the message
                await hub.handle_player_message(game_id, player_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for player {player_id}")
                break
            except Exception as e:
                logger.error(f"Error handling message from {player_id}: {e}")
                # Send error to client
                try:
                    await websocket.send_json({
                        "type": "error",
                        "error": "Failed to process message",
                    })
                except Exception:
                    pass
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for player {player_id}")
    except Exception as e:
        logger.error(f"WebSocket error for player {player_id}: {e}")
    finally:
        # Clean up connection
        await hub.disconnect(game_id, player_id)
        logger.info(f"WebSocket connection closed for player {player_id}")


@router.get("/ws/stats/{game_id}")
async def get_websocket_stats(game_id: str):
    """Get WebSocket connection statistics for a game.
    
    This is useful for debugging connection issues.
    """
    hub = get_hub()
    stats = hub.get_game_stats(game_id)
    return stats
