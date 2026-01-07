"""HITL (Human-in-the-Loop) Game Engine for TraitorSim.

A specialized game engine variant that supports real-time voice interaction
with a human player. Extends the async game engine with:

- Human player integration at any seat
- Voice-driven input for all phases
- Pause/resume for human response time
- Real-time state broadcasting
- Round Table voice orchestration

The human player participates alongside AI agents, speaking their
accusations, defenses, and votes through the voice interface.

Usage:
    from traitorsim.voice import GameEngineHITL

    engine = GameEngineHITL(
        config=config,
        human_player_name="Alice",
    )

    # With WebSocket server
    server = HITLServer(game_engine=engine)
    await server.start()
    await engine.run_game_async()
"""

import asyncio
import logging
import random
from typing import Dict, List, Optional, Any, Callable, Tuple
from collections import Counter
from datetime import datetime

logger = logging.getLogger(__name__)

# Import from core
try:
    from ..core.game_state import GameState, Player, Role
    from ..core.config import GameConfig
    from ..core.enums import GamePhase
except ImportError:
    # Allow standalone testing
    GameState = Any
    Player = Any
    Role = Any
    GameConfig = Any
    GamePhase = Any


class GamePhaseHITL:
    """Game phase constants for HITL mode."""
    WAITING = "waiting"              # Waiting for human to connect
    BREAKFAST = "breakfast"
    MISSION = "mission"
    SOCIAL = "social"
    ROUNDTABLE = "roundtable"
    TURRET = "turret"
    FINALE = "finale"
    COMPLETE = "complete"


class HumanInputRequest:
    """Represents a request for human input."""

    def __init__(
        self,
        request_type: str,
        prompt: str,
        options: Optional[List[str]] = None,
        timeout: float = 60.0,
        required: bool = True,
    ):
        self.request_type = request_type
        self.prompt = prompt
        self.options = options
        self.timeout = timeout
        self.required = required
        self.response: Optional[str] = None
        self.responded_at: Optional[datetime] = None
        self._event = asyncio.Event()

    def set_response(self, response: str):
        """Set the response and signal completion."""
        self.response = response
        self.responded_at = datetime.now()
        self._event.set()

    async def wait(self) -> Optional[str]:
        """Wait for response with timeout."""
        try:
            await asyncio.wait_for(self._event.wait(), timeout=self.timeout)
            return self.response
        except asyncio.TimeoutError:
            return None


