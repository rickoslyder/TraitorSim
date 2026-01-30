"""Core game state data structures.

Voice Integration:
    GameState can optionally emit voice events when significant game events
    occur (murders, banishments, phase transitions). Set voice_emitter
    to enable automatic voice generation for events.

    Example:
        from traitorsim.voice import create_voice_emitter, VoiceMode

        voice_emitter = create_voice_emitter(mode=VoiceMode.EPISODE)
        game_state.voice_emitter = voice_emitter
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Coroutine, TYPE_CHECKING
import numpy as np
from .enums import GamePhase, Role

if TYPE_CHECKING:
    from ..voice.voice_emitter import VoiceEmitter


@dataclass
class Player:
    """Represents a player in the game."""

    id: str  # e.g., "player_01"
    name: str  # e.g., "Diane"
    role: Role
    alive: bool = True
    has_shield: bool = False
    has_dagger: bool = False
    has_seer: bool = False  # Seer power allows checking one player's true role
    was_recruited: bool = False  # True if converted from Faithful to Traitor
    is_human: bool = False  # True if controlled by a human player

    # Big Five personality traits (0.0 to 1.0)
    personality: Dict[str, float] = field(default_factory=dict)
    # {"openness": 0.75, "conscientiousness": 0.60, ...}

    # Stats for missions
    stats: Dict[str, float] = field(default_factory=dict)
    # {"intellect": 0.8, "dexterity": 0.4, "social_influence": 0.9}

    # Agent metadata
    memory_path: Optional[str] = None  # Path to agent's memory directory

    # Archetype and persona data (from World Bible system)
    archetype_id: Optional[str] = None  # e.g., "prodigy", "charming_sociopath"
    archetype_name: Optional[str] = None  # e.g., "The Prodigy"
    demographics: Dict[str, any] = field(default_factory=dict)
    # {"age": 29, "location": "Manchester", "occupation": "NHS nurse", "ethnicity": "British-Pakistani"}
    backstory: Optional[str] = None  # Rich narrative from Deep Research
    strategic_profile: Optional[str] = None  # How they approach the game

    def __post_init__(self):
        """Initialize default personality and stats if not provided."""
        if not self.personality:
            # Default balanced personality
            self.personality = {
                "openness": 0.5,
                "conscientiousness": 0.5,
                "extraversion": 0.5,
                "agreeableness": 0.5,
                "neuroticism": 0.5,
            }
        if not self.stats:
            self.stats = {
                "intellect": 0.5,
                "dexterity": 0.5,
                "social_influence": 0.5,
            }


@dataclass
class TrustMatrix:
    """
    Matrix tracking suspicion scores between players.
    M[i][j] = Player i's suspicion of Player j
    0.0 = Absolute trust
    1.0 = Absolute certainty of treachery
    """

    player_ids: List[str]
    matrix: np.ndarray = field(init=False)

    def __post_init__(self):
        n = len(self.player_ids)
        # Initialize with neutral suspicion (0.5)
        self.matrix = np.full((n, n), 0.5)
        # Diagonal is 0 (no self-suspicion)
        np.fill_diagonal(self.matrix, 0.0)

    def get_suspicion(self, observer_id: str, suspect_id: str) -> float:
        """Get observer's suspicion of suspect."""
        i = self.player_ids.index(observer_id)
        j = self.player_ids.index(suspect_id)
        return float(self.matrix[i, j])

    def update_suspicion(
        self, observer_id: str, suspect_id: str, delta: float, clamp: bool = True
    ):
        """Update suspicion score by delta."""
        i = self.player_ids.index(observer_id)
        j = self.player_ids.index(suspect_id)
        self.matrix[i, j] += delta
        if clamp:
            self.matrix[i, j] = np.clip(self.matrix[i, j], 0.0, 1.0)

    def get_all_suspicions(self, observer_id: str) -> Dict[str, float]:
        """Get all suspicion scores for an observer."""
        i = self.player_ids.index(observer_id)
        return {
            player_id: float(self.matrix[i, j])
            for j, player_id in enumerate(self.player_ids)
            if player_id != observer_id
        }


