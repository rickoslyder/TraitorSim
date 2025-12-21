"""Base mission class and result dataclass."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class MissionResult:
    """Result of a mission execution."""

    success: bool
    earnings: float
    shield_winner: Optional[str] = None
    performance_scores: Dict[str, float] = field(default_factory=dict)
    narrative: str = ""


class BaseMission(ABC):
    """Abstract base class for all missions."""

    def __init__(self, game_state, config):
        """
        Initialize mission with game state and config.

        Args:
            game_state: Current GameState instance
            config: GameConfig instance
        """
        self.game_state = game_state
        self.config = config

    @abstractmethod
    def execute(self) -> MissionResult:
        """
        Execute the mission and return results.

        Returns:
            MissionResult with success status, earnings, and performance data
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """
        Get mission description for agents.

        Returns:
            String description of the mission objective
        """
        pass