class GameEngineHITL:
    """Game engine with Human-in-the-Loop voice support.

    This engine variant supports a human player participating
    alongside AI agents via voice interaction. It pauses for
    human input at appropriate moments and broadcasts game
    state for real-time updates.
    """

    def __init__(
        self,
        config: Optional[Any] = None,  # GameConfig
        human_player_name: str = "Human Player",
        human_player_seat: int = 0,
        hitl_handler: Any = None,
        roundtable_orchestrator: Any = None,
        hitl_server: Any = None,
    ):
        """Initialize HITL game engine.

        Args:
            config: Game configuration
            human_player_name: Name for the human player
            human_player_seat: Seat index for human (0 = first)
            hitl_handler: HITL voice handler
            roundtable_orchestrator: Round Table orchestrator
            hitl_server: WebSocket server for broadcasting
        """
        # Import config class if needed
        if config is None:
            try:
                from ..core.config import GameConfig
                config = GameConfig()
            except ImportError:
                config = type('GameConfig', (), {
                    'total_players': 15,
                    'num_traitors': 3,
                    'max_days': 10,
                })()

        self.config = config
        self.human_player_name = human_player_name
        self.human_player_seat = human_player_seat

        # Voice components
        self.hitl_handler = hitl_handler
        self.roundtable = roundtable_orchestrator
        self.server = hitl_server

        # Game state
        self.game_state: Optional[Any] = None
        self.player_agents: Dict[str, Any] = {}
        self.human_player: Optional[Any] = None
        self.human_player_id: Optional[str] = None

        # State tracking
        self.phase = GamePhaseHITL.WAITING
        self.day = 0
        self.is_running = False
        self.is_paused = False

        # Human interaction
        self._pending_input: Optional[HumanInputRequest] = None
        self._human_connected = asyncio.Event()
        self._phase_complete = asyncio.Event()

        # Registered votes
        self._votes: Dict[str, str] = {}
        self._finale_votes: Dict[str, str] = {}

        # Event callbacks
        self._on_phase_change: Optional[Callable] = None
        self._on_human_turn: Optional[Callable] = None
        self._on_game_event: Optional[Callable] = None

        logger.info(f"GameEngineHITL initialized with human player: {human_player_name}")

    # === Setup ===

    def initialize_game(self):
        """Initialize game state with human player."""
        try:
            from ..core.game_state import GameState, Player, Role, TrustMatrix
        except ImportError:
            logger.error("Could not import game state classes")
            return

        self.game_state = GameState()

        # Load personas or use random
        players = self._create_players()

        # Insert human player at specified seat
        human = Player(
            id=f"player_{self.human_player_seat:02d}",
            name=self.human_player_name,
            role=Role.FAITHFUL,  # Will be assigned later
            personality={
                "openness": 0.5,
                "conscientiousness": 0.5,
                "extraversion": 0.5,
                "agreeableness": 0.5,
                "neuroticism": 0.5,
            },
            stats={
                "intellect": 0.5,
                "dexterity": 0.5,
                "social_influence": 0.5,
            },
            is_human=True,
        )

        # Insert human at the right position
        self.game_state.players = (
            players[:self.human_player_seat]
            + [human]
            + players[self.human_player_seat:]
        )[:self.config.total_players]

        self.human_player = human
        self.human_player_id = human.id

        # Assign roles
        self._assign_roles()

        # Initialize trust matrix
        player_ids = [p.id for p in self.game_state.players]
        self.game_state.trust_matrix = TrustMatrix(player_ids)

        # Create AI agents for non-human players
        self._create_ai_agents()

        # Update HITL handler with player info
        if self.hitl_handler:
            self.hitl_handler.session.human_player_id = self.human_player_id
            self.hitl_handler.session.human_player_name = self.human_player_name
            self.hitl_handler.set_human_role(human.role == Role.TRAITOR)

            # Update known player names
            names = [p.name for p in self.game_state.players]
            self.hitl_handler.update_player_names(names)

        logger.info(f"Game initialized with {len(self.game_state.players)} players")
        logger.info(f"Human player '{self.human_player_name}' is a {human.role.value}")

    def _create_players(self) -> List[Any]:
        """Create AI player list from personas or random."""
        players = []

        try:
            from ..persona.persona_loader import PersonaLoader
            from ..core.game_state import Player, Role

            loader = PersonaLoader()
            personas = loader.sample_personas(
                count=self.config.total_players - 1,  # -1 for human
                ensure_diversity=True,
            )

            for i, persona in enumerate(personas):
                # Adjust index for human seat
                idx = i if i < self.human_player_seat else i + 1

                player = Player(
                    id=f"player_{idx:02d}",
                    name=persona.get("name", f"Player{idx+1}"),
                    role=Role.FAITHFUL,
                    personality=persona.get("personality", {}),
                    stats=persona.get("stats", {}),
                    archetype_id=persona.get("archetype"),
                    archetype_name=persona.get("archetype_name"),
                    backstory=persona.get("backstory"),
                )
                players.append(player)

        except Exception as e:
            logger.warning(f"Failed to load personas: {e}, using random")
            players = self._create_random_players()

        return players

    def _create_random_players(self) -> List[Any]:
        """Create players with random attributes."""
        try:
            from ..core.game_state import Player, Role
        except ImportError:
            return []

        players = []
        num_ai = self.config.total_players - 1

        for i in range(num_ai):
            idx = i if i < self.human_player_seat else i + 1

            player = Player(
                id=f"player_{idx:02d}",
                name=f"Player{idx+1}",
                role=Role.FAITHFUL,
                personality={
                    "openness": random.uniform(0.2, 0.8),
                    "conscientiousness": random.uniform(0.2, 0.8),
                    "extraversion": random.uniform(0.2, 0.8),
                    "agreeableness": random.uniform(0.2, 0.8),
                    "neuroticism": random.uniform(0.2, 0.8),
                },
                stats={
                    "intellect": random.uniform(0.3, 0.9),
                    "dexterity": random.uniform(0.3, 0.9),
                    "social_influence": random.uniform(0.3, 0.9),
                },
            )
            players.append(player)

        return players

    def _assign_roles(self):
        """Assign traitor/faithful roles."""
        try:
            from ..core.game_state import Role
        except ImportError:
            return

        # Determine if human should be traitor (configurable)
        human_can_be_traitor = True  # Could be config option

        player_indices = list(range(len(self.game_state.players)))

        if not human_can_be_traitor:
            player_indices.remove(self.human_player_seat)

        traitor_indices = random.sample(
            player_indices,
            min(self.config.num_traitors, len(player_indices))
        )

        for idx in traitor_indices:
            self.game_state.players[idx].role = Role.TRAITOR

    def _create_ai_agents(self):
        """Create AI agents for non-human players."""
        try:
            from ..agents.player_agent_sdk import PlayerAgentSDK
            from ..memory.memory_manager import MemoryManager
        except ImportError:
            logger.warning("Could not import agent classes")
            return

        for player in self.game_state.players:
            if player.id == self.human_player_id:
                continue  # Skip human

            try:
                memory_manager = MemoryManager(player, self.config)
                memory_manager.initialize()

                # Pass config for model provider settings
                agent = PlayerAgentSDK(player, self.game_state, memory_manager, config=self.config)
                self.player_agents[player.id] = agent
            except Exception as e:
                logger.error(f"Failed to create agent for {player.name}: {e}")

    # === Game Loop ===

    async def run_game_async(self) -> str:
        """Run complete HITL game.

        Returns:
            Winner ("FAITHFUL" or "TRAITOR")
        """
        self.is_running = True
        logger.info("=== TraitorSim HITL Game Starting ===")

        # Wait for human to connect
        self.phase = GamePhaseHITL.WAITING
        await self._wait_for_human()

        # Initialize game
        self.initialize_game()

        # Broadcast initial state
        await self._broadcast_game_state()

        # Main game loop
        try:
            while self.day < self.config.max_days and self.is_running:
                self.day += 1
                self.game_state.day = self.day
                logger.info(f"\n{'='*60}")
                logger.info(f"DAY {self.day}")
                logger.info(f"{'='*60}\n")

                # Run day phases
                await self._run_breakfast_phase()
                if await self._check_win(): break

                await self._run_mission_phase()
                if await self._check_win(): break

                await self._run_social_phase()

                await self._run_roundtable_phase()
                if await self._check_win(): break

                await self._run_turret_phase()
                if await self._check_win(): break

            # Determine final winner
            winner = self.game_state.check_win_condition()
            await self._announce_winner(winner)
            return winner or "UNKNOWN"

        finally:
            self.is_running = False
            self.phase = GamePhaseHITL.COMPLETE

    async def _wait_for_human(self):
        """Wait for human player to connect."""
        logger.info("Waiting for human player to connect...")

        # If we have a server, wait for connection
        if self.server:
            try:
                await asyncio.wait_for(
                    self._human_connected.wait(),
                    timeout=300.0  # 5 minute timeout
                )
            except asyncio.TimeoutError:
                logger.warning("Human connection timeout, proceeding with AI-only game")
        else:
            # No server - assume human is ready
            self._human_connected.set()

    def signal_human_connected(self):
        """Signal that human player has connected."""
        self._human_connected.set()
        logger.info("Human player connected")

    async def _check_win(self) -> bool:
        """Check if game has ended."""
        winner = self.game_state.check_win_condition()
        return winner is not None

    # === Phase Implementations ===

    async def _run_breakfast_phase(self):
        """Run breakfast phase with murder reveal."""
        self.phase = GamePhaseHITL.BREAKFAST
        await self._broadcast_phase_change()

        logger.info("\n--- Breakfast Phase ---")

        # Reveal last night's murder (if any)
        victim_name = self.game_state.last_murder_victim
        if victim_name:
            # Narrator announces
            await self._narrate(
                f"As dawn breaks, one chair sits empty. "
                f"{victim_name} will not be joining us today."
            )

            # Human reaction opportunity
            if self.human_player.alive:
                await self._request_human_input(
                    "reaction",
                    f"{victim_name} was murdered. How do you react?",
                    timeout=30.0,
                    required=False,
                )

            # AI reactions
            await self._collect_ai_reactions("murder", victim_name)

        else:
            await self._narrate("A new day begins. All players gather for breakfast.")

        await asyncio.sleep(2.0)

    async def _run_mission_phase(self):
        """Run mission phase."""
        self.phase = GamePhaseHITL.MISSION
        await self._broadcast_phase_change()

        logger.info("\n--- Mission Phase ---")

        await self._narrate("The contestants gather for today's mission.")

        # Simplified mission for HITL
        # (Full mission would involve human participation via voice)
        await asyncio.sleep(3.0)

        await self._narrate("The mission is complete. The prize pot grows.")

    async def _run_social_phase(self):
        """Run social phase with human conversation."""
        self.phase = GamePhaseHITL.SOCIAL
        await self._broadcast_phase_change()

        logger.info("\n--- Social Phase ---")

        await self._narrate(
            "The players disperse to discuss strategy. "
            "Alliances form. Suspicions grow."
        )

        # Allow human to speak with AI players
        if self.human_player.alive:
            await self._request_human_input(
                "social",
                "Who would you like to speak with? What do you want to discuss?",
                timeout=60.0,
                required=False,
            )

        await asyncio.sleep(5.0)

    async def _run_roundtable_phase(self):
        """Run Round Table with voice orchestration."""
        self.phase = GamePhaseHITL.ROUNDTABLE
        await self._broadcast_phase_change()

        logger.info("\n--- Round Table Phase ---")

        # Reset votes
        self._votes.clear()

        # Use Round Table orchestrator if available
        if self.roundtable:
            players_data = [
                {
                    "id": p.id,
                    "name": p.name,
                    "alive": p.alive,
                    "is_human": p.id == self.human_player_id,
                }
                for p in self.game_state.players
            ]

            async for audio_chunk in self.roundtable.run_round_table(
                day=self.day,
                players=players_data,
                human_player_id=self.human_player_id if self.human_player.alive else None,
            ):
                # Stream audio to server
                if self.server and audio_chunk:
                    await self._broadcast_audio(audio_chunk)

            # Get votes from orchestrator
            if self.roundtable.session and self.roundtable.session.voting_state:
                self._votes = dict(self.roundtable.session.voting_state.votes)

        else:
            # Fallback: Simple voting without orchestration
            await self._narrate("The Round Table convenes. It is time to vote.")

            # Collect human vote
            if self.human_player.alive:
                vote_options = [
                    p.name for p in self.game_state.players
                    if p.alive and p.id != self.human_player_id
                ]

                response = await self._request_human_input(
                    "vote",
                    "Who do you vote to banish?",
                    options=vote_options,
                    timeout=60.0,
                    required=True,
                )

                if response:
                    # Find player ID from name
                    for p in self.game_state.players:
                        if p.name.lower() == response.lower():
                            self._votes[self.human_player_id] = p.id
                            break

            # Collect AI votes
            await self._collect_ai_votes()

        # Process banishment
        await self._process_banishment()

    async def _run_turret_phase(self):
        """Run Turret phase (traitor murder selection)."""
        self.phase = GamePhaseHITL.TURRET
        await self._broadcast_phase_change()

        logger.info("\n--- Turret Phase ---")

        try:
            from ..core.game_state import Role
        except ImportError:
            return

        # Get alive traitors
        alive_traitors = [
            p for p in self.game_state.players
            if p.alive and p.role == Role.TRAITOR
        ]

        if not alive_traitors:
            logger.info("No traitors alive - skipping turret")
            return

        # Check if human is a traitor
        human_is_traitor = (
            self.human_player.alive
            and self.human_player.role == Role.TRAITOR
        )

        if human_is_traitor:
            # Human selects murder target
            await self._narrate(
                "[whispered] Fellow traitors, we must choose tonight's victim.",
                whispered=True
            )

            faithful_options = [
                p.name for p in self.game_state.players
                if p.alive and p.role == Role.FAITHFUL
            ]

            response = await self._request_human_input(
                "murder",
                "Who shall we murder tonight?",
                options=faithful_options,
                timeout=45.0,
                required=True,
            )

            if response:
                for p in self.game_state.players:
                    if p.name.lower() == response.lower():
                        p.alive = False
                        self.game_state.murdered_players.append(p.name)
                        self.game_state.last_murder_victim = p.name
                        logger.info(f"Traitors murdered: {p.name}")
                        break
        else:
            # AI traitors choose
            if alive_traitors:
                traitor_agent = self.player_agents.get(alive_traitors[0].id)
                if traitor_agent:
                    try:
                        victim_id = await traitor_agent.choose_murder_victim_async()
                        if victim_id:
                            victim = self.game_state.get_player(victim_id)
                            if victim:
                                victim.alive = False
                                self.game_state.murdered_players.append(victim.name)
                                self.game_state.last_murder_victim = victim.name
                                logger.info(f"Traitors murdered: {victim.name}")
                    except Exception as e:
                        logger.error(f"Murder selection failed: {e}")

    # === Voting ===

    async def _collect_ai_votes(self):
        """Collect votes from AI players."""
        for player_id, agent in self.player_agents.items():
            player = self.game_state.get_player(player_id)
            if not player or not player.alive:
                continue

            try:
                vote_id = await agent.choose_banishment_vote_async()
                if vote_id:
                    self._votes[player_id] = vote_id
            except Exception as e:
                logger.error(f"Vote collection failed for {player_id}: {e}")
                # Random vote as fallback
                targets = [
                    p.id for p in self.game_state.players
                    if p.alive and p.id != player_id
                ]
                if targets:
                    self._votes[player_id] = random.choice(targets)

    async def _process_banishment(self):
        """Process banishment based on votes."""
        if not self._votes:
            logger.warning("No votes collected")
            return

        # Count votes
        vote_counts = Counter(self._votes.values())
        banished_id = vote_counts.most_common(1)[0][0]
        banished_player = self.game_state.get_player(banished_id)

        if not banished_player:
            return

        # Banish
        banished_player.alive = False
        self.game_state.banished_players.append(banished_player.name)

        # Announcement
        vote_count = vote_counts[banished_id]
        role = banished_player.role.value if hasattr(banished_player.role, 'value') else str(banished_player.role)

        await self._narrate(
            f"By a vote of {vote_count}... "
            f"{banished_player.name}... "
            f"You have been banished."
        )

        await asyncio.sleep(2.0)

        await self._narrate(
            f"{banished_player.name} was a {role.upper()}."
        )

        # Broadcast
        if self.server:
            await self.server.broadcast_banishment(
                banished_id,
                banished_player.name,
                role,
                self._votes
            )

        # Check if human was banished
        if banished_id == self.human_player_id:
            await self._narrate(
                "Your journey ends here. You must now watch from the sidelines."
            )

    # === Human Interaction ===

    async def _request_human_input(
        self,
        request_type: str,
        prompt: str,
        options: Optional[List[str]] = None,
        timeout: float = 60.0,
        required: bool = True,
    ) -> Optional[str]:
        """Request input from the human player."""
        if not self.human_player.alive:
            return None

        self._pending_input = HumanInputRequest(
            request_type=request_type,
            prompt=prompt,
            options=options,
            timeout=timeout,
            required=required,
        )

        # Notify via callback
        if self._on_human_turn:
            await self._on_human_turn(request_type, prompt, options)

        # Broadcast prompt
        if self.server:
            await self.server.broadcast({
                "type": "human_turn",
                "request_type": request_type,
                "prompt": prompt,
                "options": options,
                "timeout": timeout,
            })

        # Wait for response
        response = await self._pending_input.wait()
        self._pending_input = None

        return response

    def receive_human_response(self, response: str):
        """Receive response from human player."""
        if self._pending_input:
            self._pending_input.set_response(response)
            logger.info(f"Human response received: {response[:50]}...")

    def register_vote(self, player_id: str, target: str):
        """Register a vote from a player."""
        # Find target ID from name if needed
        target_id = target
        for p in self.game_state.players:
            if p.name.lower() == target.lower():
                target_id = p.id
                break

        self._votes[player_id] = target_id
        logger.info(f"Vote registered: {player_id} -> {target_id}")

    def register_finale_vote(self, player_id: str, vote_type: str):
        """Register a finale vote (end/continue)."""
        self._finale_votes[player_id] = vote_type

    # === AI Interaction ===

    async def _collect_ai_reactions(self, event_type: str, target: str):
        """Collect reactions from AI agents to an event."""
        for player_id, agent in self.player_agents.items():
            player = self.game_state.get_player(player_id)
            if not player or not player.alive:
                continue

            try:
                if hasattr(agent, 'generate_reaction_async'):
                    reaction = await agent.generate_reaction_async(
                        event=event_type,
                        target=target,
                    )
                    logger.debug(f"{player.name} reacts: {reaction[:50]}...")
            except Exception as e:
                logger.debug(f"Reaction generation failed: {e}")

    # === Narration ===

    async def _narrate(self, text: str, whispered: bool = False):
        """Narrate text via voice and log."""
        logger.info(f"[NARRATOR] {text}")

        # Broadcast to clients
        if self.server:
            await self.server.broadcast_speaker_event(
                "narrator",
                "Narrator",
                "start",
                text
            )

        # Synthesize via HITL handler
        # (Would integrate with TTS here)

        await asyncio.sleep(len(text) / 20)  # Simulated speaking time

        if self.server:
            await self.server.broadcast_speaker_event(
                "narrator",
                "Narrator",
                "end"
            )

    async def _announce_winner(self, winner: str):
        """Announce game winner."""
        if winner == "FAITHFUL":
            text = "The Faithful have triumphed! The traitors have been vanquished."
        elif winner == "TRAITOR":
            text = "The Traitors have won! Deception prevails."
        else:
            text = "The game has ended."

        await self._narrate(text)

        if self.server:
            await self.server.broadcast({
                "type": "game_over",
                "winner": winner,
            })

    # === Broadcasting ===

    async def _broadcast_phase_change(self):
        """Broadcast phase change to all clients."""
        logger.info(f"Phase changed to: {self.phase}")

        if self._on_phase_change:
            await self._on_phase_change(self.phase, self.day)

        if self.server:
            await self.server.broadcast_phase_change(self.phase, self.day)

    async def _broadcast_game_state(self):
        """Broadcast full game state to all clients."""
        if self.server:
            for session in self.server._sessions.values():
                await self.server._send_game_state(session)

    async def _broadcast_audio(self, audio_data: bytes):
        """Broadcast audio to all clients."""
        if self.server:
            for session in self.server._sessions.values():
                await self.server._send_audio(session, audio_data)

    # === Callbacks ===

    def on_phase_change(self, callback: Callable):
        """Register callback for phase changes."""
        self._on_phase_change = callback

    def on_human_turn(self, callback: Callable):
        """Register callback for human turn requests."""
        self._on_human_turn = callback

    def on_game_event(self, callback: Callable):
        """Register callback for game events."""
        self._on_game_event = callback


# === Convenience Functions ===


def create_hitl_game(
    human_name: str = "Human Player",
    config: Any = None,
    **kwargs,
) -> GameEngineHITL:
    """Create a configured HITL game engine.

    Args:
        human_name: Name for the human player
        config: Game configuration
        **kwargs: Additional engine options

    Returns:
        Configured GameEngineHITL
    """
    return GameEngineHITL(
        config=config,
        human_player_name=human_name,
        **kwargs,
    )


async def run_hitl_game(
    engine: GameEngineHITL,
    server: Optional[Any] = None,
) -> str:
    """Run a complete HITL game.

    Args:
        engine: HITL game engine
        server: Optional HITL server

    Returns:
        Winner ("FAITHFUL" or "TRAITOR")
    """
    if server:
        engine.server = server

    return await engine.run_game_async()
