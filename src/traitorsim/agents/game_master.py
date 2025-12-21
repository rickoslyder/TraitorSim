"""Game Master agent using Gemini for narrative generation."""

import logging
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.game_state import GameState
    from ..core.config import GameConfig
    from ..missions.base import MissionResult

try:
    import google.generativeai as genai
except ImportError:
    genai = None

from .prompts.gm_templates import GMPrompts


class GameMaster:
    """
    Game Master orchestrator using Gemini 3.0 Flash.
    Handles narrative generation and announcements.
    """

    def __init__(self, config: "GameConfig"):
        """Initialize Game Master with configuration."""
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Configure Gemini
        if genai is None:
            self.logger.warning(
                "google-generativeai not installed. Using fallback narratives."
            )
            self.model = None
        else:
            if not config.gemini_api_key:
                self.logger.warning("No Gemini API key provided. Using fallback narratives.")
                self.model = None
            else:
                try:
                    genai.configure(api_key=config.gemini_api_key)
                    self.model = genai.GenerativeModel(config.gemini_model)
                    self.logger.info(f"Gemini model initialized: {config.gemini_model}")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Gemini: {e}")
                    self.model = None

        # Context accumulation (leverages 1M+ context window)
        self.full_transcript = []

    def announce_game_start(self, state: "GameState") -> str:
        """Announce game start."""
        prompt = GMPrompts.game_start(state, self.config)
        response = self._generate(prompt) or self._fallback_game_start(state)
        self._log(response)
        return response

    def announce_murder(self, victim_id: Optional[str], state: "GameState") -> str:
        """Announce breakfast and reveal murder victim."""
        if not victim_id:
            prompt = GMPrompts.first_breakfast(state)
            response = self._generate(prompt) or self._fallback_first_breakfast(state)
        else:
            victim = state.get_player(victim_id)
            victim_name = victim.name if victim else "Unknown"
            prompt = GMPrompts.murder_reveal(victim_name, state)
            response = self._generate(prompt) or self._fallback_murder_reveal(
                victim_name, state
            )

        self._log(response)
        return response

    def describe_mission(self, mission_description: str) -> str:
        """Generate dramatic mission description."""
        prompt = GMPrompts.mission_intro(mission_description)
        response = self._generate(prompt) or f"Mission: {mission_description}"
        self._log(response)
        return response

    def announce_mission_result(
        self, result: "MissionResult", state: "GameState"
    ) -> str:
        """Announce mission outcome."""
        prompt = GMPrompts.mission_result(result, state)
        response = self._generate(prompt) or result.narrative
        self._log(response)
        return response

    def open_roundtable(self, state: "GameState") -> str:
        """Open the Round Table discussion."""
        prompt = GMPrompts.roundtable_open(state)
        response = self._generate(prompt) or self._fallback_roundtable_open(state)
        self._log(response)
        return response

    def announce_banishment(
        self, banished_id: str, votes: Dict, state: "GameState"
    ) -> str:
        """Announce banishment result."""
        player = state.get_player(banished_id)
        if not player:
            return f"Player {banished_id} has been banished."

        prompt = GMPrompts.banishment(player, votes, state)
        response = self._generate(prompt) or self._fallback_banishment(player, votes)
        self._log(response)
        return response

    def announce_finale(self, winner, state: "GameState") -> str:
        """Announce game end and winner."""
        prompt = GMPrompts.finale(winner, state)
        response = self._generate(prompt) or self._fallback_finale(winner, state)
        self._log(response)
        return response

    def _generate(self, prompt: str) -> Optional[str]:
        """Generate response using Gemini."""
        if not self.model:
            return None

        try:
            # Include recent context for continuity
            context = "\n".join(self.full_transcript[-5:])  # Last 5 events
            full_prompt = f"{context}\n\n{prompt}" if context else prompt

            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            self.logger.error(f"Gemini generation failed: {e}")
            return None

    def _log(self, text: str):
        """Add to transcript."""
        self.full_transcript.append(text)

    # Fallback methods when Gemini is not available
    def _fallback_game_start(self, state: "GameState") -> str:
        """Fallback game start message."""
        return (
            f"Welcome to The Traitors. {self.config.total_players} players have entered the castle. "
            f"Among them are {self.config.num_traitors} Traitors. "
            f"The game begins with ${state.prize_pot:,.0f} in the prize pot."
        )

    def _fallback_first_breakfast(self, state: "GameState") -> str:
        """Fallback first breakfast message."""
        return f"Day {state.day}: The players gather for breakfast. The game has begun."

    def _fallback_murder_reveal(self, victim_name: str, state: "GameState") -> str:
        """Fallback murder reveal message."""
        return f"Day {state.day}: {victim_name} has been murdered during the night."

    def _fallback_roundtable_open(self, state: "GameState") -> str:
        """Fallback Round Table opening."""
        return f"Day {state.day}: The Round Table begins. {len(state.alive_players)} players remain. Someone here is a Traitor."

    def _fallback_banishment(self, player, votes: Dict) -> str:
        """Fallback banishment message."""
        vote_count = sum(1 for v in votes.values() if v == player.id)
        return f"{player.name} received {vote_count} votes and has been banished. They were a {player.role.value.upper()}."

    def _fallback_finale(self, winner, state: "GameState") -> str:
        """Fallback finale message."""
        if winner.value == "faithful":
            winners = [p.name for p in state.alive_players if p.role.value == "faithful"]
            return f"The Faithful have won! {', '.join(winners)} will share ${state.prize_pot:,.0f}."
        else:
            winners = [p.name for p in state.alive_players if p.role.value == "traitor"]
            return f"The Traitors have won! {', '.join(winners)} will take ${state.prize_pot:,.0f}."
