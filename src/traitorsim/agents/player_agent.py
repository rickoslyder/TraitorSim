"""Player agent using Claude for decision-making."""

import logging
import re
from typing import List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.game_state import GameState, Player, Role
    from ..core.config import GameConfig

try:
    import anthropic
except ImportError:
    anthropic = None

from ..memory.memory_manager import MemoryManager
from .prompts.player_templates import PlayerPrompts


class PlayerAgent:
    """
    Individual player agent using Claude Agents SDK.
    Makes decisions based on role, personality, and memory.
    """

    def __init__(
        self, player: "Player", config: "GameConfig", game_state: "GameState"
    ):
        """Initialize player agent."""
        self.player = player
        self.config = config
        self.game_state = game_state
        self.logger = logging.getLogger(f"{__name__}.{player.name}")

        # Initialize Claude client
        if anthropic is None:
            self.logger.warning("anthropic not installed. Using fallback decisions.")
            self.client = None
        else:
            if not config.anthropic_api_key:
                self.logger.warning("No Anthropic API key provided. Using fallback decisions.")
                self.client = None
            else:
                try:
                    self.client = anthropic.Anthropic(api_key=config.anthropic_api_key)
                    self.logger.info(f"Claude client initialized for {player.name}")
                except Exception as e:
                    self.logger.error(f"Failed to initialize Claude: {e}")
                    self.client = None

        # Initialize memory system
        self.memory = MemoryManager(player, config)
        self.memory.initialize()

    def reflect_on_day(self):
        """Update internal state and suspicions."""
        try:
            # Read current memories
            observations = self.memory.get_recent_observations()

            # Generate reflection
            prompt = PlayerPrompts.daily_reflection(
                self.player, observations, self.game_state
            )

            reflection = self._think(prompt)

            if reflection:
                # Update memory
                self.memory.write_diary_entry(
                    day=self.game_state.day, phase="social", content=reflection
                )

                # Update suspicions in trust matrix (agent's view)
                self._update_suspicions(reflection)
                self.logger.debug(f"{self.player.name} reflected on day {self.game_state.day}")
        except Exception as e:
            self.logger.error(f"Failed to reflect: {e}")

    def cast_vote(self) -> str:
        """Decide who to vote for at Round Table."""
        try:
            # Get current suspicions
            suspicions = self.memory.get_suspicions()

            # Get alive players (can't vote for self or dead)
            candidates = [
                p.id for p in self.game_state.alive_players if p.id != self.player.id
            ]

            if not candidates:
                self.logger.warning("No candidates to vote for")
                return candidates[0] if candidates else ""

            # Generate voting decision
            prompt = PlayerPrompts.voting_decision(
                self.player, candidates, suspicions, self.game_state
            )

            response = self._think(prompt)

            # Extract vote from response (format: "VOTE: player_id")
            vote = self._extract_vote(response, candidates)

            # Log decision
            if response:
                self.memory.write_diary_entry(
                    day=self.game_state.day,
                    phase="roundtable",
                    content=f"Voted for {vote}. Reasoning: {response}",
                )

            self.logger.info(f"{self.player.name} votes for {vote}")
            return vote
        except Exception as e:
            self.logger.error(f"Failed to cast vote: {e}")
            # Fallback: vote for first candidate
            candidates = [
                p.id for p in self.game_state.alive_players if p.id != self.player.id
            ]
            return candidates[0] if candidates else ""

    def choose_murder_victim(self) -> str:
        """Traitors choose who to murder (only called if traitor)."""
        try:
            if self.player.role.value != "traitor":
                raise ValueError("Only traitors can murder")

            # Get alive faithful
            faithful = [p.id for p in self.game_state.alive_faithful]

            if not faithful:
                self.logger.warning("No faithful to murder")
                return ""

            # Strategic decision
            prompt = PlayerPrompts.murder_decision(
                self.player, faithful, self.game_state
            )

            response = self._think(prompt)
            victim = self._extract_vote(response, faithful)

            self.logger.info(f"{self.player.name} (Traitor) chooses to murder {victim}")
            return victim
        except Exception as e:
            self.logger.error(f"Failed to choose murder victim: {e}")
            # Fallback: random faithful
            faithful = [p.id for p in self.game_state.alive_faithful]
            return faithful[0] if faithful else ""

    def _think(self, prompt: str) -> Optional[str]:
        """Generate response using Claude."""
        if not self.client:
            return None

        try:
            # Build system prompt with personality and role
            system_prompt = PlayerPrompts.system_prompt(self.player)

            message = self.client.messages.create(
                model=self.config.claude_model,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )

            return message.content[0].text
        except Exception as e:
            self.logger.error(f"Claude generation failed: {e}")
            return None

    def _extract_vote(self, response: Optional[str], candidates: List[str]) -> str:
        """Extract vote from agent response."""
        if not response:
            # Fallback: return first candidate
            return candidates[0] if candidates else ""

        # Look for "VOTE: player_id" pattern
        match = re.search(r"VOTE:\s*(\S+)", response, re.IGNORECASE)
        if match:
            vote = match.group(1)
            # Validate it's a valid candidate
            if vote in candidates:
                return vote

        # Fallback: search for any candidate ID in response
        for candidate in candidates:
            if candidate in response:
                return candidate

        # Last resort: return first candidate
        return candidates[0] if candidates else ""

    def _update_suspicions(self, reflection: str):
        """Update trust matrix based on reflection."""
        if not reflection:
            return

        try:
            # MVP: Simple keyword-based updates
            # Full version would use structured output from Claude

            for player in self.game_state.alive_players:
                if player.id == self.player.id:
                    continue

                # Simple heuristic: if mentioned negatively, increase suspicion
                player_name_lower = player.name.lower()
                reflection_lower = reflection.lower()

                delta = 0.0

                if f"{player_name_lower} suspicious" in reflection_lower or \
                   f"{player_name_lower} is a traitor" in reflection_lower or \
                   f"suspect {player_name_lower}" in reflection_lower:
                    delta = 0.1
                elif f"{player_name_lower} trust" in reflection_lower or \
                     f"{player_name_lower} is faithful" in reflection_lower or \
                     f"trust {player_name_lower}" in reflection_lower:
                    delta = -0.1

                if delta != 0:
                    # Get current suspicion from trust matrix
                    current = self.game_state.trust_matrix.get_suspicion(
                        self.player.id, player.id
                    )
                    new_score = max(0.0, min(1.0, current + delta))

                    # Update both trust matrix and memory
                    self.game_state.trust_matrix.update_suspicion(
                        self.player.id, player.id, delta
                    )
                    self.memory.update_suspicion(player.id, player.name, new_score)
        except Exception as e:
            self.logger.error(f"Failed to update suspicions: {e}")
