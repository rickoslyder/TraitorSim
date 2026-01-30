"""Decision registry for human-in-the-loop gameplay.

Tracks pending decisions from human players and routes them to the game engine.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from uuid import uuid4


logger = logging.getLogger(__name__)


class DecisionType(Enum):
    """Types of decisions human players can make."""
    
    VOTE = "vote"  # Banishment vote
    MURDER = "murder"  # Traitor murder selection
    RECRUIT = "recruit"  # Recruitment offer (accept/decline)
    SHIELD = "shield"  # Shield-related decision
    DAGGER = "dagger"  # Dagger-related decision
    SEER = "seer"  # Seer power usage
    MISSION = "mission"  # Mission participation decisions
    SOCIAL = "social"  # Social phase actions


@dataclass
class PendingDecision:
    """Represents a decision waiting for human player input."""
    
    decision_id: str
    game_id: str
    player_id: str
    decision_type: DecisionType
    context: Dict[str, Any]  # Game context for the decision
    timeout_seconds: int
    created_at: datetime
    deadline: datetime
    resolved: bool = False
    result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "decision_id": self.decision_id,
            "game_id": self.game_id,
            "player_id": self.player_id,
            "decision_type": self.decision_type.value,
            "context": self.context,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat(),
            "resolved": self.resolved,
            "result": self.result,
        }


class DecisionRegistry:
    """Registry for tracking and routing human player decisions.
    
    This class is designed to work with WebSocket connections to deliver
    decision requests to human players and receive their responses.
    """
    
    def __init__(self):
        """Initialize the decision registry."""
        self._pending: Dict[str, PendingDecision] = {}  # decision_id -> PendingDecision
        self._by_game: Dict[str, List[str]] = {}  # game_id -> [decision_ids]
        self._by_player: Dict[str, List[str]] = {}  # player_id -> [decision_ids]
        
        # Callbacks for WebSocket integration
        self._broadcast_callback: Optional[Callable] = None
        self._send_to_player_callback: Optional[Callable] = None
        
        # Event for async waiting
        self._decision_events: Dict[str, asyncio.Event] = {}
        
        logger.info("DecisionRegistry initialized")
    
    def set_broadcast_callback(self, callback: Callable[[str, Dict], Any]):
        """Set callback for broadcasting messages to all players in a game.
        
        Args:
            callback: Function(game_id: str, message: dict) -> Any
        """
        self._broadcast_callback = callback
        logger.debug("Broadcast callback registered")
    
    def set_send_to_player_callback(self, callback: Callable[[str, str, Dict], Any]):
        """Set callback for sending messages to specific players.
        
        Args:
            callback: Function(game_id: str, player_id: str, message: dict) -> Any
        """
        self._send_to_player_callback = callback
        logger.debug("Send-to-player callback registered")
    
    async def request_decision(
        self,
        game_id: str,
        player_id: str,
        decision_type: DecisionType,
        context: Dict[str, Any],
        timeout_seconds: int = 120,
    ) -> Dict[str, Any]:
        """Request a decision from a human player.
        
        This method:
        1. Creates a pending decision record
        2. Sends the decision request via WebSocket
        3. Waits for the player to respond (or timeout)
        4. Returns the decision result
        
        Args:
            game_id: Unique game identifier
            player_id: Player who needs to decide
            decision_type: Type of decision being requested
            context: Game context for the decision
            timeout_seconds: How long to wait for response
            
        Returns:
            The player's decision result
            
        Raises:
            TimeoutError: If player doesn't respond in time
        """
        decision_id = str(uuid4())
        now = datetime.now()
        
        pending = PendingDecision(
            decision_id=decision_id,
            game_id=game_id,
            player_id=player_id,
            decision_type=decision_type,
            context=context,
            timeout_seconds=timeout_seconds,
            created_at=now,
            deadline=now + timedelta(seconds=timeout_seconds),
        )
        
        # Store the pending decision
        self._pending[decision_id] = pending
        self._by_game.setdefault(game_id, []).append(decision_id)
        self._by_player.setdefault(player_id, []).append(decision_id)
        
        # Create an event for async waiting
        event = asyncio.Event()
        self._decision_events[decision_id] = event
        
        # Send decision request to player via WebSocket
        await self._notify_player(pending)
        
        # Broadcast to all players that this player is deciding
        await self._notify_broadcast(pending)
        
        logger.info(
            f"Decision requested: {decision_id} for player {player_id} "
            f"in game {game_id} (type: {decision_type.value})"
        )
        
        # Wait for resolution or timeout
        try:
            await asyncio.wait_for(
                event.wait(),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            logger.warning(f"Decision timeout: {decision_id}")
            # Mark as resolved with timeout result
            pending.resolved = True
            pending.result = {"timeout": True, "error": "Decision timed out"}
            raise TimeoutError(f"Player {player_id} did not respond in time")
        
        # Return the result
        return pending.result
    
    async def submit_decision(
        self,
        game_id: str,
        player_id: str,
        decision_data: Dict[str, Any],
    ) -> bool:
        """Submit a decision from a human player.
        
        This is called when a player submits their decision via WebSocket.
        
        Args:
            game_id: Game identifier
            player_id: Player who is submitting
            decision_data: The decision data (must include decision_id)
            
        Returns:
            True if decision was accepted, False otherwise
        """
        decision_id = decision_data.get("decision_id")
        if not decision_id:
            logger.error("Decision submission missing decision_id")
            return False
        
        if decision_id not in self._pending:
            logger.warning(f"Decision not found or already resolved: {decision_id}")
            return False
        
        pending = self._pending[decision_id]
        
        # Verify game and player match
        if pending.game_id != game_id or pending.player_id != player_id:
            logger.error(
                f"Decision mismatch: expected {pending.game_id}/{pending.player_id}, "
                f"got {game_id}/{player_id}"
            )
            return False
        
        # Check if already resolved
        if pending.resolved:
            logger.warning(f"Decision already resolved: {decision_id}")
            return False
        
        # Store the result
        pending.result = decision_data.get("result", decision_data)
        pending.resolved = True
        
        # Signal the waiting task
        if decision_id in self._decision_events:
            self._decision_events[decision_id].set()
        
        # Notify all players of the decision
        await self._notify_decision_made(pending)
        
        logger.info(f"Decision submitted: {decision_id} by player {player_id}")
        return True
    
    async def _notify_player(self, pending: PendingDecision):
        """Send decision request to the specific player."""
        if not self._send_to_player_callback:
            logger.warning("No send_to_player callback registered")
            return
        
        message = {
            "type": "decision_request",
            "decision_id": pending.decision_id,
            "decision_type": pending.decision_type.value,
            "context": pending.context,
            "timeout_seconds": pending.timeout_seconds,
            "deadline": pending.deadline.isoformat(),
        }
        
        try:
            await self._send_to_player_callback(
                pending.game_id,
                pending.player_id,
                message
            )
        except Exception as e:
            logger.error(f"Failed to send decision request: {e}")
    
    async def _notify_broadcast(self, pending: PendingDecision):
        """Broadcast that a player needs to make a decision."""
        if not self._broadcast_callback:
            return
        
        message = {
            "type": "player_deciding",
            "player_id": pending.player_id,
            "decision_type": pending.decision_type.value,
            "decision_id": pending.decision_id,
        }
        
        try:
            await self._broadcast_callback(pending.game_id, message)
        except Exception as e:
            logger.error(f"Failed to broadcast decision notification: {e}")
    
    async def _notify_decision_made(self, pending: PendingDecision):
        """Notify all players that a decision was made."""
        if not self._broadcast_callback:
            return
        
        message = {
            "type": "decision_made",
            "player_id": pending.player_id,
            "decision_type": pending.decision_type.value,
            "decision_id": pending.decision_id,
        }
        
        try:
            await self._broadcast_callback(pending.game_id, message)
        except Exception as e:
            logger.error(f"Failed to broadcast decision made: {e}")
    
    def get_pending_for_player(self, player_id: str) -> List[PendingDecision]:
        """Get all pending decisions for a player."""
        decision_ids = self._by_player.get(player_id, [])
        return [
            self._pending[did]
            for did in decision_ids
            if did in self._pending and not self._pending[did].resolved
        ]
    
    def get_pending_for_game(self, game_id: str) -> List[PendingDecision]:
        """Get all pending decisions for a game."""
        decision_ids = self._by_game.get(game_id, [])
        return [
            self._pending[did]
            for did in decision_ids
            if did in self._pending and not self._pending[did].resolved
        ]
    
    def cleanup_game(self, game_id: str):
        """Clean up all decisions for a game."""
        decision_ids = self._by_game.pop(game_id, [])
        for did in decision_ids:
            if did in self._pending:
                pending = self._pending.pop(did)
                # Signal any waiting tasks
                if did in self._decision_events:
                    self._decision_events[did].set()
        
        logger.info(f"Cleaned up {len(decision_ids)} decisions for game {game_id}")


# Global registry instance
_registry: Optional[DecisionRegistry] = None


def get_decision_registry() -> DecisionRegistry:
    """Get or create the global decision registry."""
    global _registry
    if _registry is None:
        _registry = DecisionRegistry()
    return _registry


def reset_decision_registry():
    """Reset the global registry (useful for testing)."""
    global _registry
    _registry = None
