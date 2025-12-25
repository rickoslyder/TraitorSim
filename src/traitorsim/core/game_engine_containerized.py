"""Containerized async game engine for TraitorSim.

This engine communicates with player agents running in Docker containers
via HTTP REST APIs, enabling resource isolation and parallel execution.
"""

import asyncio
import httpx
from typing import List, Dict, Optional, Tuple, Any
from collections import Counter

from ..agents.game_master_interactions import GameMasterInteractions
from ..core.game_state import GameState, Player, Role, TrustMatrix
from ..core.config import GameConfig
from ..core.enums import GamePhase
from ..missions.skill_check import SkillCheckMission
from ..utils.logger import setup_logger


class GameEngineContainerized:
    """Game engine that orchestrates containerized player agents via HTTP.

    Each player agent runs in its own Docker container with isolated resources.
    The engine communicates via REST API calls for parallel execution.
    """

    def __init__(self, config: Optional[GameConfig] = None, agent_base_url: str = "http://localhost"):
        """Initialize containerized game engine.

        Args:
            config: Game configuration (uses defaults if None)
            agent_base_url: Base URL for agent containers (default: localhost)
        """
        self.config = config or GameConfig()
        self.game_state = GameState()
        self.logger = setup_logger("game_engine")
        self.agent_base_url = agent_base_url

        # Initialize Game Master (runs on host, not containerized)
        self.gm = GameMasterInteractions(
            self.game_state,
            api_key=self.config.gemini_api_key,
            model_name=self.config.gemini_model,
            world_bible_path=self.config.world_bible_path,
        )

        # Agent URLs (port mapping: 8000-8009 for agents 0-9)
        self.agent_urls: Dict[str, str] = {}

        # Agent reasoning capture for voice scripts
        # Structure: {day: {player_id: {"vote": {...}, "murder": {...}, ...}}}
        self.agent_reasoning_by_day: Dict[int, Dict[str, Dict[str, Any]]] = {}

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
                self._finalize_player_setup()
                return
        else:
            self._initialize_random_players()

        self._finalize_player_setup()

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

    def _finalize_player_setup(self) -> None:
        """Complete player setup: assign roles, trust matrix, and URLs."""
        import random

        # Assign traitor roles
        traitor_indices = random.sample(
            range(len(self.game_state.players)), self.config.num_traitors
        )
        for idx in traitor_indices:
            self.game_state.players[idx].role = Role.TRAITOR

        # Initialize trust matrix
        player_ids = [p.id for p in self.game_state.players]
        self.game_state.trust_matrix = TrustMatrix(player_ids)

        # Setup agent URLs - use Docker service names for internal networking
        for i, player in enumerate(self.game_state.players):
            # When running inside orchestrator, use container names
            # Format: http://traitorsim-agent-0:5000
            self.agent_urls[player.id] = f"http://traitorsim-agent-{i}:5000"

        self.logger.info(f"Initialized {len(self.game_state.players)} players")
        self.logger.info(
            f"Traitors: {[p.name for p in self.game_state.players if p.role == Role.TRAITOR]}"
        )

        # Log archetype distribution if using personas
        if self.config.personality_generation == "archetype":
            archetypes = [p.archetype_name for p in self.game_state.players if p.archetype_name]
            if archetypes:
                self.logger.info(f"Archetypes in play: {set(archetypes)}")

    async def _initialize_agent_containers(self) -> None:
        """Initialize all agent containers with player data via HTTP."""
        self.logger.info("Initializing agent containers...")

        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            for player in self.game_state.players:
                url = self.agent_urls[player.id]
                payload = {
                    "player": {
                        "id": player.id,
                        "name": player.name,
                        "role": player.role.value,
                        "alive": player.alive,
                        "personality": player.personality,
                        "stats": player.stats,
                        # Persona fields for authentic characters
                        "archetype_id": player.archetype_id,
                        "archetype_name": player.archetype_name,
                        "demographics": player.demographics,
                        "backstory": player.backstory,
                        "strategic_profile": player.strategic_profile,
                    }
                }
                tasks.append(client.post(f"{url}/initialize", json=payload))

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            for player, response in zip(self.game_state.players, responses):
                if isinstance(response, Exception):
                    self.logger.error(f"Failed to initialize {player.name}: {response}")
                else:
                    self.logger.info(f"Initialized container for {player.name}")

    def _serialize_game_state(self) -> Dict:
        """Serialize GameState for HTTP transmission."""
        return {
            "day": self.game_state.day,
            "phase": self.game_state.phase.value,
            "prize_pot": self.game_state.prize_pot,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "role": p.role.value,
                    "alive": p.alive,
                    "personality": p.personality,
                    "stats": p.stats,
                    "archetype_name": p.archetype_name,
                }
                for p in self.game_state.players
            ],
            "trust_matrix": True,  # Agents manage their own trust values
            "murdered_players": self.game_state.murdered_players,
            "banished_players": self.game_state.banished_players,
            "last_murder_victim": self.game_state.last_murder_victim
        }

    async def run_game_async(self) -> str:
        """Run complete game asynchronously with containerized agents.

        Returns:
            Winner ("FAITHFUL" or "TRAITOR")
        """
        self.logger.info("=== TraitorSim Game Starting (Containerized) ===")

        # Initialize players
        self._initialize_players()

        # Initialize agent containers
        await self._initialize_agent_containers()

        # Game start announcement
        all_names = [p.name for p in self.game_state.players]
        traitor_names = [p.name for p in self.game_state.players if p.role == Role.TRAITOR]
        faithful_names = [p.name for p in self.game_state.players if p.role == Role.FAITHFUL]

        opening = await self.gm.announce_game_start_async(
            all_names, traitor_names, faithful_names
        )
        self.logger.info(f"\n{opening}\n")

        # Main game loop
        while self.game_state.day <= self.config.max_days:
            self.game_state.day += 1
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"DAY {self.game_state.day}")
            self.logger.info(f"{'='*60}\n")

            # Run 5-phase cycle
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
                # Trigger end game
                winner = await self._run_end_game_async()
                if winner:
                    break

        # Finale
        winner = self.game_state.check_win_condition()
        if not winner:
            self.logger.warning(f"Game reached max days ({self.config.max_days})")
            winner = Role.FAITHFUL if len(self.game_state.alive_traitors) == 0 else Role.TRAITOR

        survivors = [p.name for p in self.game_state.alive_players]
        finale = await self.gm.announce_finale_async(winner.value.upper(), survivors)

        self.logger.info(f"\n{'='*60}")
        self.logger.info(finale)
        self.logger.info(f"🏆 WINNERS: {winner.value.upper()}")
        self.logger.info(f"{'='*60}\n")

        # Save complete game report for UI visualization
        try:
            report_path = self.save_game_report()
            self.logger.info(f"📊 Game report saved: {report_path}")
        except Exception as e:
            self.logger.error(f"Failed to save game report: {e}")

        return winner.value.upper()

    async def _run_breakfast_phase_async(self) -> None:
        """Breakfast phase: Announce murder victim and track entry order."""
        self.game_state.phase = GamePhase.BREAKFAST
        self.logger.info("--- Breakfast Phase ---")

        # Generate breakfast entry order (dramatic if enabled)
        breakfast_order = self._generate_breakfast_entry_order()
        self.game_state.breakfast_order_history.append(breakfast_order)

        if self.config.enable_dramatic_entry and len(breakfast_order) > 0:
            self.logger.info(f"Breakfast entry order: {', '.join([self.game_state.get_player(pid).name for pid in breakfast_order])}")

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
            narrative=f"Players arrived at breakfast. {'Murder discovered!' if self.game_state.last_murder_victim else 'No murder last night.'}",
        )

        if self.game_state.last_murder_victim:
            narrative = await self.gm.announce_murder_async(
                self.game_state.last_murder_victim, self.game_state.day
            )
            self.logger.info(narrative)

            # Agents reflect on murder and entry order
            events = [f"{self.game_state.last_murder_victim} was murdered"]
            if self.config.enable_dramatic_entry and len(breakfast_order) > 0:
                last_player_id = breakfast_order[-1]
                last_player = self.game_state.get_player(last_player_id)
                events.append(f"{last_player.name} entered breakfast last (potential Tell)")

            await self._parallel_reflection_async(events)
        else:
            self.logger.info("No murder last night (first day).")

    def _generate_breakfast_entry_order(self) -> List[str]:
        """Generate breakfast entry order (dramatic or random).

        If enable_dramatic_entry is True, puts murder discussion targets last
        (the "at-risk" Faithfuls discussed in the Turret), with occasional Traitor misdirection.

        This creates a meta-tell where smart agents can track who enters last.

        Returns:
            List of player IDs in entry order
        """
        import random

        alive = self.game_state.alive_players
        if len(alive) == 0:
            return []

        player_ids = [p.id for p in alive]

        if not self.config.enable_dramatic_entry:
            # Random order
            random.shuffle(player_ids)
            return player_ids

        # Dramatic entry: Put murder discussion targets last
        # Based on who the Traitors discussed for murder in the Turret

        discussion_targets = self.game_state.last_murder_discussion.copy()

        # Occasionally (30% chance) throw in a Traitor for misdirection
        alive_traitors = [p for p in alive if p.role == Role.TRAITOR]
        if alive_traitors and random.random() < 0.3:
            traitor_to_add = random.choice(alive_traitors)
            if traitor_to_add.id not in discussion_targets:
                discussion_targets.append(traitor_to_add.id)

        # Separate into early arrivals and late arrivals
        early_arrivals = [pid for pid in player_ids if pid not in discussion_targets]
        late_arrivals = [pid for pid in discussion_targets if pid in player_ids]

        # Shuffle both groups
        random.shuffle(early_arrivals)
        random.shuffle(late_arrivals)

        # Early arrivals first, then the "at-risk" players last
        return early_arrivals + late_arrivals

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

        # Record structured MISSION_COMPLETE event for UI
        self.game_state.add_event(
            event_type="MISSION_COMPLETE",
            phase="mission",
            data={
                "mission_name": "Skill Check",
                "success": success_rate >= 0.5,
                "success_rate": success_rate,
                "earnings": result.earnings,
                "participants": [p.id for p in self.game_state.alive_players],
                "performance_scores": result.performance_scores,
            },
            narrative=f"Mission {'succeeded' if success_rate >= 0.5 else 'failed'}. £{result.earnings:,.0f} added to prize pot.",
        )

        # Award Shield and Dagger based on performance
        if self.config.enable_shields:
            await self._award_shield_and_dagger(result.performance_scores)

        # Award Seer power if enabled and available
        if self.config.enable_seer and self.game_state.day >= self.config.seer_available_day:
            await self._award_seer_power(result.performance_scores)

        # Agents reflect on mission
        events = [
            f"Mission {'succeeded' if success_rate >= 0.5 else 'failed'}",
            f"${result.earnings:,.0f} added to pot",
        ]
        await self._parallel_reflection_async(events)

    async def _award_shield_and_dagger(self, performance_scores: Dict[str, float]) -> None:
        """Award Shield or Dagger to mission winner based on config.

        Realistic behavior (based on actual show research):
        - "never": Only Shield awarded (UK/US style)
        - "rare": On specific days, winner CHOOSES Shield OR Dagger (Canada style)
        - "every_mission": Old unrealistic behavior (both awarded)

        Shield: Grants murder immunity for the night
        Dagger: Grants double voting power at Round Table

        Args:
            performance_scores: Dict mapping player_id -> performance (0.0-1.0)
        """
        if len(performance_scores) < 1:
            return

        # Sort players by performance (descending)
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
            # UK/US style: Only Shield, no Dagger
            self._award_shield(winner)

        elif dagger_mode == "rare":
            # Canada style: Dagger offered as choice on specific days
            if current_day in dagger_days:
                # Winner must choose: Shield OR Dagger
                choice = self._choose_shield_or_dagger(winner)
                if choice == "dagger":
                    self._award_dagger(winner)
                    self.logger.info(f"🗡️  {winner.name} chose the DAGGER over the Shield!")
                else:
                    self._award_shield(winner)
                    self.logger.info(f"🛡️  {winner.name} chose the SHIELD over the Dagger!")
            else:
                # Normal day: Only Shield available
                self._award_shield(winner)

        elif dagger_mode == "every_mission":
            # Old unrealistic behavior: both awarded
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
            self.logger.info(f"🛡️  Shield awarded (secret)")

    def _award_dagger(self, player: Player) -> None:
        """Award Dagger to a player."""
        player.has_dagger = True
        self.game_state.dagger_holder = player.name
        self.logger.info(f"🗡️  {player.name} won the DAGGER!")

    def _choose_shield_or_dagger(self, player: Player) -> str:
        """AI player chooses between Shield and Dagger.

        Strategic logic:
        - Traitors prefer Dagger (manipulate votes, they're less likely to be murdered)
        - Faithful with high neuroticism prefer Shield (fear of death)
        - Faithful with high extraversion prefer Dagger (influence the vote)
        - Default: slight preference for Shield (survival instinct)

        Returns:
            "shield" or "dagger"
        """
        import random

        # Traitors: 70% prefer Dagger (they won't murder themselves)
        if player.role == Role.TRAITOR:
            return "dagger" if random.random() < 0.70 else "shield"

        # Faithful: personality-based decision
        neuroticism = player.personality.get("neuroticism", 0.5)
        extraversion = player.personality.get("extraversion", 0.5)

        # High neuroticism = fear of death = prefer Shield
        # High extraversion = want influence = prefer Dagger
        dagger_preference = (extraversion * 0.4) - (neuroticism * 0.3) + 0.3

        return "dagger" if random.random() < dagger_preference else "shield"

    async def _award_seer_power(self, performance_scores: Dict[str, float]) -> None:
        """Award Seer power to top mission performer.

        Seer power (UK Series 3+, US Season 3+) allows one player to
        privately confirm another contestant's true role (Traitor or Faithful).

        The Seer can then fabricate any narrative about what happened.

        Args:
            performance_scores: Dict mapping player_id -> performance (0.0-1.0)
        """
        # Only award if no one currently has Seer
        if self.game_state.seer_holder:
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

    async def _use_seer_power_async(self, seer_player: Player) -> None:
        """Allow Seer holder to use their power.

        The Seer chooses a target and learns their true role.
        Both players can then fabricate any narrative about the meeting.

        Args:
            seer_player: Player with Seer power
        """
        self.logger.info(f"\n👁️  SEER POWER: {seer_player.name} uses their ability")

        # Seer chooses target via HTTP
        target_id = await self._choose_seer_target_http(seer_player.id)

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

        # Notify the Seer agent of the truth via HTTP
        await self._notify_seer_result_http(seer_player.id, target_id, true_role)

        # Consume the Seer power (one-time use)
        seer_player.has_seer = False
        self.game_state.seer_holder = None

        # Public announcement (vague - both can fabricate)
        self.logger.info(f"   {seer_player.name} and {target_player.name} had a private meeting...")
        self.logger.info(f"   What was revealed? Only they know for sure.")

    async def _choose_seer_target_http(self, seer_id: str) -> Optional[str]:
        """Have Seer choose who to investigate via HTTP.

        Args:
            seer_id: ID of the player with Seer power

        Returns:
            Player ID of investigation target, or None if failed
        """
        try:
            url = self.agent_urls[seer_id]
            game_state_data = self._serialize_game_state()

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{url}/choose_seer_target",
                    json={"game_state": game_state_data}
                )
                response.raise_for_status()
                data = response.json()
                return data['target_player_id']
        except Exception as e:
            self.logger.error(f"Error choosing Seer target: {e}")
            # Fallback: choose random player
            import random
            valid_targets = [p.id for p in self.game_state.alive_players if p.id != seer_id]
            return random.choice(valid_targets) if valid_targets else None

    async def _notify_seer_result_http(self, seer_id: str, target_id: str, role: str) -> None:
        """Notify Seer of investigation result via HTTP.

        Args:
            seer_id: ID of the Seer
            target_id: ID of the investigated player
            role: The true role ("TRAITOR" or "FAITHFUL")
        """
        try:
            url = self.agent_urls[seer_id]

            async with httpx.AsyncClient(timeout=30.0) as client:
                await client.post(
                    f"{url}/seer_result",
                    json={
                        "target_player_id": target_id,
                        "true_role": role
                    }
                )
        except Exception as e:
            self.logger.error(f"Error notifying Seer result: {e}")

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

    async def _run_roundtable_phase_async(self) -> None:
        """Round Table phase: Voting and banishment."""
        self.game_state.phase = GamePhase.ROUNDTABLE
        self.logger.info("\n--- Round Table Phase ---")

        # Collect votes in parallel via HTTP
        votes = await self._collect_votes_parallel_async()

        # Tally votes (accounting for Dagger double-vote)
        vote_counts = Counter()
        for voter_id, target_id in votes.items():
            voter = self.game_state.get_player(voter_id)
            # Dagger gives double vote weight
            vote_weight = 2 if (voter and voter.has_dagger) else 1
            vote_counts[target_id] += vote_weight

            if voter and voter.has_dagger:
                self.logger.info(f"🗡️  {voter.name} used the DAGGER for double vote!")

        # Check for ties and resolve using configured method
        banished_id = await self._resolve_vote_tie_async(vote_counts, votes)

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
            if player.has_dagger:
                player.has_dagger = False

        # Determine if we should reveal role (2025 rule: no reveal in endgame)
        alive_count = len(self.game_state.alive_players)
        is_endgame = alive_count <= self.config.final_player_count
        should_reveal_role = self.config.endgame_reveal_roles or not is_endgame

        # GM announces banishment
        if should_reveal_role:
            narrative = await self.gm.announce_banishment_async(
                banished_player.name,
                banished_player.role.value,
                dict(vote_counts),
                self.game_state.day,
            )
        else:
            # 2025 rule: Don't reveal role in endgame
            narrative = await self.gm.announce_banishment_async(
                banished_player.name,
                "UNKNOWN",  # Role hidden
                dict(vote_counts),
                self.game_state.day,
            )
            self.logger.info(f"🔒 2025 RULE: {banished_player.name}'s role is NOT revealed!")
        self.logger.info(narrative)

        # Record votes in history (for countback tie-breaking)
        self.game_state.vote_history.append(votes.copy())

        # Log votes
        for voter_id, target_id in votes.items():
            voter = self.game_state.get_player(voter_id)
            target = self.game_state.get_player(target_id)
            if voter and target:
                self.logger.info(f"  {voter.name} voted for {target.name}")

        # Record structured VOTE_TALLY event for UI
        self.game_state.add_event(
            event_type="VOTE_TALLY",
            phase="roundtable",
            target=banished_id,
            data={
                "votes": votes.copy(),
                "tally": dict(vote_counts),
                "eliminated": banished_id,
                "eliminated_name": banished_player.name,
                "eliminated_role": banished_player.role.value,
            },
            narrative=f"{banished_player.name} was banished with {vote_counts[banished_id]} votes.",
        )

        # Agents reflect - only reveal role if allowed
        if should_reveal_role:
            events = [
                f"{banished_player.name} was banished",
                f"They were a {banished_player.role.value.upper()}",
            ]
        else:
            events = [
                f"{banished_player.name} was banished",
                f"Their role was NOT revealed (2025 endgame rule)",
            ]
        await self._parallel_reflection_async(events)

        # Check for recruitment (if a Traitor was banished)
        if self.config.enable_recruitment and banished_player.role == Role.TRAITOR:
            await self._handle_recruitment_async()

    async def _handle_recruitment_async(self) -> None:
        """Handle Traitor recruitment after a Traitor is banished.

        Two modes:
        - Standard: Traitors offer recruitment, Faithful can refuse
        - Ultimatum: Last Traitor forces "Join or Die"
        """
        alive_traitors = self.game_state.alive_traitors
        alive_faithful = self.game_state.alive_faithful

        if not alive_faithful:
            return  # No one to recruit

        is_ultimatum = (self.config.recruitment_type == "ultimatum" and
                       len(alive_traitors) == 1)

        # Traitors choose who to recruit
        if alive_traitors:
            # First traitor selects recruit target
            recruiter = alive_traitors[0]
            recruit_target_id = await self._choose_recruit_target_http(recruiter.id)
            recruit_target = self.game_state.get_player(recruit_target_id)

            if not recruit_target or recruit_target.role == Role.TRAITOR:
                self.logger.warning(f"Invalid recruitment target: {recruit_target_id}")
                return

            # Announce recruitment offer
            offer_type = "ULTIMATUM" if is_ultimatum else "RECRUITMENT OFFER"
            self.logger.info(f"\n🎭 {offer_type}: {recruit_target.name}")

            # Ask Faithful if they accept
            accepts = await self._offer_recruitment_http(recruit_target.id, is_ultimatum)

            if accepts:
                # Convert to Traitor
                recruit_target.role = Role.TRAITOR
                recruit_target.was_recruited = True
                self.game_state.recruited_players.append(recruit_target.name)

                self.logger.info(f"✅ {recruit_target.name} ACCEPTED recruitment!")

                # Record structured RECRUITMENT event for UI
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
                    },
                    narrative=f"{recruit_target.name} accepted recruitment and became a Traitor!",
                )

                # Notify all agents
                events = [f"{recruit_target.name} has been recruited as a Traitor!"]
                await self._parallel_reflection_async(events)
            else:
                if is_ultimatum:
                    # Ultimatum refused = immediate murder
                    recruit_target.alive = False
                    self.game_state.murdered_players.append(recruit_target.name)
                    self.logger.info(f"❌ {recruit_target.name} REFUSED ultimatum and was murdered!")

                    # Record structured RECRUITMENT event for UI (refusal + murder)
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
                            "consequence": "murdered",
                        },
                        narrative=f"{recruit_target.name} refused the ultimatum and was murdered!",
                    )

                    events = [f"{recruit_target.name} refused the ultimatum and was murdered!"]
                    await self._parallel_reflection_async(events)
                else:
                    # Standard refusal
                    self.logger.info(f"❌ {recruit_target.name} REFUSED recruitment")

                    # Record structured RECRUITMENT event for UI (refusal)
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
                        },
                        narrative=f"{recruit_target.name} refused recruitment.",
                    )

    async def _choose_recruit_target_http(self, traitor_id: str) -> str:
        """Have traitor choose who to recruit via HTTP.

        Args:
            traitor_id: ID of the traitor making the choice

        Returns:
            Player ID of recruitment target
        """
        try:
            url = self.agent_urls[traitor_id]
            game_state_data = self._serialize_game_state()

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{url}/choose_recruit_target",
                    json={"game_state": game_state_data}
                )
                response.raise_for_status()
                data = response.json()
                return data['target_player_id']
        except Exception as e:
            self.logger.error(f"Error choosing recruit target: {e}")
            # Fallback: choose random faithful
            faithful = self.game_state.alive_faithful
            return faithful[0].id if faithful else None

    async def _offer_recruitment_http(self, faithful_id: str, is_ultimatum: bool) -> bool:
        """Offer recruitment to a Faithful via HTTP.

        Args:
            faithful_id: ID of the Faithful being recruited
            is_ultimatum: True if this is forced ultimatum

        Returns:
            True if Faithful accepts, False otherwise
        """
        try:
            url = self.agent_urls[faithful_id]
            game_state_data = self._serialize_game_state()

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{url}/decide_recruitment",
                    json={
                        "game_state": game_state_data,
                        "is_ultimatum": is_ultimatum
                    }
                )
                response.raise_for_status()
                data = response.json()
                return data.get('accepts', False)
        except Exception as e:
            self.logger.error(f"Error offering recruitment: {e}")
            # Personality-based fallback
            player = self.game_state.get_player(faithful_id)
            if player:
                # High agreeableness = more likely to accept
                agreeableness = player.personality.get('agreeableness', 0.5)
                # If ultimatum, always accept (survival)
                if is_ultimatum:
                    return True
                return agreeableness > 0.6
            return False

    async def _run_turret_phase_async(self) -> None:
        """Turret phase: Traitors murder a Faithful.

        If Death List is enabled, Traitors must pre-select 3-4 murder candidates
        and can only choose from that list. This mechanic restricts their options.
        """
        self.game_state.phase = GamePhase.TURRET
        self.logger.info("\n--- Turret Phase ---")

        # Get alive traitors
        alive_traitors = [p for p in self.game_state.alive_players if p.role == Role.TRAITOR]

        if not alive_traitors:
            self.logger.info("No traitors alive to murder.")
            return

        import random
        alive_faithful = [p for p in self.game_state.alive_players if p.role == Role.FAITHFUL]

        # Death List mechanic (optional)
        death_list = None
        if self.config.enable_death_list:
            death_list = await self._create_death_list_async(alive_traitors, alive_faithful)
            if death_list:
                death_list_names = [self.game_state.get_player(pid).name for pid in death_list]
                self.logger.info(f"📜 DEATH LIST: {', '.join(death_list_names)}")
                self.logger.info("   Traitors can ONLY murder from this list!")

        # First traitor chooses victim (restricted by Death List if enabled)
        traitor = alive_traitors[0]
        victim_id = await self._choose_murder_victim_http(traitor.id, death_list)

        if not victim_id:
            self.logger.warning("No murder victim chosen")
            return

        victim = self.game_state.get_player(victim_id)
        if not victim:
            self.logger.error(f"Invalid victim: {victim_id}")
            return

        # Validate victim is on Death List if enabled
        if death_list and victim_id not in death_list:
            self.logger.warning(f"Victim {victim.name} not on Death List! Forcing valid selection.")
            victim_id = random.choice(death_list)
            victim = self.game_state.get_player(victim_id)

        # Generate murder discussion shortlist (for breakfast order "tell")
        # This simulates the Traitors discussing 2-3 potential targets
        shortlist = [victim_id]  # Chosen victim always on list
        if len(alive_faithful) > 1:
            # Add 1-2 other Faithfuls to discussion list
            other_faithful = [p.id for p in alive_faithful if p.id != victim_id]
            num_others = min(random.randint(1, 2), len(other_faithful))
            shortlist.extend(random.sample(other_faithful, num_others))

        self.game_state.last_murder_discussion = shortlist
        self.logger.info(f"Murder discussion targets: {[self.game_state.get_player(pid).name for pid in shortlist]}")

        # Check for Shield protection (works even if On Trial / Death List)
        if victim.has_shield:
            victim.has_shield = False  # Shield consumed
            self.logger.info(f"🛡️  {victim.name} was PROTECTED by the Shield!")
            self.logger.info("The murder attempt failed!")
            # No murder happened - victim survives
            return

        # Murder victim
        victim.alive = False
        self.game_state.murdered_players.append(victim.name)
        self.game_state.last_murder_victim = victim.name

        self.logger.info(f"Traitors murdered: {victim.name}")

        # Record structured MURDER event for UI
        self.game_state.add_event(
            event_type="MURDER",
            phase="turret",
            actor=traitor.id,
            target=victim.id,
            data={
                "victim_name": victim.name,
                "victim_role": victim.role.value,
                "traitor_name": traitor.name,
                "murder_shortlist": shortlist,
            },
            narrative=f"{victim.name} was murdered by the Traitors.",
        )

    async def _create_death_list_async(self, traitors: List[Player], faithful: List[Player]) -> List[str]:
        """Create Death List - Traitors pre-select 3-4 murder candidates.

        This mechanic restricts Traitor options when they've been "too efficient".
        Traitors can nominate themselves for strategic complexity.

        Args:
            traitors: List of alive Traitors
            faithful: List of alive Faithfuls

        Returns:
            List of player IDs on the Death List
        """
        if len(faithful) == 0:
            return []

        # Typically 3-4 candidates
        import random
        num_candidates = min(random.randint(3, 4), len(faithful))

        # For now, Traitors select the Death List via HTTP (first Traitor decides)
        if traitors:
            try:
                traitor = traitors[0]
                url = self.agent_urls[traitor.id]
                game_state_data = self._serialize_game_state()

                async with httpx.AsyncClient(timeout=120.0) as client:
                    response = await client.post(
                        f"{url}/create_death_list",
                        json={
                            "game_state": game_state_data,
                            "num_candidates": num_candidates
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    return data.get('death_list', [])[:num_candidates]
            except Exception as e:
                self.logger.error(f"Error creating Death List: {e}")

        # Fallback: random selection from Faithful
        return random.sample([p.id for p in faithful], num_candidates)

    def _store_reasoning(self, player_id: str, reasoning_type: str, data: Dict[str, Any]) -> None:
        """Store agent reasoning for voice script generation.

        Args:
            player_id: Player who made the decision
            reasoning_type: Type of reasoning (vote, murder, vote_to_end, etc.)
            data: Full response data including reasoning
        """
        day = self.game_state.day
        if day not in self.agent_reasoning_by_day:
            self.agent_reasoning_by_day[day] = {}
        if player_id not in self.agent_reasoning_by_day[day]:
            self.agent_reasoning_by_day[day][player_id] = {}

        self.agent_reasoning_by_day[day][player_id][reasoning_type] = data

    async def _collect_votes_parallel_async(self) -> Dict[str, str]:
        """Collect votes from all alive players in parallel via HTTP.

        Returns:
            Dict mapping player_id -> voted_player_id
        """
        alive_players = [p for p in self.game_state.alive_players]
        game_state_data = self._serialize_game_state()

        async with httpx.AsyncClient(timeout=120.0) as client:
            async def vote_via_http(player: Player) -> Tuple[str, str, Dict[str, Any]]:
                """Get vote from agent container via HTTP."""
                try:
                    url = self.agent_urls[player.id]
                    response = await client.post(
                        f"{url}/vote",
                        json={"game_state": game_state_data}
                    )
                    response.raise_for_status()
                    data = response.json()
                    return (player.id, data['target_player_id'], data)
                except Exception as e:
                    self.logger.error(f"Error getting vote from {player.name}: {e}")
                    return (player.id, self._emergency_vote(player.id), {"reasoning": "Error fallback"})

            # Execute votes in parallel
            vote_tasks = [vote_via_http(p) for p in alive_players]
            vote_results = await asyncio.gather(*vote_tasks)

            # Convert to dict and capture reasoning
            votes = {}
            for pid, target, data in vote_results:
                votes[pid] = target
                # Store vote reasoning for voice scripts
                self._store_reasoning(pid, "vote_result", {
                    "target_player_id": target,
                    "reasoning": data.get("reasoning", ""),
                })

            return votes

    async def _resolve_vote_tie_async(self, vote_counts: Counter, original_votes: Dict[str, str]) -> str:
        """Resolve voting ties using configured tie-breaking method.

        Args:
            vote_counts: Counter of votes per player
            original_votes: Dict of voter_id -> target_id

        Returns:
            Player ID of banished player
        """
        if len(vote_counts) == 0:
            self.logger.error("No votes cast!")
            return list(self.game_state.alive_players)[0].id

        # Get max vote count
        max_votes = vote_counts.most_common(1)[0][1]

        # Get all players with max votes (tied players)
        tied_players = [pid for pid, count in vote_counts.items() if count == max_votes]

        if len(tied_players) == 1:
            # No tie, clear winner
            return tied_players[0]

        # TIE - Apply tie-breaking method
        tied_names = [self.game_state.get_player(pid).name for pid in tied_players]
        self.logger.info(f"\n⚖️  TIE: {len(tied_players)} players with {max_votes} votes each: {', '.join(tied_names)}")

        if self.config.tie_break_method == "random":
            return self._tie_break_random(tied_players)
        elif self.config.tie_break_method == "revote":
            return await self._tie_break_revote_async(tied_players)
        elif self.config.tie_break_method == "countback":
            return self._tie_break_countback(tied_players)
        else:
            self.logger.warning(f"Unknown tie-break method: {self.config.tie_break_method}, using random")
            return self._tie_break_random(tied_players)

    def _tie_break_random(self, tied_players: List[str]) -> str:
        """Break tie with random selection.

        Args:
            tied_players: List of player IDs in the tie

        Returns:
            Randomly selected player ID
        """
        import random
        selected = random.choice(tied_players)
        selected_player = self.game_state.get_player(selected)
        self.logger.info(f"🎲 Random tie-break: {selected_player.name}")
        return selected

    async def _tie_break_revote_async(self, tied_players: List[str]) -> str:
        """Break tie with revote (tied players immune).

        Args:
            tied_players: List of player IDs in the tie

        Returns:
            Player ID selected in revote
        """
        self.logger.info(f"🔄 REVOTE: Tied players are immune, others vote again")

        # Temporarily remove tied players from alive list for voting
        original_alive = self.game_state.alive_players.copy()
        eligible_voters = [p for p in original_alive if p.id not in tied_players]

        if len(eligible_voters) == 0:
            self.logger.warning("No eligible voters for revote, using random")
            return self._tie_break_random(tied_players)

        # Collect revotes (only from non-tied players)
        game_state_data = self._serialize_game_state()
        revotes = {}

        async with httpx.AsyncClient(timeout=120.0) as client:
            for voter in eligible_voters:
                try:
                    url = self.agent_urls[voter.id]
                    response = await client.post(
                        f"{url}/vote",
                        json={"game_state": game_state_data}
                    )
                    response.raise_for_status()
                    data = response.json()
                    target_id = data['target_player_id']

                    # Ignore votes for tied players (they're immune)
                    if target_id not in tied_players:
                        revotes[voter.id] = target_id
                except Exception as e:
                    self.logger.error(f"Error in revote from {voter.name}: {e}")

        if len(revotes) == 0:
            self.logger.warning("No valid revotes, using random")
            return self._tie_break_random(tied_players)

        # Tally revotes
        revote_counts = Counter(revotes.values())
        winner_id = revote_counts.most_common(1)[0][0]
        winner = self.game_state.get_player(winner_id)

        self.logger.info(f"✅ Revote result: {winner.name} selected")
        return winner_id

    def _tie_break_countback(self, tied_players: List[str]) -> str:
        """Break tie with countback (cumulative season votes).

        Args:
            tied_players: List of player IDs in the tie

        Returns:
            Player ID with most cumulative votes
        """
        self.logger.info(f"📊 COUNTBACK: Checking cumulative season votes")

        # Count total votes each tied player has received all season
        cumulative_votes = {pid: 0 for pid in tied_players}

        for vote_record in self.game_state.vote_history:
            for voter_id, target_id in vote_record.items():
                if target_id in tied_players:
                    cumulative_votes[target_id] += 1

        # Player with MOST cumulative votes is banished
        max_cumulative = max(cumulative_votes.values())
        candidates = [pid for pid, count in cumulative_votes.items() if count == max_cumulative]

        if len(candidates) > 1:
            # Still tied on countback, use random
            self.logger.info(f"⚠️  Countback also tied, using random selection")
            return self._tie_break_random(candidates)

        selected = candidates[0]
        selected_player = self.game_state.get_player(selected)
        self.logger.info(f"✅ Countback result: {selected_player.name} ({cumulative_votes[selected]} cumulative votes)")
        return selected

    async def _choose_murder_victim_http(self, traitor_id: str, death_list: Optional[List[str]] = None) -> Optional[str]:
        """Have traitor choose murder victim via HTTP.

        Args:
            traitor_id: ID of the traitor making the choice
            death_list: Optional list of valid victim IDs (Death List mechanic)

        Returns:
            Player ID of victim, or None if failed
        """
        try:
            url = self.agent_urls[traitor_id]
            game_state_data = self._serialize_game_state()

            payload = {"game_state": game_state_data}
            if death_list:
                payload["death_list"] = death_list  # Restrict victim choices

            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{url}/choose_murder_victim",
                    json=payload
                )
                response.raise_for_status()
                data = response.json()

                # Store murder reasoning for voice scripts
                self._store_reasoning(traitor_id, "murder_result", {
                    "target_player_id": data['target_player_id'],
                    "reasoning": data.get("reasoning", ""),
                })

                return data['target_player_id']
        except Exception as e:
            self.logger.error(f"Error choosing murder victim: {e}")
            # Fallback: random from death_list or all faithful
            import random
            if death_list:
                return random.choice(death_list) if death_list else None
            return None

    async def _run_end_game_async(self) -> Optional[Role]:
        """Run end game mechanics (Vote to End or Traitor's Dilemma).

        Returns:
            Winner role if game ends, None to continue
        """
        alive_count = len(self.game_state.alive_players)
        traitor_count = len(self.game_state.alive_traitors)

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"END GAME TRIGGERED: {alive_count} players remaining")
        self.logger.info(f"{'='*60}\n")

        # Check if Traitor's Dilemma should trigger (exactly 2 Traitors, no Faithful)
        if (self.config.end_game_type == "traitors_dilemma" and
            traitor_count == 2 and len(self.game_state.alive_faithful) == 0):
            return await self._run_traitors_dilemma_async()

        # Otherwise, run Vote to End
        return await self._run_vote_to_end_async()

    async def _run_vote_to_end_async(self) -> Optional[Role]:
        """Run Vote to End mechanic (Final N vote).

        Players vote whether to END or BANISH again.
        Requires unanimous END vote to finish.

        Returns:
            Winner role if unanimous END, None to continue
        """
        self.logger.info("\n--- Vote to End ---")
        self.logger.info("Players must decide: END the game or BANISH again?")
        self.logger.info("Unanimous END required to finish.\n")

        # Collect votes via HTTP
        votes = {}
        game_state_data = self._serialize_game_state()

        async with httpx.AsyncClient(timeout=120.0) as client:
            for player in self.game_state.alive_players:
                try:
                    url = self.agent_urls[player.id]
                    response = await client.post(
                        f"{url}/vote_to_end",
                        json={"game_state": game_state_data}
                    )
                    response.raise_for_status()
                    data = response.json()
                    vote = data['vote']
                    reasoning = data.get('reasoning', '')
                    votes[player.id] = vote
                    self.logger.info(f"{player.name} votes {vote}: {reasoning}")

                    # Store vote_to_end reasoning for voice scripts
                    self._store_reasoning(player.id, "vote_to_end_result", {
                        "vote": vote,
                        "reasoning": reasoning,
                    })
                except Exception as e:
                    self.logger.error(f"Error getting vote from {player.name}: {e}")
                    votes[player.id] = "BANISH"  # Default to BANISH on error

        # Check for unanimity
        end_votes = sum(1 for v in votes.values() if v == "END")
        total_votes = len(votes)

        self.logger.info(f"\nVote Result: {end_votes}/{total_votes} voted END")

        if end_votes == total_votes:
            # Unanimous END
            self.logger.info("✅ UNANIMOUS END - Game concludes!")

            # Determine winner
            if len(self.game_state.alive_traitors) > 0:
                # Traitors win
                return Role.TRAITOR
            else:
                # Faithful win
                return Role.FAITHFUL
        else:
            self.logger.info("❌ Not unanimous - Continue to next Round Table")
            return None

    async def _run_traitors_dilemma_async(self) -> Role:
        """Run Traitor's Dilemma (Prisoner's Dilemma with 2 Traitors).

        Each Traitor chooses SHARE or STEAL:
        - Both SHARE: Split pot 50/50
        - One STEAL, one SHARE: Stealer gets 100%
        - Both STEAL: Both get 0% (pot burned)

        Returns:
            Winner role (always TRAITOR, but with different outcomes)
        """
        self.logger.info("\n" + "="*60)
        self.logger.info("⚔️  TRAITOR'S DILEMMA")
        self.logger.info("="*60)
        self.logger.info("Two Traitors remain. Each must choose: SHARE or STEAL")
        self.logger.info("")

        traitors = self.game_state.alive_traitors
        if len(traitors) != 2:
            self.logger.error(f"Traitor's Dilemma requires exactly 2 Traitors, found {len(traitors)}")
            return Role.TRAITOR

        # Collect decisions via HTTP
        decisions = {}
        game_state_data = self._serialize_game_state()

        async with httpx.AsyncClient(timeout=120.0) as client:
            for traitor in traitors:
                try:
                    url = self.agent_urls[traitor.id]
                    response = await client.post(
                        f"{url}/share_or_steal",
                        json={"game_state": game_state_data}
                    )
                    response.raise_for_status()
                    data = response.json()
                    decision = data['decision']
                    reasoning = data.get('reasoning', '')
                    decisions[traitor.id] = decision
                    self.logger.info(f"🤫 {traitor.name} decides (secretly): {reasoning}")

                    # Store dilemma reasoning for voice scripts
                    self._store_reasoning(traitor.id, "dilemma_result", {
                        "decision": decision,
                        "reasoning": reasoning,
                    })
                except Exception as e:
                    self.logger.error(f"Error getting decision from {traitor.name}: {e}")
                    decisions[traitor.id] = "STEAL"  # Default to STEAL on error

        # Reveal results
        t1, t2 = traitors[0], traitors[1]
        d1, d2 = decisions[t1.id], decisions[t2.id]

        self.logger.info("\n" + "="*60)
        self.logger.info("THE REVEAL")
        self.logger.info("="*60)
        self.logger.info(f"{t1.name} chose: {d1}")
        self.logger.info(f"{t2.name} chose: {d2}\n")

        # Determine outcome
        if d1 == "SHARE" and d2 == "SHARE":
            self.logger.info("💰 Both SHARED - They split the pot 50/50!")
            self.logger.info(f"{t1.name}: ${self.game_state.prize_pot/2:,.0f}")
            self.logger.info(f"{t2.name}: ${self.game_state.prize_pot/2:,.0f}")
        elif d1 == "STEAL" and d2 == "STEAL":
            self.logger.info("🔥 Both STOLE - The pot is BURNED! Nobody wins!")
            self.logger.info(f"${self.game_state.prize_pot:,.0f} goes up in flames!")
        elif d1 == "STEAL":
            self.logger.info(f"💸 {t1.name} STOLE - Takes everything!")
            self.logger.info(f"{t1.name}: ${self.game_state.prize_pot:,.0f}")
            self.logger.info(f"{t2.name}: $0")
        else:  # d2 == "STEAL"
            self.logger.info(f"💸 {t2.name} STOLE - Takes everything!")
            self.logger.info(f"{t2.name}: ${self.game_state.prize_pot:,.0f}")
            self.logger.info(f"{t1.name}: $0")

        return Role.TRAITOR

    async def _parallel_reflection_async(self, events: List[str]) -> None:
        """Have all alive agents reflect on events in parallel via HTTP.

        Args:
            events: List of event descriptions
        """
        alive_players = self.game_state.alive_players
        game_state_data = self._serialize_game_state()

        async with httpx.AsyncClient(timeout=120.0) as client:
            async def reflect_via_http(player: Player):
                """Trigger reflection in agent container via HTTP."""
                try:
                    url = self.agent_urls[player.id]
                    response = await client.post(
                        f"{url}/reflect",
                        json={
                            "game_state": game_state_data,
                            "events": events
                        }
                    )
                    response.raise_for_status()
                except Exception as e:
                    self.logger.error(f"Error in reflection for {player.name}: {e}")

            # Execute reflections in parallel
            reflection_tasks = [reflect_via_http(p) for p in alive_players]
            await asyncio.gather(*reflection_tasks, return_exceptions=True)

    def _emergency_vote(self, player_id: str) -> str:
        """Emergency fallback vote.

        Args:
            player_id: ID of voting player

        Returns:
            Random valid target
        """
        import random

        valid_targets = [
            p.id for p in self.game_state.alive_players if p.id != player_id
        ]
        return random.choice(valid_targets) if valid_targets else player_id

    def save_game_report(self, output_path: str = None) -> str:
        """Save complete game data to JSON for UI visualization.

        Uses the canonical to_export_dict() method to ensure all data
        needed by the TraitorSim UI is included.

        Args:
            output_path: Optional path to save JSON. Defaults to reports/{timestamp}.json

        Returns:
            Path to the saved JSON file
        """
        import json
        from datetime import datetime
        from pathlib import Path

        # Default path - use mounted volume in container, or local reports dir
        if output_path is None:
            import os
            # Check for container environment (mounted at /app/data)
            if os.path.isdir("/app/data"):
                reports_dir = Path("/app/data/reports")
            else:
                reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = reports_dir / f"game_{timestamp}.json"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build complete game report
        game_data = self.game_state.to_export_dict()

        # Add game-level metadata
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

        # Convert numpy arrays and other non-JSON-serializable types
        def make_serializable(obj):
            if hasattr(obj, 'tolist'):  # numpy array
                return obj.tolist()
            elif hasattr(obj, 'value'):  # enum
                return obj.value
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [make_serializable(v) for v in obj]
            return obj

        game_data = make_serializable(game_data)

        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(game_data, f, indent=2, default=str)

        self.logger.info(f"Game report saved: {output_path}")
        return str(output_path)

    # Synchronous wrapper
    def run_game(self) -> str:
        """Synchronous wrapper for run_game_async."""
        return asyncio.run(self.run_game_async())

    # =========================================================================
    # VOICE INTEGRATION HOOKS
    # =========================================================================

    def generate_voice_scripts(self, output_dir: Optional[str] = None) -> str:
        """Generate voice scripts for all game days.

        Creates DialogueScript files for each day that can be used
        for ElevenLabs voice synthesis (Episode Mode).

        Args:
            output_dir: Directory for output. Defaults to reports/voice_scripts/

        Returns:
            Path to output directory
        """
        from pathlib import Path
        from ..voice import (
            EpisodeGenerator,
            EpisodeGeneratorConfig,
            export_season_scripts,
        )

        # Default output directory
        if output_dir is None:
            reports_dir = Path("reports")
            if Path("/app/data").is_dir():
                reports_dir = Path("/app/data/reports")
            output_dir = reports_dir / "voice_scripts"

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Export all episode scripts with captured reasoning
        export_season_scripts(
            game_state=self.game_state,
            output_path=str(output_path),
            agent_reasoning_by_day=self.agent_reasoning_by_day,
            config=EpisodeGeneratorConfig(
                include_cold_open=True,
                include_preview=True,
                include_social_phase=True,
            )
        )

        self.logger.info(f"📜 Voice scripts generated: {output_path}")
        return str(output_path)

    def generate_single_day_script(self, day: int) -> Optional["DialogueScript"]:
        """Generate voice script for a single day.

        Args:
            day: Day number to generate script for

        Returns:
            DialogueScript for the day, or None if no events
        """
        from ..voice import extract_script_from_game_state

        try:
            return extract_script_from_game_state(
                game_state=self.game_state,
                day=day,
                agent_reasoning=self.agent_reasoning_by_day.get(day),
            )
        except Exception as e:
            self.logger.error(f"Error generating voice script for day {day}: {e}")
            return None

    def get_player_voice_config(self, player_id: str) -> Optional[Dict]:
        """Get voice configuration for a player.

        Returns ElevenLabs API parameters for the player's voice
        based on their archetype and personality.

        Args:
            player_id: Player ID

        Returns:
            Dict with voice_id and voice_settings, or None
        """
        from ..voice import get_voice_config_for_persona

        player = self.game_state.get_player(player_id)
        if not player:
            return None

        persona_data = {
            "archetype_id": player.archetype_id,
            "demographics": player.demographics,
            "personality": player.personality,
        }

        config = get_voice_config_for_persona(persona_data)
        return config.to_api_params()

    def get_agent_reasoning(self, day: Optional[int] = None) -> Dict[int, Dict[str, Dict[str, Any]]]:
        """Get captured agent reasoning for voice script generation.

        Args:
            day: Optional specific day to retrieve. If None, returns all days.

        Returns:
            Dict of {day: {player_id: {reasoning_type: data}}}
        """
        if day is not None:
            return {day: self.agent_reasoning_by_day.get(day, {})}
        return self.agent_reasoning_by_day.copy()

    def export_reasoning_to_json(self, output_path: Optional[str] = None) -> str:
        """Export captured reasoning to JSON file.

        Useful for debugging and post-game analysis.

        Args:
            output_path: Optional path. Defaults to reports/reasoning.json

        Returns:
            Path to the exported file
        """
        import json

        if output_path is None:
            reports_dir = Path("reports")
            if Path("/app/data").is_dir():
                reports_dir = Path("/app/data/reports")
            reports_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(reports_dir / "agent_reasoning.json")

        with open(output_path, "w") as f:
            json.dump(self.agent_reasoning_by_day, f, indent=2)

        self.logger.info(f"📝 Agent reasoning exported: {output_path}")
        return output_path
