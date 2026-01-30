"""Playable game engine for human-in-the-loop gameplay.

Extends the async game engine to support human players making decisions
via WebSocket connections.
"""

import asyncio
import logging
import random
from typing import Dict, List, Optional, Set, Tuple, Any

from .game_engine_async import GameEngineAsync
from .config import GameConfig
from .game_state import GameState, Player, Role
from .enums import GamePhase
from .decision_registry import DecisionRegistry, DecisionType, get_decision_registry
from ..agents.player_agent_sdk import PlayerAgentSDK
from ..memory.memory_manager import MemoryManager


logger = logging.getLogger(__name__)


@dataclass
class HumanPlayerConfig:
    """Configuration for a human player."""
    player_id: str
    display_name: str
    role: Optional[Role] = None  # If None, assigned randomly


class PlayableGameEngine(GameEngineAsync):
    """Game engine that supports human players.
    
    This engine extends the async game engine to:
    1. Replace AI agents with human players for specific player slots
    2. Pause game execution when human decisions are needed
    3. Route decisions through the DecisionRegistry
    4. Broadcast game state updates to all connected clients
    """
    
    def __init__(
        self,
        config: Optional[GameConfig] = None,
        game_id: Optional[str] = None,
        human_player_configs: Optional[List[HumanPlayerConfig]] = None,
        decision_registry: Optional[DecisionRegistry] = None,
        broadcast_callback: Optional[Callable[[str, Dict], Any]] = None,
        send_to_player_callback: Optional[Callable[[str, str, Dict], Any]] = None,
    ):
        """Initialize playable game engine.
        
        Args:
            config: Game configuration
            game_id: Unique game identifier
            human_player_configs: List of human player configurations
            decision_registry: Decision registry for routing human decisions
            broadcast_callback: Callback to broadcast messages to all players
            send_to_player_callback: Callback to send messages to specific players
        """
        super().__init__(config)
        
        self.game_id = game_id or f"game_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.human_player_ids: Set[str] = set()
        self.human_configs: Dict[str, HumanPlayerConfig] = {}
        
        # Set up decision registry
        self.decision_registry = decision_registry or get_decision_registry()
        if broadcast_callback:
            self.decision_registry.set_broadcast_callback(broadcast_callback)
        if send_to_player_callback:
            self.decision_registry.set_send_to_player_callback(send_to_player_callback)
        
        # Store callbacks for direct use
        self._broadcast = broadcast_callback
        self._send_to_player = send_to_player_callback
        
        # Configure human players
        if human_player_configs:
            for hp_config in human_player_configs:
                self.human_player_ids.add(hp_config.player_id)
                self.human_configs[hp_config.player_id] = hp_config
        
        logger.info(
            f"PlayableGameEngine initialized: {len(self.human_player_ids)} human players, "
            f"{self.config.total_players - len(self.human_player_ids)} AI players"
        )
    
    def _initialize_players(self) -> None:
        """Initialize players with human/AI mix."""
        from ..persona.persona_loader import PersonaLoader
        
        # Initialize human players first
        human_count = len(self.human_configs)
        ai_count = self.config.total_players - human_count
        
        # Validate
        if human_count > self.config.total_players:
            raise ValueError(
                f"Too many human players: {human_count} > {self.config.total_players}"
            )
        
        # Create human players
        for i, (player_id, hp_config) in enumerate(self.human_configs.items()):
            player = Player(
                id=player_id,
                name=hp_config.display_name,
                role=Role.FAITHFUL,  # Will be reassigned
                personality={
                    "openness": 0.5,
                    "conscientiousness": 0.5,
                    "extraversion": 0.5,
                    "agreeableness": 0.5,
                    "neuroticism": 0.5,
                },
                stats={
                    "intellect": 50,
                    "dexterity": 50,
                    "composure": 50,
                    "willpower": 50,
                    "perception": 50,
                },
                is_human=True,
            )
            self.game_state.players[player_id] = player
            
            # Human players don't need AI agents
            self.player_agents[player_id] = None
            
            # Create memory manager for human players (for game state tracking)
            self.memory_managers[player_id] = MemoryManager(
                player_id=player_id,
                memory_base_path=f"/tmp/traitorsim/{self.game_id}/memories",
            )
        
        # Load personas for AI players
        ai_personas = []
        if ai_count > 0:
            try:
                loader = PersonaLoader(self.config.persona_library_path)
                ai_personas = loader.sample_personas(
                    count=ai_count,
                    ensure_diversity=True,
                    max_per_archetype=2
                )
            except Exception as e:
                logger.warning(f"Failed to load personas: {e}. Using random generation.")
                ai_personas = self._generate_default_personas(ai_count)
        
        # Create AI players
        for i, persona in enumerate(ai_personas):
            player_id = f"player_{human_count + i:02d}"
            player = Player(
                id=player_id,
                name=persona.get("name", f"AI Player {i+1}"),
                role=Role.FAITHFUL,
                personality=persona.get("personality", {
                    "openness": 0.5,
                    "conscientiousness": 0.5,
                    "extraversion": 0.5,
                    "agreeableness": 0.5,
                    "neuroticism": 0.5,
                }),
                stats=persona.get("stats", {
                    "intellect": 50,
                    "dexterity": 50,
                    "composure": 50,
                    "willpower": 50,
                    "perception": 50,
                }),
                is_human=False,
            )
            self.game_state.players[player_id] = player
            
            # Create AI agent for this player
            self.player_agents[player_id] = PlayerAgentSDK(
                player=player,
                game_state=self.game_state,
                memory_manager=self.memory_managers.get(player_id),
            )
            
            # Create memory manager
            self.memory_managers[player_id] = MemoryManager(
                player_id=player_id,
                memory_base_path=f"/tmp/traitorsim/{self.game_id}/memories",
            )
        
        # Assign roles
        self._assign_roles()
        
        logger.info(f"Initialized {len(self.game_state.players)} players")
    
    def _generate_default_personas(self, count: int) -> List[Dict]:
        """Generate default personas when library is unavailable."""
        personas = []
        for i in range(count):
            personas.append({
                "name": f"AI Player {i+1}",
                "personality": {
                    "openness": random.uniform(0.3, 0.7),
                    "conscientiousness": random.uniform(0.3, 0.7),
                    "extraversion": random.uniform(0.3, 0.7),
                    "agreeableness": random.uniform(0.3, 0.7),
                    "neuroticism": random.uniform(0.3, 0.7),
                },
                "stats": {
                    "intellect": random.randint(40, 60),
                    "dexterity": random.randint(40, 60),
                    "composure": random.randint(40, 60),
                    "willpower": random.randint(40, 60),
                    "perception": random.randint(40, 60),
                },
            })
        return personas
    
    async def run_game(self) -> str:
        """Run the game with human players.
        
        This overrides the parent method to add broadcasting of game state.
        """
        logger.info(f"Starting playable game: {self.game_id}")
        
        # Broadcast game start
        await self._broadcast_game_state("game_started")
        
        try:
            result = await super().run_game()
            await self._broadcast_game_state("game_ended", {"winner": result})
            return result
        except Exception as e:
            logger.error(f"Game error: {e}")
            await self._broadcast_game_state("game_error", {"error": str(e)})
            raise
    
    async def _run_roundtable_phase(self) -> None:
        """Run roundtable phase with human voting support."""
        await self._broadcast_game_state("phase_started", {"phase": "roundtable"})
        
        # Get banishment candidates
        candidates = self._get_banishment_candidates()
        
        # Collect votes
        votes: Dict[str, str] = {}  # voter_id -> candidate_id
        
        for player_id, player in self.game_state.players.items():
            if not player.alive:
                continue
            
            if player_id in self.human_player_ids:
                # Human player - request decision
                try:
                    vote_result = await self.decision_registry.request_decision(
                        game_id=self.game_id,
                        player_id=player_id,
                        decision_type=DecisionType.VOTE,
                        context={
                            "phase": "roundtable",
                            "candidates": [
                                {"id": cid, "name": self.game_state.players[cid].name}
                                for cid in candidates
                            ],
                            "day": self.game_state.day,
                        },
                        timeout_seconds=120,
                    )
                    
                    if "timeout" in vote_result:
                        # Timeout - use AI fallback
                        logger.warning(f"Human player {player_id} timed out on vote")
                        vote = await self._get_ai_vote(player_id, candidates)
                    else:
                        vote = vote_result.get("vote")
                        
                except Exception as e:
                    logger.error(f"Error getting human vote: {e}")
                    vote = await self._get_ai_vote(player_id, candidates)
            else:
                # AI player
                vote = await self._get_ai_vote(player_id, candidates)
            
            if vote in candidates:
                votes[player_id] = vote
                await self._broadcast_game_state("vote_cast", {
                    "player_id": player_id,
                    "voted_for": vote,
                })
        
        # Process votes
        await self._process_votes(votes)
        await self._broadcast_game_state("phase_ended", {"phase": "roundtable"})
    
    async def _run_turret_phase(self) -> None:
        """Run turret phase with human traitor support."""
        await self._broadcast_game_state("phase_started", {"phase": "turret"})
        
        # Get living traitors
        traitors = [
            pid for pid, p in self.game_state.players.items()
            if p.alive and p.role == Role.TRAITOR
        ]
        
        if not traitors:
            logger.info("No traitors remaining")
            return
        
        # Get murder candidates (living faithful)
        candidates = [
            pid for pid, p in self.game_state.players.items()
            if p.alive and p.role == Role.FAITHFUL
        ]
        
        if not candidates:
            logger.info("No faithful remaining to murder")
            return
        
        # For simplicity, first traitor makes the decision
        # (In full implementation, traitors might discuss first)
        deciding_traitor = traitors[0]
        
        if deciding_traitor in self.human_player_ids:
            # Human traitor - request decision
            try:
                murder_result = await self.decision_registry.request_decision(
                    game_id=self.game_id,
                    player_id=deciding_traitor,
                    decision_type=DecisionType.MURDER,
                    context={
                        "phase": "turret",
                        "candidates": [
                            {"id": cid, "name": self.game_state.players[cid].name}
                            for cid in candidates
                        ],
                        "day": self.game_state.day,
                        "fellow_traitors": [
                            {"id": tid, "name": self.game_state.players[tid].name}
                            for tid in traitors if tid != deciding_traitor
                        ],
                    },
                    timeout_seconds=120,
                )
                
                if "timeout" in murder_result:
                    victim_id = random.choice(candidates)
                else:
                    victim_id = murder_result.get("target")
                    if victim_id not in candidates:
                        victim_id = random.choice(candidates)
                        
            except Exception as e:
                logger.error(f"Error getting human murder decision: {e}")
                victim_id = random.choice(candidates)
        else:
            # AI traitor
            victim_id = await self._get_ai_murder_decision(deciding_traitor, candidates)
        
        # Execute murder
        if victim_id:
            victim = self.game_state.players[victim_id]
            victim.alive = False
            self.game_state.murdered_players.append(victim_id)
            
            await self._broadcast_game_state("murder", {
                "victim_id": victim_id,
                "victim_name": victim.name,
            })
        
        await self._broadcast_game_state("phase_ended", {"phase": "turret"})
    
    async def _get_ai_vote(self, player_id: str, candidates: List[str]) -> str:
        """Get a vote from an AI player."""
        agent = self.player_agents.get(player_id)
        if agent:
            # Use agent to make decision
            try:
                vote = await agent.make_vote_decision(candidates)
                return vote if vote in candidates else random.choice(candidates)
            except Exception as e:
                logger.error(f"AI vote error: {e}")
        
        return random.choice(candidates)
    
    async def _get_ai_murder_decision(self, traitor_id: str, candidates: List[str]) -> str:
        """Get murder decision from AI traitor."""
        agent = self.player_agents.get(traitor_id)
        if agent:
            try:
                target = await agent.make_murder_decision(candidates)
                return target if target in candidates else random.choice(candidates)
            except Exception as e:
                logger.error(f"AI murder decision error: {e}")
        
        return random.choice(candidates)
    
    def _get_banishment_candidates(self) -> List[str]:
        """Get list of players eligible for banishment."""
        return [
            pid for pid, p in self.game_state.players.items()
            if p.alive
        ]
    
    async def _process_votes(self, votes: Dict[str, str]) -> None:
        """Process votes and banish player."""
        if not votes:
            return
        
        # Count votes
        vote_counts: Dict[str, int] = {}
        for target_id in votes.values():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
        
        # Find highest vote count
        max_votes = max(vote_counts.values())
        top_candidates = [pid for pid, count in vote_counts.items() if count == max_votes]
        
        if len(top_candidates) == 1:
            # Clear winner
            banished_id = top_candidates[0]
        else:
            # Tie - handle according to config
            banished_id = self._resolve_tie(top_candidates, votes)
        
        # Banish player
        if banished_id:
            player = self.game_state.players[banished_id]
            player.alive = False
            self.game_state.banished_players.append(banished_id)
            
            await self._broadcast_game_state("banishment", {
                "player_id": banished_id,
                "player_name": player.name,
                "role": player.role.value,
                "votes": vote_counts.get(banished_id, 0),
            })
    
    def _resolve_tie(self, tied: List[str], all_votes: Dict[str, str]) -> Optional[str]:
        """Resolve a tie in voting."""
        if self.config.tie_break_method == "random":
            return random.choice(tied)
        elif self.config.tie_break_method == "revote":
            # For simplicity, random choice on first tie
            # Full implementation would do actual revote
            return random.choice(tied)
        else:
            return random.choice(tied)
    
    async def _broadcast_game_state(self, event_type: str, data: Optional[Dict] = None):
        """Broadcast game state update to all connected clients."""
        if not self._broadcast:
            return
        
        message = {
            "type": "game_event",
            "event": event_type,
            "game_id": self.game_id,
            "data": data or {},
        }
        
        try:
            await self._broadcast(self.game_id, message)
        except Exception as e:
            logger.error(f"Failed to broadcast game state: {e}")


# Import needed for dataclass
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Any