@dataclass
class GameState:
    """Complete game state."""

    day: int = 1
    phase: GamePhase = GamePhase.INIT
    prize_pot: float = 0.0

    players: List[Player] = field(default_factory=list)
    trust_matrix: Optional[TrustMatrix] = None

    # History tracking
    murdered_players: List[str] = field(default_factory=list)
    banished_players: List[str] = field(default_factory=list)
    vote_history: List[Dict] = field(default_factory=list)
    recruited_players: List[str] = field(default_factory=list)  # Players who were recruited

    # Current phase data
    last_murder_victim: Optional[str] = None
    shield_holder: Optional[str] = None  # Player who won shield this mission
    dagger_holder: Optional[str] = None  # Player who won dagger this mission
    seer_holder: Optional[str] = None  # Player who holds Seer power (UK/US S3+)

    # Mission rewards (set during mission phase)
    shield_available: bool = False  # Is shield up for grabs this mission?
    dagger_available: bool = False  # Is dagger up for grabs this mission?

    # Breakfast order tracking (for dramatic entry patterns)
    breakfast_order_history: List[List[str]] = field(default_factory=list)  # List of player IDs in entry order per day
    last_murder_discussion: List[str] = field(default_factory=list)  # Player IDs discussed for murder in last Turret

    # Trust matrix snapshots for UI visualization
    trust_snapshots: List[Dict[str, Any]] = field(default_factory=list)  # Captured after each phase

    # Structured events for UI timeline
    events: List[Dict[str, Any]] = field(default_factory=list)  # All game events with metadata

    # Voice integration (optional)
    voice_emitter: Optional["VoiceEmitter"] = None
    voice_emit_callback: Optional[Callable[[Any], Coroutine[Any, Any, None]]] = None

    # Event types that trigger voice emission
    VOICE_ENABLED_EVENTS: set = field(default_factory=lambda: {
        "MURDER",
        "BANISHMENT",
        "MISSION_COMPLETE",
        "PHASE_CHANGE",
        "RECRUITMENT",
        "SHIELD_AWARDED",
        "DAGGER_USED",
        "GAME_END",
    })

    @property
    def alive_players(self) -> List[Player]:
        """Get list of alive players."""
        return [p for p in self.players if p.alive]

    @property
    def alive_faithful(self) -> List[Player]:
        """Get alive Faithful players."""
        return [p for p in self.alive_players if p.role == Role.FAITHFUL]

    @property
    def alive_traitors(self) -> List[Player]:
        """Get alive Traitor players."""
        return [p for p in self.alive_players if p.role == Role.TRAITOR]

    def check_win_condition(self) -> Optional[Role]:
        """
        Check if game has ended and who won.
        Returns Role.FAITHFUL, Role.TRAITOR, or None
        """
        traitor_count = len(self.alive_traitors)
        faithful_count = len(self.alive_faithful)

        if traitor_count == 0:
            return Role.FAITHFUL  # Faithful win
        elif traitor_count >= faithful_count:
            return Role.TRAITOR  # Traitors win (majority)
        return None  # Game continues

    def get_player(self, player_id: str) -> Optional[Player]:
        """Get player by ID."""
        for player in self.players:
            if player.id == player_id:
                return player
        return None

    def get_player_by_name(self, name: str) -> Optional[Player]:
        """Get player by name."""
        for player in self.players:
            if player.name == name:
                return player
        return None

    def add_event(
        self,
        event_type: str,
        phase: str,
        actor: Optional[str] = None,
        target: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        narrative: Optional[str] = None,
    ) -> None:
        """
        Record a structured game event for UI timeline.

        Also emits voice events for significant game moments if voice_emitter
        is configured. Voice-enabled event types are defined in VOICE_ENABLED_EVENTS.

        Args:
            event_type: Type of event (MURDER, BANISHMENT, VOTE_TALLY, MISSION_COMPLETE, etc.)
            phase: Game phase (breakfast, mission, social, roundtable, turret)
            actor: Player ID who performed the action (optional)
            target: Player ID who was affected (optional)
            data: Additional structured data for the event
            narrative: Human-readable description
        """
        event = {
            "day": self.day,
            "phase": phase,
            "type": event_type,
            "actor": actor,
            "target": target,
            "data": data or {},
            "narrative": narrative,
        }
        self.events.append(event)

        # Emit voice event if configured and event type is voice-enabled
        if self.voice_emitter and event_type in self.VOICE_ENABLED_EVENTS and narrative:
            self._queue_voice_event(event_type, phase, narrative, data or {})

    def _queue_voice_event(
        self,
        event_type: str,
        phase: str,
        narrative: str,
        data: Dict[str, Any],
    ) -> None:
        """Queue a voice event for emission (sync wrapper for async emit).

        Args:
            event_type: Type of game event
            phase: Game phase
            narrative: Text to synthesize
            data: Event metadata
        """
        if not self.voice_emitter:
            return

        try:
            from ..voice.voice_emitter import VoiceEvent, VoiceEventType, EmotionHint

            # Map event types to voice event types
            type_map = {
                "MURDER": VoiceEventType.EVENT_MURDER,
                "BANISHMENT": VoiceEventType.EVENT_BANISHMENT,
                "MISSION_COMPLETE": VoiceEventType.EVENT_MISSION_COMPLETE,
                "RECRUITMENT": VoiceEventType.EVENT_RECRUITMENT,
                "SHIELD_AWARDED": VoiceEventType.EVENT_SHIELD,
                "DAGGER_USED": VoiceEventType.EVENT_DAGGER,
                "GAME_END": VoiceEventType.SYSTEM_GAME_END,
                "PHASE_CHANGE": VoiceEventType.SYSTEM_PHASE_TRANSITION,
            }
            voice_type = type_map.get(event_type, VoiceEventType.NARRATOR)

            # Determine emotion from event type
            emotion_map = {
                "MURDER": EmotionHint.SOMBER,
                "BANISHMENT": EmotionHint.DRAMATIC,
                "MISSION_COMPLETE": EmotionHint.NEUTRAL,
                "GAME_END": EmotionHint.TRIUMPHANT,
            }
            emotion = emotion_map.get(event_type, EmotionHint.NEUTRAL)

            voice_event = VoiceEvent(
                event_type=voice_type,
                text=narrative,
                speaker_id="narrator",
                speaker_name="The Host",
                emotion=emotion,
                day=self.day,
                phase=phase,
                priority=3,  # Medium-high priority for game events
                metadata={"game_event_type": event_type, **data},
            )

            # Use callback if provided (for async contexts)
            if self.voice_emit_callback:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.voice_emit_callback(voice_event))
                except RuntimeError:
                    # No running loop, use synchronous approach
                    asyncio.run(self.voice_emitter.emit(voice_event))
            else:
                # Try to emit directly (works if emitter.emit is sync-compatible)
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.voice_emitter.emit(voice_event))
                except RuntimeError:
                    # No running loop - queue for later
                    pass

        except Exception as e:
            # Voice emission should never break game logic
            print(f"Warning: Failed to queue voice event: {e}")

    def capture_trust_snapshot(self, phase: str) -> Dict[str, Any]:
        """
        Capture current trust matrix state for UI export.

        Creates a snapshot of all alive players' suspicion scores,
        useful for visualizing trust evolution over the game timeline.

        Args:
            phase: Current game phase (breakfast, mission, social, roundtable, turret)

        Returns:
            Dict with day, phase, and nested matrix of suspicion scores
        """
        if not self.trust_matrix:
            return {"day": self.day, "phase": phase, "matrix": {}}

        matrix_data = {}
        for observer in self.alive_players:
            matrix_data[observer.id] = {}
            for target in self.players:  # Include all players (even dead) for historical context
                if target.id != observer.id:
                    matrix_data[observer.id][target.id] = self.trust_matrix.get_suspicion(
                        observer.id, target.id
                    )

        snapshot = {
            "day": self.day,
            "phase": phase,
            "alive_count": len(self.alive_players),
            "matrix": matrix_data,
        }

        # Auto-append to history
        self.trust_snapshots.append(snapshot)

        return snapshot

    def to_export_dict(self) -> Dict[str, Any]:
        """
        Export complete game state for UI visualization.

        This is the canonical export method that ensures all data
        needed by the TraitorSim UI is included in the JSON output.

        Returns:
            Dict containing all game data suitable for JSON serialization
        """
        return {
            "day": self.day,
            "phase": self.phase.value if hasattr(self.phase, 'value') else str(self.phase),
            "prize_pot": self.prize_pot,
            "players": {
                p.id: {
                    "id": p.id,
                    "name": p.name,
                    "role": p.role.value if hasattr(p.role, 'value') else str(p.role),
                    "alive": p.alive,
                    "has_shield": p.has_shield,
                    "has_dagger": p.has_dagger,
                    "was_recruited": p.was_recruited,
                    # Archetype and persona data
                    "archetype_id": p.archetype_id,
                    "archetype_name": p.archetype_name,
                    "backstory": p.backstory,
                    "strategic_profile": p.strategic_profile,
                    "demographics": p.demographics,
                    # OCEAN personality traits
                    "personality": {
                        "openness": p.personality.get("openness", 0.5),
                        "conscientiousness": p.personality.get("conscientiousness", 0.5),
                        "extraversion": p.personality.get("extraversion", 0.5),
                        "agreeableness": p.personality.get("agreeableness", 0.5),
                        "neuroticism": p.personality.get("neuroticism", 0.5),
                    },
                    # Mission stats
                    "stats": {
                        "intellect": p.stats.get("intellect", 0.5),
                        "dexterity": p.stats.get("dexterity", 0.5),
                        "social_influence": p.stats.get("social_influence", 0.5),
                        "composure": p.stats.get("composure", 0.5),
                    },
                }
                for p in self.players
            },
            "murdered_players": self.murdered_players,
            "banished_players": self.banished_players,
            "recruited_players": self.recruited_players,
            "vote_history": self.vote_history,
            "breakfast_order_history": self.breakfast_order_history,
            "trust_snapshots": self.trust_snapshots,
            "events": self.events,
            "shield_holder": self.shield_holder,
            "dagger_holder": self.dagger_holder,
            "seer_holder": self.seer_holder,
        }
