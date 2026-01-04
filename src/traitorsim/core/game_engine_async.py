"""Async game engine for TraitorSim using dual-SDK architecture.

This engine orchestrates the complete game loop using:
- Claude Agent SDK for player agents (with MCP tools)
- Gemini Interactions API for Game Master (with server-side state)
- Async/parallel execution for performance
"""

import asyncio
import os
import random
from typing import List, Dict, Optional, Set, Tuple
from collections import Counter

from ..agents.player_agent_sdk import PlayerAgentSDK
from ..agents.game_master_interactions import GameMasterInteractions
from ..core.game_state import GameState, Player, Role
from ..core.config import GameConfig
from ..core.enums import GamePhase
from ..memory.memory_manager import MemoryManager
from ..missions.skill_check import SkillCheckMission
from ..utils.logger import setup_logger


class GameEngineAsync:
    """Async game engine orchestrating player agents and game master.

    Uses dual-SDK architecture:
    - PlayerAgentSDK (Claude) for autonomous strategic decisions
    - GameMasterInteractions (Gemini) for dramatic narratives
    """

    def __init__(self, config: Optional[GameConfig] = None):
        """Initialize async game engine.

        Args:
            config: Game configuration (uses defaults if None)
        """
        self.config = config or GameConfig()
        self.game_state = GameState()
        self.logger = setup_logger("game_engine")

        # Initialize Game Master
        self.gm = GameMasterInteractions(
            self.game_state,
            api_key=self.config.gemini_api_key or os.getenv("GEMINI_API_KEY"),
            model_name=self.config.gemini_model,
            world_bible_path=self.config.world_bible_path,
        )

        # Player agents (created after game state init)
        self.player_agents: Dict[str, PlayerAgentSDK] = {}

        # Memory managers
        self.memory_managers: Dict[str, MemoryManager] = {}

    def _initialize_players(self) -> None:
        """Initialize players and assign roles using persona library."""
        import random
        from ..persona.persona_loader import PersonaLoader

        # Load personas from library
        if self.config.personality_generation == "archetype":
            try:
                loader = PersonaLoader(self.config.persona_library_path)
                personas = loader.sample_personas(
                    count=self.config.total_players,
                    ensure_diversity=True,
                    max_per_archetype=2
                )
                self.logger.info(f"Loaded {len(personas)} personas from library")

                # Create players from persona cards
                for i, persona in enumerate(personas):
                    player = Player(
                        id=f"player_{i:02d}",
                        name=persona.get("name", f"Player{i+1}"),
                        role=Role.FAITHFUL,  # Default, will reassign
                        personality=persona.get("personality", {
                            "openness": 0.5,
                            "conscientiousness": 0.5,
                            "extraversion": 0.5,
                            "agreeableness": 0.5,
                            "neuroticism": 0.5,
                        }),
                        stats=persona.get("stats", {
                            "intellect": 0.5,
                            "dexterity": 0.5,
                            "social_influence": 0.5,
                        }),
                        archetype_id=persona.get("archetype"),
                        archetype_name=persona.get("archetype_name"),
                        demographics=persona.get("demographics", {}),
                        backstory=persona.get("backstory"),
                        strategic_profile=persona.get("strategic_approach"),
                    )
                    self.game_state.players.append(player)

            except (FileNotFoundError, ValueError) as e:
                self.logger.error(f"Failed to load persona library: {e}")
                self.logger.error("Falling back to random personality generation")
                self._initialize_random_players()
        else:
            self._initialize_random_players()

        # Assign traitor roles
        traitor_indices = random.sample(
            range(self.config.total_players), self.config.num_traitors
        )
        for idx in traitor_indices:
            self.game_state.players[idx].role = Role.TRAITOR

        # Initialize trust matrix
        from ..core.game_state import TrustMatrix

        player_ids = [p.id for p in self.game_state.players]
        self.game_state.trust_matrix = TrustMatrix(player_ids)

        # Create player agents
        for player in self.game_state.players:
            # Create memory manager
            memory_manager = MemoryManager(player, self.config)
            memory_manager.initialize()
            self.memory_managers[player.id] = memory_manager

            # Create agent
            agent = PlayerAgentSDK(player, self.game_state, memory_manager)
            self.player_agents[player.id] = agent

        self.logger.info(f"Initialized {len(self.game_state.players)} players")
        self.logger.info(
            f"Traitors: {[p.name for p in self.game_state.players if p.role == Role.TRAITOR]}"
        )

        # Log archetype distribution if using personas
        if self.config.personality_generation == "archetype":
            archetypes = [p.archetype_name for p in self.game_state.players if p.archetype_name]
            if archetypes:
                self.logger.info(f"Archetypes in play: {set(archetypes)}")

    def _initialize_random_players(self) -> None:
        """Fallback: Initialize players with random personalities."""
        import random

        self.logger.warning("Using random personality generation (no persona library)")

        for i in range(self.config.total_players):
            player = Player(
                id=f"player_{i:02d}",
                name=f"Player{i+1}",
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
            self.game_state.players.append(player)

    async def run_game_async(self) -> str:
        """Run complete game asynchronously.

        Returns:
            Winner ("FAITHFUL" or "TRAITOR")
        """
        self.logger.info("=== TraitorSim Game Starting ===")

        # Initialize players
        self._initialize_players()

        # Game start announcement
        all_names = [p.name for p in self.game_state.players]
        traitor_names = [p.name for p in self.game_state.players if p.role == Role.TRAITOR]
        faithful_names = [p.name for p in self.game_state.players if p.role == Role.FAITHFUL]

        opening = await self.gm.announce_game_start_async(
            all_names, traitor_names, faithful_names
        )
        self.logger.info(f"\n{opening}\n")

        # Main game loop starts with Day 1 containing the first mission/roundtable
        # (Traitors are selected before this point per show canon; first breakfast
        # to reveal a murder happens on Day 2).
        self.game_state.day = 1

        while self.game_state.day <= self.config.max_days:
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"DAY {self.game_state.day}")
            self.logger.info(f"{'='*60}\n")

            # In the real format, Day 1 starts with introductions/mission and no
            # overnight murder to reveal. Breakfast begins on Day 2.
            if self.game_state.day > 1:
                await self._run_breakfast_phase_async()

                winner = self.game_state.check_win_condition()
                if winner:
                    break

            await self._run_mission_phase_async()

            await self._run_social_phase_async()

            await self._run_roundtable_phase_async()

            winner = self.game_state.check_win_condition()
            if winner:
                break

            await self._run_turret_phase_async()

            # Check win condition
            winner = self.game_state.check_win_condition()
            if winner:
                break

            self.game_state.day += 1

        # Finale
        winner = self.game_state.check_win_condition()
        if not winner:
            self.logger.warning(f"Game reached max days ({self.config.max_days})")
            winner = Role.FAITHFUL if len(self.game_state.alive_traitors) == 0 else Role.TRAITOR

        survivors = [p.name for p in self.game_state.alive_players]
        finale = await self.gm.announce_finale_async(winner.value.upper(), survivors)

        self.logger.info(f"\n{'='*60}")
        self.logger.info(finale)
        self.logger.info(f"{'='*60}\n")

        return winner.value.upper()

    async def _run_breakfast_phase_async(self) -> None:
        """Breakfast phase: Announce murder victim."""
        self.game_state.phase = GamePhase.BREAKFAST
        self.logger.info("--- Breakfast Phase ---")

        if self.game_state.last_murder_victim:
            narrative = await self.gm.announce_murder_async(
                self.game_state.last_murder_victim, self.game_state.day
            )
            self.logger.info(narrative)

            # Agents reflect on murder
            events = [f"{self.game_state.last_murder_victim} was murdered"]
            await self._parallel_reflection_async(events)

            # Clear last murder victim to avoid stale announcements
            self.game_state.last_murder_victim = None
        else:
            self.logger.info("No murder last night.")

    async def _run_mission_phase_async(self) -> None:
        """Mission phase: Execute mission challenge."""
        self.game_state.phase = GamePhase.MISSION
        self.logger.info("\n--- Mission Phase ---")

        # Create mission
        mission = SkillCheckMission(self.game_state, self.config)

        # GM describes mission
        narrative = await self.gm.describe_mission_async(
            "Skill Check", self.config.mission_difficulty, self.game_state.day
        )
        self.logger.info(narrative)

        # Execute mission
        result = mission.execute()

        # Update prize pot
        self.game_state.prize_pot += result.earnings

        # GM announces results
        success_rate = sum(result.performance_scores.values()) / len(
            result.performance_scores
        )
        result_narrative = await self.gm.announce_mission_result_async(
            success_rate, result.earnings, self.game_state.day
        )
        self.logger.info(result_narrative)
        self.logger.info(f"Prize pot: ${self.game_state.prize_pot:,.0f}")

        # Agents reflect on mission
        events = [
            f"Mission {'succeeded' if success_rate >= 0.5 else 'failed'}",
            f"${result.earnings:,.0f} added to pot",
        ]
        await self._parallel_reflection_async(events)

    async def _run_social_phase_async(self) -> None:
        """Social phase: Agents reflect privately."""
        self.game_state.phase = GamePhase.SOCIAL
        self.logger.info("\n--- Social Phase ---")

        events = ["Private reflection time"]
        await self._parallel_reflection_async(events)

    async def _run_roundtable_phase_async(self) -> None:
        """Round Table phase: Voting and banishment."""
        self.game_state.phase = GamePhase.ROUNDTABLE
        self.logger.info("\n--- Round Table Phase ---")

        # Collect votes in parallel
        initial_votes = await self._collect_votes_parallel_async()

        # Tally votes
        vote_counts = Counter(initial_votes.values())
        if not vote_counts:
            self.logger.warning("No votes were cast. Skipping banishment.")
            return

        # Resolve any ties (UK/US style: revote among tied, then random fallback)
        banished_id, final_votes, tie_info = await self._resolve_vote_tie_async(
            vote_counts, initial_votes
        )

        # Get player
        banished_player = self.game_state.get_player(banished_id)
        if not banished_player:
            self.logger.error(f"Invalid banished player: {banished_id}")
            return

        # Banish player
        banished_player.alive = False
        self.game_state.banished_players.append(banished_player.name)

        # GM announces banishment
        final_vote_counts = Counter(final_votes.values())
        narrative = await self.gm.announce_banishment_async(
            banished_player.name,
            banished_player.role.value,
            dict(final_vote_counts),
            self.game_state.day,
            banished_id=banished_player.id,
        )
        self.logger.info(narrative)

        # Log votes
        for voter_id, target_id in final_votes.items():
            voter = self.game_state.get_player(voter_id)
            target = self.game_state.get_player(target_id)
            if voter and target:
                self.logger.info(f"  {voter.name} voted for {target.name}")

        # Agents reflect
        events = [
            f"{banished_player.name} was banished",
            f"They were a {banished_player.role.value.upper()}",
        ]
        if tie_info.get("random_resolution"):
            events.append(
                f"Tie between {', '.join(tie_info['tied_names'])} resolved randomly after revote"
            )
        elif tie_info.get("revote_triggered"):
            events.append("Revote among tied players decided the banishment")
        await self._parallel_reflection_async(events)

    async def _run_turret_phase_async(self) -> None:
        """Turret phase: Traitors murder a Faithful."""
        self.game_state.phase = GamePhase.TURRET
        self.logger.info("\n--- Turret Phase ---")

        # Get alive traitors
        alive_traitors = [a for a in self.player_agents.values() if a.player.alive and a.player.role == Role.TRAITOR]

        if not alive_traitors:
            self.logger.info("No traitors alive to murder.")
            self.game_state.last_murder_victim = None
            return

        # First traitor chooses (simplified - no conferencing in MVP)
        traitor_agent = alive_traitors[0]

        victim_id = await traitor_agent.choose_murder_victim_async()

        if not victim_id:
            self.logger.warning("No murder victim chosen")
            self.game_state.last_murder_victim = None
            return

        victim = self.game_state.get_player(victim_id)
        if not victim:
            self.logger.error(f"Invalid victim: {victim_id}")
            self.game_state.last_murder_victim = None
            return

        # Murder victim
        victim.alive = False
        self.game_state.murdered_players.append(victim.name)
        self.game_state.last_murder_victim = victim.name

        self.logger.info(f"Traitors murdered: {victim.name}")

    async def _collect_votes_parallel_async(
        self, allowed_targets: Optional[Set[str]] = None
    ) -> Dict[str, str]:
        """Collect votes from all alive players in parallel.

        Args:
            allowed_targets: Optional set of valid target IDs (for revotes among tied players)

        Returns:
            Dict mapping player_id -> voted_player_id
        """
        alive_agents = [
            (pid, agent)
            for pid, agent in self.player_agents.items()
            if agent.player.alive
        ]

        # Create vote tasks
        async def vote_with_fallback(player_id: str, agent: PlayerAgentSDK) -> Tuple[str, str]:
            """Vote with error handling."""
            try:
                target = await agent.cast_vote_async()
                if target and (allowed_targets is None or target in allowed_targets):
                    return (player_id, target)
                if target and allowed_targets is not None and target not in allowed_targets:
                    self.logger.info(
                        f"{agent.player.name} voted for {target} outside tied candidates; "
                        "selecting from tied candidates instead."
                    )
                return (player_id, self._emergency_vote(player_id, allowed_targets))
            except Exception as e:
                self.logger.error(f"Error getting vote from {agent.player.name}: {e}")
                return (player_id, self._emergency_vote(player_id, allowed_targets))

        # Execute votes in parallel
        vote_tasks = [vote_with_fallback(pid, agent) for pid, agent in alive_agents]
        vote_results = await asyncio.gather(*vote_tasks)

        # Convert to dict
        votes = {pid: target for pid, target in vote_results}

        return votes

    async def _resolve_vote_tie_async(
        self, vote_counts: Counter, initial_votes: Dict[str, str]
    ) -> Tuple[str, Dict[str, str], Dict]:
        """Resolve voting ties using UK/US style revote, then random fallback.

        Args:
            vote_counts: Counter of votes per player
            initial_votes: Original votes dict

        Returns:
            Tuple of (banished_id, final_votes, tie_info_dict)
        """
        top_votes = vote_counts.most_common()
        highest_count = top_votes[0][1]
        tied_ids = [player_id for player_id, count in vote_counts.items() if count == highest_count]

        tie_info: Dict = {"revote_triggered": False, "random_resolution": False, "tied_names": []}

        # No tie - return winner directly
        if len(tied_ids) == 1:
            return tied_ids[0], initial_votes, tie_info

        # TIE DETECTED - Initiate revote among tied players
        tie_info["revote_triggered"] = True
        tied_names = [
            self.game_state.get_player(pid).name if self.game_state.get_player(pid) else pid
            for pid in tied_ids
        ]
        tie_info["tied_names"] = tied_names

        self.logger.info(
            f"⚖️  Tie detected: {', '.join(tied_names)} with {highest_count} votes each. "
            "Initiating revote among tied players."
        )

        # Revote - only votes for tied players count
        revote = await self._collect_votes_parallel_async(set(tied_ids))
        revote_counts = Counter(revote.values())

        top_revotes = revote_counts.most_common()
        highest_revote = top_revotes[0][1]
        still_tied_ids = [player_id for player_id, count in revote_counts.items() if count == highest_revote]

        # Check if tie persists after revote
        if len(still_tied_ids) > 1:
            tie_info["random_resolution"] = True
            banished_id = random.choice(still_tied_ids)
            still_tied_names = [
                self.game_state.get_player(pid).name if self.game_state.get_player(pid) else pid
                for pid in still_tied_ids
            ]
            tie_info["tied_names"] = still_tied_names
            banished_name = (
                self.game_state.get_player(banished_id).name
                if self.game_state.get_player(banished_id) else banished_id
            )
            self.logger.info(
                f"⚖️  Tie persisted after revote between {', '.join(still_tied_names)}. "
                f"Selecting {banished_name} at random per fallback rules."
            )
        else:
            banished_id = top_revotes[0][0]

        return banished_id, revote, tie_info

    async def _parallel_reflection_async(self, events: List[str]) -> None:
        """Have all alive agents reflect on events in parallel.

        Args:
            events: List of event descriptions
        """
        alive_agents = [
            agent for agent in self.player_agents.values() if agent.player.alive
        ]

        # Create reflection tasks
        reflection_tasks = [agent.reflect_on_day_async(events) for agent in alive_agents]

        # Execute in parallel
        await asyncio.gather(*reflection_tasks, return_exceptions=True)

    def _emergency_vote(
        self, player_id: str, allowed_targets: Optional[Set[str]] = None
    ) -> str:
        """Emergency fallback vote.

        Args:
            player_id: ID of voting player
            allowed_targets: Optional set of valid target IDs (for revotes)

        Returns:
            Random valid target
        """
        valid_targets = [
            p.id
            for p in self.game_state.alive_players
            if p.id != player_id and (allowed_targets is None or p.id in allowed_targets)
        ]
        return random.choice(valid_targets) if valid_targets else player_id

    # Synchronous wrapper
    def run_game(self) -> str:
        """Synchronous wrapper for run_game_async."""
        return asyncio.run(self.run_game_async())
