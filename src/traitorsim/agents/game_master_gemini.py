"""Gemini-powered Game Master for TraitorSim.

This module implements the Game Master using Google's Gemini API with
ChatSession for conversation continuity across game phases.
"""

import os
from typing import List, Dict, Any, Optional

import google.generativeai as genai

from ..core.game_state import GameState, GamePhase
from ..core.enums import Role


class GameMasterGemini:
    """Gemini-powered Game Master with narrative generation.

    Uses Gemini's ChatSession to maintain full game transcript and
    generate dramatic, contextual narratives for each phase.
    """

    def __init__(
        self,
        game_state: GameState,
        api_key: Optional[str] = None,
        model_name: str = "gemini-3-flash-preview",
    ):
        """Initialize Game Master with Gemini.

        Args:
            game_state: Current game state (shared reference)
            api_key: Gemini API key (or from GEMINI_API_KEY env var)
            model_name: Gemini model to use
        """
        self.game_state = game_state
        self.model_name = model_name

        # Configure Gemini API
        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        else:
            print("Warning: No GEMINI_API_KEY found. GM narratives will be basic.")
            self.model = None
            self.chat = None
            return

        # Initialize model with system instruction
        try:
            self.model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=self._get_system_instruction(),
            )

            # Start chat session (maintains full conversation history)
            self.chat = self.model.start_chat()

        except Exception as e:
            print(f"Error initializing Gemini GM: {e}")
            self.model = None
            self.chat = None

    def _get_system_instruction(self) -> str:
        """Generate system instruction for Game Master role.

        Returns:
            System instruction string
        """
        return """You are the **Game Master** for "The Traitors", narrating a dramatic reality TV show.

**Your Role**:
- Generate dramatic, TV-style announcements for each game phase
- Build tension and suspense in your narration
- Reference past events to create narrative continuity
- Use evocative language that captures the show's atmosphere
- Keep announcements concise (2-4 sentences) but impactful

**Tone**: Mysterious, dramatic, suspenseful - like a reality TV host creating maximum drama.

**Style Examples**:
- Breakfast: "As dawn breaks over the castle, a chilling discovery awaits. Last night, the Traitors struck again..."
- Round Table: "The tension is palpable as the contestants gather. Tonight, one player's fate will be sealed..."
- Turret: "Under cover of darkness, the Traitors convene to select their next victim..."

Generate only the narration requested. Do not add meta-commentary or explanations."""

    async def announce_game_start_async(
        self, players: List[str], traitors: List[str], faithful: List[str]
    ) -> str:
        """Generate game start announcement.

        Args:
            players: List of all player names
            traitors: List of traitor names (for GM context only)
            faithful: List of faithful names (for GM context only)

        Returns:
            Opening narration
        """
        if not self.chat:
            return self._fallback_game_start(players)

        prompt = f"""Generate the opening announcement for "The Traitors" game.

**Context**:
- {len(players)} contestants have arrived
- {len(traitors)} Traitors among them: {', '.join(traitors)}
- {len(faithful)} innocent Faithfuls
- Prize pot starts at $0, grows with successful missions

Create a dramatic opening narration (2-3 sentences) welcoming contestants and hinting at the betrayal to come."""

        try:
            response = await self.chat.send_message_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error in announce_game_start_async: {e}")
            return self._fallback_game_start(players)

    async def announce_murder_async(self, victim_name: str, day: int) -> str:
        """Generate murder announcement for Breakfast phase.

        Args:
            victim_name: Name of murdered player
            day: Current day number

        Returns:
            Breakfast narration revealing the murder
        """
        if not self.chat:
            return self._fallback_murder(victim_name, day)

        prompt = f"""Generate the Breakfast phase announcement for Day {day}.

**Event**: {victim_name} was murdered by the Traitors last night.

Create a dramatic reveal (2-3 sentences) announcing this death to the remaining contestants."""

        try:
            response = await self.chat.send_message_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error in announce_murder_async: {e}")
            return self._fallback_murder(victim_name, day)

    async def describe_mission_async(
        self, mission_type: str, difficulty: float, day: int
    ) -> str:
        """Generate mission description.

        Args:
            mission_type: Type of mission (e.g., "Skill Check")
            difficulty: Mission difficulty (0.0-1.0)
            day: Current day number

        Returns:
            Mission phase narration
        """
        if not self.chat:
            return self._fallback_mission(mission_type, difficulty)

        difficulty_desc = "extremely difficult" if difficulty > 0.7 else "challenging" if difficulty > 0.5 else "moderate"

        prompt = f"""Generate the Mission phase announcement for Day {day}.

**Mission Details**:
- Type: {mission_type}
- Difficulty: {difficulty_desc}

Create a dramatic mission briefing (2-3 sentences) building tension around this challenge."""

        try:
            response = await self.chat.send_message_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error in describe_mission_async: {e}")
            return self._fallback_mission(mission_type, difficulty)

    async def announce_mission_result_async(
        self, success_rate: float, earnings: float, day: int
    ) -> str:
        """Generate mission result announcement.

        Args:
            success_rate: Percentage of players who succeeded (0.0-1.0)
            earnings: Amount added to prize pot
            day: Current day number

        Returns:
            Mission result narration
        """
        if not self.chat:
            return self._fallback_mission_result(success_rate, earnings)

        result = "succeeded" if success_rate >= 0.5 else "failed"

        prompt = f"""Generate the mission result announcement for Day {day}.

**Result**:
- Performance: {success_rate:.0%} success rate
- Outcome: Mission {result}
- Earnings: ${earnings:,.0f} added to prize pot

Create a dramatic announcement (2-3 sentences) revealing these results."""

        try:
            response = await self.chat.send_message_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error in announce_mission_result_async: {e}")
            return self._fallback_mission_result(success_rate, earnings)

    async def announce_banishment_async(
        self, banished_name: str, role: str, votes: Dict[str, int], day: int
    ) -> str:
        """Generate banishment announcement for Round Table.

        Args:
            banished_name: Name of banished player
            role: Revealed role ("traitor" or "faithful")
            votes: Vote counts per player
            day: Current day number

        Returns:
            Round Table narration with vote reveal
        """
        if not self.chat:
            return self._fallback_banishment(banished_name, role)

        prompt = f"""Generate the Round Table banishment announcement for Day {day}.

**Result**:
- Banished: {banished_name}
- Revealed role: {role.upper()}
- Vote count: {votes.get(banished_name, 0)} votes

Create a dramatic announcement (2-3 sentences) revealing the banishment and their true role."""

        try:
            response = await self.chat.send_message_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error in announce_banishment_async: {e}")
            return self._fallback_banishment(banished_name, role)

    async def announce_finale_async(self, winner: str, survivors: List[str]) -> str:
        """Generate finale announcement.

        Args:
            winner: Winning team ("FAITHFUL" or "TRAITOR")
            survivors: List of surviving player names

        Returns:
            Finale narration
        """
        if not self.chat:
            return self._fallback_finale(winner, survivors)

        prompt = f"""Generate the finale announcement for "The Traitors".

**Outcome**:
- Winners: {winner}S
- Survivors: {', '.join(survivors)}

Create a dramatic finale narration (3-4 sentences) wrapping up the game and declaring the victors."""

        try:
            response = await self.chat.send_message_async(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error in announce_finale_async: {e}")
            return self._fallback_finale(winner, survivors)

    # Fallback methods for when Gemini API is unavailable

    def _fallback_game_start(self, players: List[str]) -> str:
        """Fallback game start message."""
        return f"Welcome to The Traitors. {len(players)} contestants enter the castle, but betrayal lurks within..."

    def _fallback_murder(self, victim_name: str, day: int) -> str:
        """Fallback murder announcement."""
        return f"Day {day} - Breakfast: {victim_name} has been murdered by the Traitors."

    def _fallback_mission(self, mission_type: str, difficulty: float) -> str:
        """Fallback mission description."""
        return f"Today's mission: {mission_type}. Will the team work together, or will the Traitors sabotage?"

    def _fallback_mission_result(self, success_rate: float, earnings: float) -> str:
        """Fallback mission result."""
        result = "succeeded" if success_rate >= 0.5 else "failed"
        return f"The mission has {result}. ${earnings:,.0f} added to the prize pot."

    def _fallback_banishment(self, banished_name: str, role: str) -> str:
        """Fallback banishment announcement."""
        return f"{banished_name} has been banished. They were a {role.upper()}."

    def _fallback_finale(self, winner: str, survivors: List[str]) -> str:
        """Fallback finale announcement."""
        return f"The game is over. The {winner}S have won! Survivors: {', '.join(survivors)}"

    # Synchronous wrappers for backward compatibility

    def announce_game_start(
        self, players: List[str], traitors: List[str], faithful: List[str]
    ) -> str:
        """Synchronous version of announce_game_start_async."""
        import asyncio
        return asyncio.run(self.announce_game_start_async(players, traitors, faithful))

    def announce_murder(self, victim_name: str, day: int) -> str:
        """Synchronous version of announce_murder_async."""
        import asyncio
        return asyncio.run(self.announce_murder_async(victim_name, day))

    def describe_mission(self, mission_type: str, difficulty: float, day: int) -> str:
        """Synchronous version of describe_mission_async."""
        import asyncio
        return asyncio.run(self.describe_mission_async(mission_type, difficulty, day))

    def announce_mission_result(
        self, success_rate: float, earnings: float, day: int
    ) -> str:
        """Synchronous version of announce_mission_result_async."""
        import asyncio
        return asyncio.run(self.announce_mission_result_async(success_rate, earnings, day))

    def announce_banishment(
        self, banished_name: str, role: str, votes: Dict[str, int], day: int
    ) -> str:
        """Synchronous version of announce_banishment_async."""
        import asyncio
        return asyncio.run(self.announce_banishment_async(banished_name, role, votes, day))

    def announce_finale(self, winner: str, survivors: List[str]) -> str:
        """Synchronous version of announce_finale_async."""
        import asyncio
        return asyncio.run(self.announce_finale_async(winner, survivors))
