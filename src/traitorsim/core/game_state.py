"""Core game state data structures."""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import numpy as np
from .enums import GamePhase, Role


@dataclass
class Player:
    """Represents a player in the game."""

    id: str  # e.g., "player_01"
    name: str  # e.g., "Diane"
    role: Role
    alive: bool = True
    has_shield: bool = False
    has_dagger: bool = False
    was_recruited: bool = False  # True if converted from Faithful to Traitor

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

    # Mission rewards (set during mission phase)
    shield_available: bool = False  # Is shield up for grabs this mission?
    dagger_available: bool = False  # Is dagger up for grabs this mission?

    # Breakfast order tracking (for dramatic entry patterns)
    breakfast_order_history: List[List[str]] = field(default_factory=list)  # List of player IDs in entry order per day
    last_murder_discussion: List[str] = field(default_factory=list)  # Player IDs discussed for murder in last Turret

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
