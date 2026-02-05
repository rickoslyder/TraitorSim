"""Async game engine for TraitorSim using dual-SDK architecture.

This engine orchestrates the complete game loop using:
- Claude Agent SDK for player agents (with MCP tools)
- Gemini Interactions API for Game Master (with server-side state)
- Async/parallel execution for performance
"""

import asyncio
import os
import random
from typing import List, Dict, Optional, Set, Tuple, Any
from collections import Counter

from ..agents.player_agent_sdk import PlayerAgentSDK
from ..agents.game_master_interactions import GameMasterInteractions
from ..core.game_state import GameState, Player, Role
from ..core.config import GameConfig
from ..core.enums import GamePhase
from ..memory.memory_manager import MemoryManager
from ..missions import MISSION_TYPES, MISSION_NAMES
from ..utils.logger import setup_logger
from ..voice import create_voice_emitter, VoiceMode


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

        # Create voice emitter if enabled
        self.voice_emitter = create_voice_emitter(
            mode=VoiceMode(self.config.voice_mode)
            if self.config.voice_mode != "disabled"
            else VoiceMode.DISABLED
        )
        if self.voice_emitter.is_enabled():
            self.logger.info(f"🎤 Voice mode: {self.config.voice_mode}")

        # Store voice emitter on game_state for access by other components
        self.game_state.voice_emitter = self.voice_emitter

        # Initialize Game Master
        self.gm = GameMasterInteractions(
            self.game_state,
            api_key=self.config.gemini_api_key or os.getenv("GEMINI_API_KEY"),
            model_name=self.config.gemini_model,
            world_bible_path=self.config.world_bible_path,
            voice_emitter=self.voice_emitter,
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

            # Create agent with config for model provider settings
            agent = PlayerAgentSDK(player, self.game_state, memory_manager, config=self.config)
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
                self.game_state.capture_trust_snapshot("breakfast")

                winner = self.game_state.check_win_condition()
                if winner:
                    break

            await self._run_mission_phase_async()
            self.game_state.capture_trust_snapshot("mission")

            await self._run_social_phase_async()
            self.game_state.capture_trust_snapshot("social")

            await self._run_roundtable_phase_async()
            self.game_state.capture_trust_snapshot("roundtable")

            winner = self.game_state.check_win_condition()
            if winner:
                break

            await self._run_turret_phase_async()
            self.game_state.capture_trust_snapshot("turret")

            # Check win condition
            winner = self.game_state.check_win_condition()
            if winner:
                break

            # Check for end game trigger (Final N players)
            alive_count = len(self.game_state.alive_players)
            if alive_count <= self.config.final_player_count and alive_count > 0:
                winner = await self._run_end_game_async()
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

        # Save complete game report for UI visualization
        try:
            report_path = self.save_game_report()
            self.logger.info(f"📊 Game report saved: {report_path}")
        except Exception as e:
            self.logger.error(f"Failed to save game report: {e}")

        return winner.value.upper()

    async def _run_breakfast_phase_async(self) -> None:
        """Breakfast phase: Announce murder victim."""
        self.game_state.phase = GamePhase.BREAKFAST
        self.logger.info("--- Breakfast Phase ---")

        # Generate breakfast entry order (dramatic if enabled)
        breakfast_order = self._generate_breakfast_entry_order()
        self.game_state.breakfast_order_history.append(breakfast_order)

        if self.config.enable_dramatic_entry and len(breakfast_order) > 0:
            breakfast_names = [
                self.game_state.get_player(pid).name
                for pid in breakfast_order
                if self.game_state.get_player(pid)
            ]
            self.logger.info(f"Breakfast entry order: {', '.join(breakfast_names)}")

        # Record structured BREAKFAST_ORDER event for UI
        last_player_id = breakfast_order[-1] if breakfast_order else None
        self.game_state.add_event(
            event_type="BREAKFAST_ORDER",
            phase="breakfast",
            data={
                "order": breakfast_order,
                "last_to_arrive": last_player_id,
                "victim_revealed": self.game_state.last_murder_victim,
            },
            narrative=(
                "Players arrived at breakfast. "
                f"{'Murder discovered!' if self.game_state.last_murder_victim else 'No murder last night.'}"
            ),
        )

        if self.game_state.last_murder_victim:
            narrative = await self.gm.announce_murder_async(
                self.game_state.last_murder_victim, self.game_state.day
            )
            self.logger.info(narrative)

            # Agents reflect on murder
            events = [f"{self.game_state.last_murder_victim} was murdered"]
            if self.config.enable_dramatic_entry and len(breakfast_order) > 0:
                last_player = self.game_state.get_player(breakfast_order[-1])
                if last_player:
                    events.append(f"{last_player.name} entered breakfast last (potential Tell)")
            await self._parallel_reflection_async(events)

            # Clear last murder victim to avoid stale announcements
            self.game_state.last_murder_victim = None
        else:
            self.logger.info("No murder last night.")

    def _generate_breakfast_entry_order(self) -> List[str]:
        """Generate breakfast entry order (dramatic or random)."""
        alive = self.game_state.alive_players
        if len(alive) == 0:
            return []

        player_ids = [p.id for p in alive]

        if not self.config.enable_dramatic_entry:
            random.shuffle(player_ids)
            return player_ids

        discussion_targets = self.game_state.last_murder_discussion.copy()

        # Occasionally add a Traitor for misdirection
        alive_traitors = [p for p in alive if p.role == Role.TRAITOR]
        if alive_traitors and random.random() < 0.3:
            traitor_to_add = random.choice(alive_traitors)
            if traitor_to_add.id not in discussion_targets:
                discussion_targets.append(traitor_to_add.id)

        early_arrivals = [pid for pid in player_ids if pid not in discussion_targets]
        late_arrivals = [pid for pid in discussion_targets if pid in player_ids]

        random.shuffle(early_arrivals)
        random.shuffle(late_arrivals)

        return early_arrivals + late_arrivals

    async def _run_mission_phase_async(self) -> None:
        """Mission phase: Execute mission challenge."""
        self.game_state.phase = GamePhase.MISSION
        self.logger.info("\n--- Mission Phase ---")

        # Select random mission type for variety
        mission_class = random.choice(MISSION_TYPES)
        mission = mission_class(self.game_state, self.config)
        mission_name = MISSION_NAMES.get(mission_class, "Challenge")

        self.logger.info(f"Today's mission: {mission_name}")

        # GM describes mission
        narrative = await self.gm.describe_mission_async(
            mission_name, self.config.mission_difficulty, self.game_state.day
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

        # Record structured MISSION_COMPLETE event for UI
        self.game_state.add_event(
            event_type="MISSION_COMPLETE",
            phase="mission",
            data={
                "mission_name": mission_name,
                "success": success_rate >= 0.5,
                "success_rate": success_rate,
                "earnings": result.earnings,
                "participants": [p.id for p in self.game_state.alive_players],
                "performance_scores": result.performance_scores,
            },
            narrative=(
                f"Mission {'succeeded' if success_rate >= 0.5 else 'failed'}. "
                f"${result.earnings:,.0f} added to prize pot."
            ),
        )

        # Award Shield and Dagger based on performance
        if self.config.enable_shields:
            await self._award_shield_and_dagger(result.performance_scores)

        # Award Seer power if available (UK/US style - top performer)
        if self.config.enable_seer and self.game_state.day >= self.config.seer_available_day:
            await self._award_seer_power(result.performance_scores)

        # Agents reflect on mission
        events = [
            f"Mission {'succeeded' if success_rate >= 0.5 else 'failed'}",
            f"${result.earnings:,.0f} added to pot",
        ]
        await self._parallel_reflection_async(events)

    async def _run_social_phase_async(self) -> None:
        """Social phase: Agents reflect privately. Seer may use power."""
        self.game_state.phase = GamePhase.SOCIAL
        self.logger.info("\n--- Social Phase ---")

        # Check if anyone has Seer power and wants to use it
        for player in self.game_state.alive_players:
            if getattr(player, 'has_seer', False):
                # Seer holder can use their power during social phase
                await self._use_seer_power_async(player)

        events = ["Private reflection time"]
        await self._parallel_reflection_async(events)

    async def _award_shield_and_dagger(self, performance_scores: Dict[str, float]) -> None:
        """Award Shield or Dagger to mission winner based on config."""
        if len(performance_scores) < 1:
            return

        sorted_performers = sorted(
            performance_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        winner_id = sorted_performers[0][0]
        winner = self.game_state.get_player(winner_id)
        if not winner:
            return

        dagger_mode = getattr(self.config, 'dagger_mode', 'rare')
        dagger_days = getattr(self.config, 'dagger_mission_days', (4, 8))
        current_day = self.game_state.day

        if dagger_mode == "never":
            self._award_shield(winner)
        elif dagger_mode == "rare":
            if current_day in dagger_days:
                choice = self._choose_shield_or_dagger(winner)
                if choice == "dagger":
                    self._award_dagger(winner)
                    self.logger.info(f"🗡️  {winner.name} chose the DAGGER over the Shield!")
                else:
                    self._award_shield(winner)
                    self.logger.info(f"🛡️  {winner.name} chose the SHIELD over the Dagger!")
            else:
                self._award_shield(winner)
        elif dagger_mode == "every_mission":
            self._award_shield(winner)
            if len(sorted_performers) >= 2:
                second_id = sorted_performers[1][0]
                second_winner = self.game_state.get_player(second_id)
                if second_winner:
                    self._award_dagger(second_winner)

    def _award_shield(self, player: Player) -> None:
        """Award Shield to a player."""
        player.has_shield = True
        self.game_state.shield_holder = player.name
        if self.config.shield_visibility == "public":
            self.logger.info(f"🛡️  {player.name} won the SHIELD!")
        else:
            self.logger.info("🛡️  Shield awarded (secret)")

        self.game_state.add_event(
            event_type="SHIELD_AWARDED",
            phase="mission",
            target=player.id,
            data={"winner_name": player.name},
            narrative=f"{player.name} received the Shield.",
        )

    def _award_dagger(self, player: Player) -> None:
        """Award Dagger to a player."""
        player.has_dagger = True
        self.game_state.dagger_holder = player.name
        self.logger.info(f"🗡️  {player.name} won the DAGGER!")

        self.game_state.add_event(
            event_type="DAGGER_AWARDED",
            phase="mission",
            target=player.id,
            data={"winner_name": player.name},
            narrative=f"{player.name} received the Dagger.",
        )

    def _choose_shield_or_dagger(self, player: Player) -> str:
        """AI player chooses between Shield and Dagger."""
        if player.role == Role.TRAITOR:
            return "dagger" if random.random() < 0.70 else "shield"

        neuroticism = player.personality.get("neuroticism", 0.5)
        extraversion = player.personality.get("extraversion", 0.5)

        dagger_preference = (extraversion * 0.4) - (neuroticism * 0.3) + 0.3

        return "dagger" if random.random() < dagger_preference else "shield"

    async def _award_seer_power(self, performance_scores: Dict[str, float]) -> None:
        """Award Seer power to top mission performer.

        Seer power (UK Series 3+, US Season 3+) allows one player to
        privately confirm another contestant's true role (Traitor or Faithful).

        Args:
            performance_scores: Dict mapping player_id -> performance (0.0-1.0)
        """
        # Only award if Seer is enabled and available
        if not self.config.enable_seer:
            return
        if self.game_state.day < self.config.seer_available_day:
            return
        # Only award if no one currently has Seer
        if getattr(self.game_state, 'seer_holder', None):
            return
        if len(performance_scores) < 1:
            return

        # Top performer gets Seer
        sorted_performers = sorted(
            performance_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        winner_id = sorted_performers[0][0]
        winner = self.game_state.get_player(winner_id)
        if not winner:
            return

        winner.has_seer = True
        self.game_state.seer_holder = winner.name

        self.logger.info(f"👁️  {winner.name} won the SEER POWER!")
        self.logger.info(f"   They can privately confirm one player's true role.")

        self.game_state.add_event(
            event_type="SEER_AWARDED",
            phase="mission",
            target=winner.id,
            data={"winner_name": winner.name},
            narrative=f"{winner.name} received the Seer power.",
        )

    async def _use_seer_power_async(self, seer_player: Player) -> None:
        """Allow Seer holder to use their power.

        The Seer chooses a target and learns their true role.

        Args:
            seer_player: Player with Seer power
        """
        self.logger.info(f"\n👁️  SEER POWER: {seer_player.name} uses their ability")

        # Get target - use agent if available, otherwise pick highest suspicion
        agent = self.player_agents.get(seer_player.id)
        target_id = None

        if agent:
            # Use agent's suspicion to pick target
            suspicions = agent.memory_manager.get_suspicions() if agent.memory_manager else {}
            if suspicions:
                # Pick player with highest suspicion that we're uncertain about (0.3-0.7 range)
                uncertain = {pid: sus for pid, sus in suspicions.items()
                            if 0.3 <= sus <= 0.7 and pid != seer_player.id}
                if uncertain:
                    target_id = max(uncertain, key=uncertain.get)

        # Fallback: random target
        if not target_id:
            valid_targets = [p.id for p in self.game_state.alive_players if p.id != seer_player.id]
            target_id = random.choice(valid_targets) if valid_targets else None

        if not target_id:
            self.logger.warning("Seer failed to choose target")
            return

        target_player = self.game_state.get_player(target_id)
        if not target_player:
            self.logger.error(f"Invalid Seer target: {target_id}")
            return

        # Reveal the truth to the Seer
        true_role = target_player.role.value.upper()
        self.logger.info(f"👁️  {seer_player.name} learns: {target_player.name} is a {true_role}")

        self.game_state.add_event(
            event_type="SEER_USED",
            phase="social",
            actor=seer_player.id,
            target=target_player.id,
            data={"target_name": target_player.name, "true_role": true_role},
            narrative=f"{seer_player.name} used the Seer power on {target_player.name}.",
        )

        # Update agent's suspicion based on truth
        if agent and agent.memory_manager:
            new_suspicion = 1.0 if true_role == "TRAITOR" else 0.0
            agent.memory_manager.update_suspicion(
                target_id,
                target_player.name,
                new_suspicion,
                "Seer power revealed true role",
            )
            self.logger.info(f"   Updated suspicion of {target_player.name} to {new_suspicion}")

        # Consume the Seer power (one-time use)
        seer_player.has_seer = False
        self.game_state.seer_holder = None

        # Public announcement (vague - both can fabricate)
        self.logger.info(f"   {seer_player.name} and {target_player.name} had a private meeting...")
        self.logger.info(f"   What was revealed? Only they know for sure.")

    async def _run_roundtable_phase_async(self) -> None:
        """Round Table phase: Voting and banishment."""
        self.game_state.phase = GamePhase.ROUNDTABLE
        self.logger.info("\n--- Round Table Phase ---")

        # Collect votes in parallel
        initial_votes = await self._collect_votes_parallel_async()

        # Tally votes (accounting for Dagger double-vote)
        vote_counts = self._tally_votes(initial_votes, log_dagger=True)

        if not vote_counts:
            self.logger.warning("No votes were cast. Skipping banishment.")
            return

        # Resolve any ties
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

        # Consume all Daggers after use
        for player in self.game_state.players:
            if getattr(player, 'has_dagger', False):
                player.has_dagger = False

        # Determine if we should reveal role (2025 rule: no reveal in endgame)
        alive_count = len(list(self.game_state.alive_players))
        is_endgame = alive_count <= self.config.final_player_count
        should_reveal_role = self.config.endgame_reveal_roles or not is_endgame

        # GM announces banishment
        final_vote_counts = self._tally_votes(final_votes, log_dagger=False)
        if should_reveal_role:
            narrative = await self.gm.announce_banishment_async(
                banished_player.name,
                banished_player.role.value,
                dict(final_vote_counts),
                self.game_state.day,
                banished_id=banished_player.id,
            )
        else:
            # 2025 rule: Don't reveal role in endgame
            narrative = await self.gm.announce_banishment_async(
                banished_player.name,
                "UNKNOWN",  # Role hidden
                dict(final_vote_counts),
                self.game_state.day,
                banished_id=banished_player.id,
            )
            self.logger.info(f"🔒 2025 RULE: {banished_player.name}'s role is NOT revealed!")
        self.logger.info(narrative)

        # Record votes in history (for countback tie-breaking)
        self.game_state.vote_history.append(final_votes.copy())

        # Log votes
        for voter_id, target_id in final_votes.items():
            voter = self.game_state.get_player(voter_id)
            target = self.game_state.get_player(target_id)
            if voter and target:
                self.logger.info(f"  {voter.name} voted for {target.name}")

        # Agents reflect
        if should_reveal_role:
            events = [
                f"{banished_player.name} was banished",
                f"They were a {banished_player.role.value.upper()}",
            ]
        else:
            events = [
                f"{banished_player.name} was banished",
                "Their role was NOT revealed (2025 endgame rule)",
            ]
        if tie_info.get("random_resolution"):
            events.append(
                f"Tie between {', '.join(tie_info['tied_names'])} resolved randomly after revote"
            )
        elif tie_info.get("revote_triggered"):
            events.append("Revote among tied players decided the banishment")
        await self._parallel_reflection_async(events)

        # Record structured VOTE_TALLY event for UI
        self.game_state.add_event(
            event_type="VOTE_TALLY",
            phase="roundtable",
            target=banished_id,
            data={
                "votes": final_votes.copy(),
                "tally": dict(final_vote_counts),
                "eliminated": banished_id,
                "eliminated_name": banished_player.name,
                "eliminated_role": banished_player.role.value,
            },
            narrative=f"{banished_player.name} was banished with {final_vote_counts[banished_id]} votes.",
        )

        # Check for recruitment (if a Traitor was banished)
        if self.config.enable_recruitment and banished_player.role == Role.TRAITOR:
            await self._handle_recruitment_async()

    async def _run_turret_phase_async(self) -> None:
        """Turret phase: Traitors murder a Faithful."""
        self.game_state.phase = GamePhase.TURRET
        self.logger.info("\n--- Turret Phase ---")

        # Get alive traitors and faithful
        alive_traitors = [a for a in self.player_agents.values() if a.player.alive and a.player.role == Role.TRAITOR]
        alive_faithful = [p for p in self.game_state.alive_players if p.role == Role.FAITHFUL]

        if not alive_traitors:
            self.logger.info("No traitors alive to murder.")
            self.game_state.last_murder_victim = None
            return

        # Death List mechanic (optional)
        death_list = None
        if self.config.enable_death_list and alive_faithful:
            death_list = await self._create_death_list_async(alive_faithful)
            if death_list:
                death_list_names = [self.game_state.get_player(pid).name for pid in death_list if self.game_state.get_player(pid)]
                self.logger.info(f"📜 DEATH LIST: {', '.join(death_list_names)}")
                self.logger.info("   Traitors can ONLY murder from this list!")

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

        # Validate victim is on Death List if enabled
        if death_list and victim_id not in death_list:
            self.logger.warning(f"Victim {victim.name} not on Death List! Forcing valid selection.")
            victim_id = random.choice(death_list)
            victim = self.game_state.get_player(victim_id)

        # Generate murder discussion shortlist (for breakfast order "tell")
        shortlist = [victim_id]
        if len(alive_faithful) > 1:
            other_faithful = [p.id for p in alive_faithful if p.id != victim_id]
            num_others = min(random.randint(1, 2), len(other_faithful))
            shortlist.extend(random.sample(other_faithful, num_others))

        self.game_state.last_murder_discussion = shortlist

        # Check for Shield protection
        if getattr(victim, 'has_shield', False):
            victim.has_shield = False  # Shield consumed
            self.logger.info(f"🛡️  {victim.name} was PROTECTED by the Shield!")
            self.logger.info("The murder attempt failed!")
            self.game_state.last_murder_victim = None
            self.game_state.add_event(
                event_type="MURDER_BLOCKED",
                phase="turret",
                actor=traitor_agent.player.id,
                target=victim.id,
                data={"victim_name": victim.name},
                narrative=f"{victim.name} was protected by the Shield.",
            )
            return

        # Murder victim
        victim.alive = False
        self.game_state.murdered_players.append(victim.name)
        self.game_state.last_murder_victim = victim.name

        self.logger.info(f"Traitors murdered: {victim.name}")

        self.game_state.add_event(
            event_type="MURDER",
            phase="turret",
            actor=traitor_agent.player.id,
            target=victim.id,
            data={
                "victim_name": victim.name,
                "victim_role": victim.role.value,
                "traitor_name": traitor_agent.player.name,
                "murder_shortlist": shortlist,
            },
            narrative=f"{victim.name} was murdered by the Traitors.",
        )

    async def _create_death_list_async(self, faithful: List[Player]) -> List[str]:
        """Create Death List - pre-select 3-4 murder candidates.

        This mechanic restricts Traitor options when they've been "too efficient".

        Args:
            faithful: List of alive Faithfuls

        Returns:
            List of player IDs on the Death List
        """
        if len(faithful) == 0:
            return []

        # Typically 3-4 candidates
        num_candidates = min(random.randint(3, 4), len(faithful))

        # Simple selection: pick most threatening Faithfuls by social influence
        sorted_faithful = sorted(
            faithful,
            key=lambda p: p.stats.get('social_influence', 0.5),
            reverse=True
        )

        return [p.id for p in sorted_faithful[:num_candidates]]

    async def _collect_votes_parallel_async(
        self,
        allowed_targets: Optional[Set[str]] = None,
        allowed_voters: Optional[Set[str]] = None,
    ) -> Dict[str, str]:
        """Collect votes from all alive players in parallel.

        Args:
            allowed_targets: Optional set of valid target IDs (for revotes among tied players)
            allowed_voters: Optional set of voter IDs allowed to vote

        Returns:
            Dict mapping player_id -> voted_player_id
        """
        alive_agents = [
            (pid, agent)
            for pid, agent in self.player_agents.items()
            if agent.player.alive and (allowed_voters is None or pid in allowed_voters)
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
        """Resolve voting ties using configured tie-breaking method.

        Args:
            vote_counts: Counter of votes per player
            initial_votes: Original votes dict

        Returns:
            Tuple of (banished_id, final_votes, tie_info_dict)
        """
        if len(vote_counts) == 0:
            self.logger.error("No votes cast!")
            return list(self.game_state.alive_players)[0].id, initial_votes, {
                "revote_triggered": False,
                "random_resolution": True,
                "tied_names": [],
            }

        highest_count = vote_counts.most_common(1)[0][1]
        tied_ids = [player_id for player_id, count in vote_counts.items() if count == highest_count]

        tie_info: Dict = {"revote_triggered": False, "random_resolution": False, "tied_names": []}

        # No tie - return winner directly
        if len(tied_ids) == 1:
            return tied_ids[0], initial_votes, tie_info

        tied_names = [
            self.game_state.get_player(pid).name if self.game_state.get_player(pid) else pid
            for pid in tied_ids
        ]
        tie_info["tied_names"] = tied_names

        self.logger.info(
            f"⚖️  Tie detected: {', '.join(tied_names)} with {highest_count} votes each."
        )

        if self.config.tie_break_method == "random":
            tie_info["random_resolution"] = True
            banished_id = random.choice(tied_ids)
            return banished_id, initial_votes, tie_info

        if self.config.tie_break_method == "countback":
            banished_id = self._tie_break_countback(tied_ids)
            return banished_id, initial_votes, tie_info

        if self.config.tie_break_method != "revote":
            self.logger.warning(
                f"Unknown tie-break method: {self.config.tie_break_method}, using random"
            )
            tie_info["random_resolution"] = True
            banished_id = random.choice(tied_ids)
            return banished_id, initial_votes, tie_info

        tie_info["revote_triggered"] = True
        self.logger.info("Initiating revote among tied players.")

        eligible_voters = {
            player.id for player in self.game_state.alive_players if player.id not in tied_ids
        }
        if not eligible_voters:
            tie_info["random_resolution"] = True
            banished_id = random.choice(tied_ids)
            return banished_id, initial_votes, tie_info

        revote = await self._collect_votes_parallel_async(
            allowed_targets=set(tied_ids),
            allowed_voters=eligible_voters,
        )
        revote_counts = self._tally_votes(revote, log_dagger=True)

        highest_revote = revote_counts.most_common(1)[0][1]
        still_tied_ids = [player_id for player_id, count in revote_counts.items() if count == highest_revote]

        if len(still_tied_ids) > 1:
            tie_info["random_resolution"] = True
            banished_id = random.choice(still_tied_ids)
            tie_info["tied_names"] = [
                self.game_state.get_player(pid).name if self.game_state.get_player(pid) else pid
                for pid in still_tied_ids
            ]
            banished_name = (
                self.game_state.get_player(banished_id).name
                if self.game_state.get_player(banished_id) else banished_id
            )
            self.logger.info(
                f"⚖️  Tie persisted after revote between {', '.join(tie_info['tied_names'])}. "
                f"Selecting {banished_name} at random per fallback rules."
            )
        else:
            banished_id = revote_counts.most_common(1)[0][0]

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

    def _tally_votes(self, votes: Dict[str, str], log_dagger: bool = True) -> Counter:
        """Tally votes with dagger weight applied."""
        vote_counts: Counter = Counter()
        for voter_id, target_id in votes.items():
            voter = self.game_state.get_player(voter_id)
            vote_weight = 2 if (voter and getattr(voter, 'has_dagger', False)) else 1
            vote_counts[target_id] += vote_weight

            if log_dagger and voter and getattr(voter, 'has_dagger', False):
                self.logger.info(f"🗡️  {voter.name} used the DAGGER for double vote!")
        return vote_counts

    async def _handle_recruitment_async(self) -> None:
        """Handle Traitor recruitment after a Traitor is banished."""
        alive_traitors = self.game_state.alive_traitors
        alive_faithful = self.game_state.alive_faithful

        if not alive_faithful:
            return

        is_ultimatum = (
            self.config.recruitment_type == "ultimatum"
            and len(alive_traitors) == 1
        )

        if alive_traitors:
            recruiter = alive_traitors[0]
            recruit_target = self._choose_recruit_target(alive_faithful)

            if not recruit_target or recruit_target.role == Role.TRAITOR:
                self.logger.warning("Invalid recruitment target")
                return

            offer_type = "ULTIMATUM" if is_ultimatum else "RECRUITMENT OFFER"
            self.logger.info(f"\n🎭 {offer_type}: {recruit_target.name}")

            accepts, reasoning = self._offer_recruitment(recruit_target, is_ultimatum)

            if accepts:
                recruit_target.role = Role.TRAITOR
                recruit_target.was_recruited = True
                self.game_state.recruited_players.append(recruit_target.name)

                self.logger.info(f"✅ {recruit_target.name} ACCEPTED recruitment!")
                self.game_state.add_event(
                    event_type="RECRUITMENT",
                    phase="roundtable",
                    actor=recruiter.id,
                    target=recruit_target.id,
                    data={
                        "offer_type": "ultimatum" if is_ultimatum else "standard",
                        "accepted": True,
                        "recruiter_name": recruiter.name,
                        "recruit_name": recruit_target.name,
                        "reasoning": reasoning,
                    },
                    narrative=f"{recruit_target.name} accepted recruitment and became a Traitor!",
                )

                events = [f"{recruit_target.name} has been recruited as a Traitor!"]
                await self._parallel_reflection_async(events)
            else:
                if is_ultimatum:
                    recruit_target.alive = False
                    self.game_state.murdered_players.append(recruit_target.name)
                    self.logger.info(
                        f"❌ {recruit_target.name} REFUSED ultimatum and was murdered!"
                    )
                    self.game_state.add_event(
                        event_type="RECRUITMENT",
                        phase="roundtable",
                        actor=recruiter.id,
                        target=recruit_target.id,
                        data={
                            "offer_type": "ultimatum",
                            "accepted": False,
                            "recruiter_name": recruiter.name,
                            "recruit_name": recruit_target.name,
                            "reasoning": reasoning,
                            "consequence": "murdered",
                        },
                        narrative=f"{recruit_target.name} refused the ultimatum and was murdered!",
                    )
                    events = [
                        f"{recruit_target.name} refused the ultimatum and was murdered!"
                    ]
                    await self._parallel_reflection_async(events)
                else:
                    self.logger.info(f"❌ {recruit_target.name} REFUSED recruitment")
                    self.game_state.add_event(
                        event_type="RECRUITMENT",
                        phase="roundtable",
                        actor=recruiter.id,
                        target=recruit_target.id,
                        data={
                            "offer_type": "standard",
                            "accepted": False,
                            "recruiter_name": recruiter.name,
                            "recruit_name": recruit_target.name,
                            "reasoning": reasoning,
                        },
                        narrative=f"{recruit_target.name} refused recruitment.",
                    )

    def _choose_recruit_target(self, faithful: List[Player]) -> Optional[Player]:
        """Choose who to recruit as a Traitor."""
        if not faithful:
            return None
        return max(
            faithful,
            key=lambda p: p.stats.get("social_influence", 0.5),
        )

    def _offer_recruitment(self, recruit_target: Player, is_ultimatum: bool) -> Tuple[bool, str]:
        """Decide whether a Faithful accepts recruitment."""
        if is_ultimatum:
            return True, "Survival instinct - accepting ultimatum"

        agreeableness = recruit_target.personality.get("agreeableness", 0.5)
        neuroticism = recruit_target.personality.get("neuroticism", 0.5)

        traitor_count = len(self.game_state.alive_traitors)
        faithful_count = len(self.game_state.alive_faithful)

        base_prob = (agreeableness + neuroticism) / 2
        if traitor_count >= faithful_count * 0.7:
            base_prob += 0.2

        accepts = base_prob > 0.6
        reasoning = (
            f"Personality-based decision (agreeableness={agreeableness:.2f}, "
            f"neuroticism={neuroticism:.2f})"
        )
        return accepts, reasoning

    def _tie_break_countback(self, tied_players: List[str]) -> str:
        """Break tie with countback (cumulative season votes)."""
        cumulative_votes = {pid: 0 for pid in tied_players}

        for vote_record in self.game_state.vote_history:
            for target_id in vote_record.values():
                if target_id in tied_players:
                    cumulative_votes[target_id] += 1

        max_cumulative = max(cumulative_votes.values())
        candidates = [pid for pid, count in cumulative_votes.items() if count == max_cumulative]

        if len(candidates) > 1:
            return random.choice(candidates)

        return candidates[0]

    async def _run_end_game_async(self) -> Optional[Role]:
        """Run end game mechanics (Vote to End or Traitor's Dilemma)."""
        alive_count = len(self.game_state.alive_players)
        traitor_count = len(self.game_state.alive_traitors)

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"END GAME TRIGGERED: {alive_count} players remaining")
        self.logger.info(f"{'='*60}\n")

        if (
            self.config.end_game_type == "traitors_dilemma"
            and traitor_count == 2
            and len(self.game_state.alive_faithful) == 0
        ):
            return await self._run_traitors_dilemma_async()

        return await self._run_vote_to_end_async()

    async def _run_vote_to_end_async(self) -> Optional[Role]:
        """Run Vote to End mechanic (Final N vote)."""
        self.logger.info("\n--- Vote to End ---")
        self.logger.info("Players must decide: END the game or BANISH again?")
        self.logger.info("Unanimous END required to finish.\n")

        votes: Dict[str, str] = {}
        for player in self.game_state.alive_players:
            if player.role == Role.TRAITOR:
                traitor_count = len(self.game_state.alive_traitors)
                faithful_count = len(self.game_state.alive_faithful)
                if traitor_count >= faithful_count:
                    vote = "END"
                    reasoning = "Traitor majority - safe to end game"
                else:
                    vote = "BANISH"
                    reasoning = "Need to eliminate more Faithful first"
            else:
                memory_manager = self.memory_managers.get(player.id)
                suspicions = memory_manager.get_suspicions() if memory_manager else {}
                max_suspicion = max(suspicions.values()) if suspicions else 0.0
                neuroticism = player.personality.get("neuroticism", 0.5)
                threshold = 0.05 + (neuroticism * 0.15)

                if max_suspicion > threshold:
                    vote = "BANISH"
                    reasoning = (
                        f"Still suspicious (max={max_suspicion:.2f}, threshold={threshold:.2f})"
                    )
                else:
                    vote = "END"
                    reasoning = "Confident all Traitors eliminated"

            votes[player.id] = vote
            self.logger.info(f"{player.name} votes {vote}: {reasoning}")

        self.game_state.add_event(
            event_type="VOTE_TO_END",
            phase="roundtable",
            data={"votes": votes.copy()},
            narrative="Final vote to end the game or continue banishments.",
        )

        end_votes = sum(1 for v in votes.values() if v == "END")
        total_votes = len(votes)

        self.logger.info(f"\nVote Result: {end_votes}/{total_votes} voted END")

        if end_votes == total_votes:
            self.logger.info("✅ UNANIMOUS END - Game concludes!")
            if len(self.game_state.alive_traitors) > 0:
                return Role.TRAITOR
            return Role.FAITHFUL

        self.logger.info("❌ Not unanimous - Continue to next Round Table")
        return None

    async def _run_traitors_dilemma_async(self) -> Role:
        """Run Traitor's Dilemma (Prisoner's Dilemma with 2 Traitors)."""
        self.logger.info("\n" + "=" * 60)
        self.logger.info("⚔️  TRAITOR'S DILEMMA")
        self.logger.info("=" * 60)
        self.logger.info("Two Traitors remain. Each must choose: SHARE or STEAL")
        self.logger.info("")

        traitors = self.game_state.alive_traitors
        if len(traitors) != 2:
            self.logger.error(
                f"Traitor's Dilemma requires exactly 2 Traitors, found {len(traitors)}"
            )
            return Role.TRAITOR

        decisions: Dict[str, str] = {}
        for traitor in traitors:
            agreeableness = traitor.personality.get("agreeableness", 0.5)
            neuroticism = traitor.personality.get("neuroticism", 0.5)
            share_prob = agreeableness * 0.6 - neuroticism * 0.4 + 0.2
            share_prob = max(0.0, min(1.0, share_prob))
            decision = "SHARE" if random.random() < share_prob else "STEAL"
            decisions[traitor.id] = decision
            self.logger.info(
                f"{traitor.name} chooses to {decision} "
                f"(agreeableness={agreeableness:.2f}, neuroticism={neuroticism:.2f})"
            )

        if all(decision == "SHARE" for decision in decisions.values()):
            outcome = "Both Traitors chose SHARE. The pot is split."
        elif all(decision == "STEAL" for decision in decisions.values()):
            outcome = "Both Traitors chose STEAL. The pot is burned."
        else:
            stealer = next(pid for pid, decision in decisions.items() if decision == "STEAL")
            stealer_name = self.game_state.get_player(stealer).name
            outcome = f"{stealer_name} chose STEAL and takes the full pot."

        self.logger.info(outcome)
        return Role.TRAITOR

    def save_game_report(self, output_path: str = None) -> str:
        """Save complete game data to JSON for UI visualization."""
        import json
        from datetime import datetime
        from pathlib import Path

        if output_path is None:
            reports_dir = Path("data/reports")
            reports_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = reports_dir / f"game_{timestamp}.json"
        else:
            reports_dir = Path("data/reports").resolve()
            safe_output_path = reports_dir.joinpath(output_path).resolve()
            if not str(safe_output_path).startswith(str(reports_dir)):
                raise ValueError("Invalid output path: Path traversal detected.")
            output_path = safe_output_path
            output_path.parent.mkdir(parents=True, exist_ok=True)

        game_data = self.game_state.to_export_dict()
        game_data["name"] = f"Game {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        game_data["total_days"] = self.game_state.day
        game_data["winner"] = (
            "FAITHFUL" if len(self.game_state.alive_traitors) == 0
            else "TRAITORS" if len(self.game_state.alive_faithful) == 0
            else "UNKNOWN"
        )
        game_data["rule_variant"] = self.config.rule_set if hasattr(self.config, 'rule_set') else "uk"
        game_data["config"] = {
            "total_players": self.config.total_players,
            "num_traitors": self.config.num_traitors,
            "max_days": self.config.max_days,
            "enable_recruitment": self.config.enable_recruitment,
            "enable_shields": self.config.enable_shields,
            "enable_death_list": self.config.enable_death_list,
            "tie_break_method": self.config.tie_break_method,
        }

        def make_serializable(obj: Any):
            if hasattr(obj, 'tolist'):
                return obj.tolist()
            if hasattr(obj, 'value'):
                return obj.value
            if isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [make_serializable(v) for v in obj]
            return obj

        game_data = make_serializable(game_data)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(game_data, f, indent=2, default=str)

        return str(output_path)

    # Synchronous wrapper
    def run_game(self) -> str:
        """Synchronous wrapper for run_game_async."""
        return asyncio.run(self.run_game_async())
