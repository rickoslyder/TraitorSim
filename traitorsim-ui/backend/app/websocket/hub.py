"""WebSocket hub for managing live game connections.

Coordinates WebSocket connections between human players and the PlayableGameEngine.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

from fastapi import WebSocket


logger = logging.getLogger(__name__)


@dataclass
class GameConnection:
    """Represents a WebSocket connection for a player."""
    websocket: WebSocket
    player_id: str
    game_id: str
    connected_at: str = None
    
    def __post_init__(self):
        if self.connected_at is None:
            from datetime import datetime
            self.connected_at = datetime.now().isoformat()


class WebSocketHub:
    """Hub for managing WebSocket connections and routing game events.
    
    This class:
    1. Manages player WebSocket connections
    2. Routes messages between PlayableGameEngine and players
    3. Broadcasts game state updates
    4. Handles player disconnections and reconnections
    """
    
    def __init__(self):
        """Initialize the WebSocket hub."""
        # game_id -> {player_id -> GameConnection}
        self.connections: Dict[str, Dict[str, GameConnection]] = {}
        
        # Track active games and their engines
        self.active_games: Dict[str, Any] = {}  # game_id -> PlayableGameEngine
        
        # Track player session info
        self.player_sessions: Dict[str, Dict[str, Any]] = {}  # player_id -> session info
        
        logger.info("WebSocketHub initialized")
    
    async def connect(self, connection: GameConnection) -> bool:
        """Register a new WebSocket connection.
        
        Args:
            connection: The GameConnection to register
            
        Returns:
            True if connected successfully
        """
        game_id = connection.game_id
        player_id = connection.player_id
        
        # Initialize game entry if needed
        if game_id not in self.connections:
            self.connections[game_id] = {}
        
        # Check if player already connected
        if player_id in self.connections[game_id]:
            logger.warning(f"Player {player_id} already connected to game {game_id}")
            # Close old connection
            old_conn = self.connections[game_id][player_id]
            try:
                await old_conn.websocket.close()
            except Exception:
                pass
        
        # Store new connection
        self.connections[game_id][player_id] = connection
        self.player_sessions[player_id] = {
            "game_id": game_id,
            "connected_at": connection.connected_at,
        }
        
        logger.info(f"Player {player_id} connected to game {game_id}")
        return True
    
    async def disconnect(self, game_id: str, player_id: str):
        """Remove a WebSocket connection.
        
        Args:
            game_id: Game identifier
            player_id: Player identifier
        """
        if game_id in self.connections and player_id in self.connections[game_id]:
            del self.connections[game_id][player_id]
            logger.info(f"Player {player_id} disconnected from game {game_id}")
        
        if player_id in self.player_sessions:
            del self.player_sessions[player_id]
    
    async def broadcast_to_game(self, game_id: str, message: Dict[str, Any]):
        """Broadcast a message to all players in a game.
        
        Args:
            game_id: Game to broadcast to
            message: Message to send
        """
        if game_id not in self.connections:
            return
        
        disconnected = []
        for player_id, conn in self.connections[game_id].items():
            try:
                await conn.websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to {player_id}: {e}")
                disconnected.append(player_id)
        
        # Clean up disconnected players
        for player_id in disconnected:
            await self.disconnect(game_id, player_id)
    
    async def send_to_player(self, game_id: str, player_id: str, message: Dict[str, Any]):
        """Send a message to a specific player.
        
        Args:
            game_id: Game identifier
            player_id: Player to send to
            message: Message to send
        """
        if game_id not in self.connections:
            return
        
        conn = self.connections[game_id].get(player_id)
        if not conn:
            logger.warning(f"Player {player_id} not connected to game {game_id}")
            return
        
        try:
            await conn.websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send to {player_id}: {e}")
            await self.disconnect(game_id, player_id)
    
    async def handle_player_message(
        self,
        game_id: str,
        player_id: str,
        message: Dict[str, Any]
    ):
        """Handle an incoming message from a player.
        
        Args:
            game_id: Game identifier
            player_id: Player who sent the message
            message: The message data
        """
        msg_type = message.get("type")
        
        if msg_type == "action":
            # Player submitted an action/decision
            await self._handle_player_action(game_id, player_id, message.get("data", {}))
        elif msg_type == "ping":
            # Heartbeat
            await self.send_to_player(game_id, player_id, {"type": "pong"})
        elif msg_type == "get_state":
            # Request for current game state
            await self._send_game_state(game_id, player_id)
        else:
            logger.warning(f"Unknown message type from {player_id}: {msg_type}")
    
    async def _handle_player_action(self, game_id: str, player_id: str, action_data: Dict):
        """Handle a player action/decision submission."""
        # Import here to avoid circular dependency
        from src.traitorsim.core.decision_registry import get_decision_registry
        
        registry = get_decision_registry()
        success = await registry.submit_decision(
            game_id=game_id,
            player_id=player_id,
            decision_data=action_data,
        )
        
        if success:
            # Acknowledge receipt
            await self.send_to_player(game_id, player_id, {
                "type": "action_ack",
                "decision_id": action_data.get("decision_id"),
            })
        else:
            # Error
            await self.send_to_player(game_id, player_id, {
                "type": "action_error",
                "error": "Failed to process action",
            })
    
    async def _send_game_state(self, game_id: str, player_id: str):
        """Send current game state to a player."""
        engine = self.active_games.get(game_id)
        if not engine:
            await self.send_to_player(game_id, player_id, {
                "type": "error",
                "error": "Game not found",
            })
            return
        
        # Build game state for this player
        state = self._build_game_state(engine, player_id)
        
        await self.send_to_player(game_id, player_id, {
            "type": "game_state",
            "data": state,
        })
    
    def _build_game_state(self, engine: Any, player_id: str) -> Dict[str, Any]:
        """Build game state for a specific player."""
        # Get the player's perspective
        player = engine.game_state.players.get(player_id)
        if not player:
            return {"error": "Player not found"}
        
        # Build state
        state = {
            "game_id": engine.game_id,
            "day": engine.game_state.day,
            "phase": engine.game_state.phase.value if engine.game_state.phase else None,
            "prize_pot": engine.game_state.prize_pot,
            "players": [],
            "my_player": {
                "id": player.id,
                "name": player.name,
                "role": player.role.value if player.role else None,
                "alive": player.alive,
                "has_shield": player.has_shield,
            },
        }
        
        # Add all players (with role info depending on perspective)
        for pid, p in engine.game_state.players.items():
            player_info = {
                "id": p.id,
                "name": p.name,
                "alive": p.alive,
            }
            
            # Show roles based on game rules and player perspective
            if player.role == Role.TRAITOR and p.role == Role.TRAITOR:
                # Traitors know each other
                player_info["role"] = p.role.value
            elif not p.alive:
                # Dead players' roles are revealed
                player_info["role"] = p.role.value
            elif pid == player_id:
                # Self
                player_info["role"] = p.role.value
            
            state["players"].append(player_info)
        
        return state
    
    def register_game_engine(self, game_id: str, engine: Any):
        """Register a game engine for a game.
        
        Args:
            game_id: Game identifier
            engine: PlayableGameEngine instance
        """
        self.active_games[game_id] = engine
        logger.info(f"Registered game engine for {game_id}")
    
    def unregister_game(self, game_id: str):
        """Unregister a game and clean up connections."""
        if game_id in self.active_games:
            del self.active_games[game_id]
        
        if game_id in self.connections:
            del self.connections[game_id]
        
        logger.info(f"Unregistered game {game_id}")
    
    def get_game_stats(self, game_id: str) -> Dict[str, Any]:
        """Get statistics for a game."""
        return {
            "connected_players": len(self.connections.get(game_id, {})),
            "total_players": len(self.active_games.get(game_id, {}).game_state.players) if game_id in self.active_games else 0,
            "is_active": game_id in self.active_games,
        }


# Import at end to avoid circular imports
from src.traitorsim.core.enums import Role


# Global hub instance
_hub: Optional[WebSocketHub] = None


def get_hub() -> WebSocketHub:
    """Get or create the global WebSocket hub."""
    global _hub
    if _hub is None:
        _hub = WebSocketHub()
    return _hub


def reset_hub():
    """Reset the global hub (useful for testing)."""
    global _hub
    _hub = None
