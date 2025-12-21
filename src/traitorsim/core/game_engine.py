"""Main game loop orchestrator."""

import logging
import random
from typing import Dict, Optional, List

from .game_state import GameState, GamePhase, Role, Player, TrustMatrix
from .config import GameConfig
from ..agents.game_master import GameMaster
from ..agents.player_agent import PlayerAgent
from ..missions.skill_check import SkillCheckMission


# List of player names for the simulation
PLAYER_NAMES = [
    "Alice", "Bob", "Claire", "David", "Emma",
    "Frank", "Grace", "Henry", "Iris", "Jack",
    "Kate", "Liam", "Maya", "Noah", "Olivia",
    "Paul", "Quinn", "Rachel", "Sam", "Tara"
]


class GameEngine:
    """
    Core game loop orchestrator.
    Manages state transitions and enforces game rules.
    """

    def __init__(self, config: GameConfig):
        """Initialize game engine."""
        self.config = config
        self.state = GameState()
        self.game_master = GameMaster(config)
        self.player_agents: Dict[str, PlayerAgent] = {}

        self.logger = logging.getLogger(__name__)

    def initialize_game(self):
        """Set up initial game state."""
        self.logger.info("Initializing game...")

        # Create players
        players = self._create_players()
        self.state.players = players

        # Assign roles
        self._assign_roles()

        # Initialize trust matrix
        player_ids = [p.id for p in players]
        self.state.trust_matrix = TrustMatrix(player_ids)

        # Initialize player agents
        for player in players:
            agent = PlayerAgent(player=player, config=self.config, game_state=self.state)
            self.player_agents[player.id] = agent

        # GM announces game start
        announcement = self.game_master.announce_game_start(self.state)
        self.logger.info(f"\n{announcement}\n")

        self.state.phase = GamePhase.BREAKFAST
        self.logger.info("Game initialized.")
        self.logger.info(f"Players: {', '.join([p.name for p in players])}")
        traitors = [p.name for p in self.state.alive_traitors]
        self.logger.info(f"Traitors (hidden): {', '.join(traitors)}\n")

    def run_game(self):
        """Main game loop."""
        self.initialize_game()

        while self.state.phase != GamePhase.ENDED:
            if self.state.day > self.config.max_days:
                self.logger.warning(f"Max days ({self.config.max_days}) reached. Ending game.")
                self.end_game(None)
                break

            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"DAY {self.state.day}")
            self.logger.info(f"{'='*60}\n")
            self.run_day_cycle()

            # Check win condition
            winner = self.state.check_win_condition()
            if winner:
                self.end_game(winner)
                break

            self.state.day += 1

    def run_day_cycle(self):
        """Execute one complete day cycle."""

        # Phase 1: Breakfast (reveal murder)
        self.run_breakfast_phase()

        # Check win condition after murder
        winner = self.state.check_win_condition()
        if winner:
            return

        # Phase 2: Mission
        self.run_mission_phase()

        # Phase 3: Social (MVP: simplified)
        self.run_social_phase()

        # Phase 4: Round Table (voting)
        self.run_roundtable_phase()

        # Check win condition after banishment
        winner = self.state.check_win_condition()
        if winner:
            return

        # Phase 5: Turret (murder)
        self.run_turret_phase()

    def run_breakfast_phase(self):
        """Phase 1: Reveal murder victim."""
        self.state.phase = GamePhase.BREAKFAST
        self.logger.info("--- BREAKFAST PHASE ---")

        victim = self.state.last_murder_victim

        # GM announces murder
        narrative = self.game_master.announce_murder(victim, self.state)
        self.logger.info(f"\n{narrative}\n")

    def run_mission_phase(self):
        """Phase 2: Execute mission."""
        self.state.phase = GamePhase.MISSION
        self.logger.info("--- MISSION PHASE ---")

        # Create mission (MVP: simple skill check)
        mission = SkillCheckMission(self.state, self.config)

        # GM describes mission
        description = self.game_master.describe_mission(mission.get_description())
        self.logger.info(f"\n{description}\n")

        # Execute mission
        result = mission.execute()

        # Update pot
        self.state.prize_pot += result.earnings

        # GM announces result
        announcement = self.game_master.announce_mission_result(result, self.state)
        self.logger.info(f"\n{announcement}\n")

        # Log individual performances
        for player_id, score in result.performance_scores.items():
            player = self.state.get_player(player_id)
            if player:
                status = "succeeded" if score > 0.5 else "failed"
                self.logger.debug(f"  {player.name}: {status}")

    def run_social_phase(self):
        """Phase 3: Social interaction (MVP: minimal)."""
        self.state.phase = GamePhase.SOCIAL
        self.logger.info("--- SOCIAL PHASE ---")

        # MVP: Simplified - agents just update suspicions
        # Full version would have inter-agent conversations

        for agent in self._active_agents():
            agent.reflect_on_day()

        self.logger.info("Players reflect on the day's events.\n")

    def run_roundtable_phase(self):
        """Phase 4: Public voting and banishment."""
        self.state.phase = GamePhase.ROUNDTABLE
        self.logger.info("--- ROUND TABLE PHASE ---")

        # GM opens round table
        opening = self.game_master.open_roundtable(self.state)
        self.logger.info(f"\n{opening}\n")

        # Collect votes from all alive players
        votes = self._collect_votes()

        # Tally votes
        banished = self._tally_votes(votes)

        if not banished:
            self.logger.warning("No one was banished (this shouldn't happen)")
            return

        # Process banishment
        self._process_banishment(banished)

        # GM announces result
        announcement = self.game_master.announce_banishment(banished, votes, self.state)
        self.logger.info(f"\n{announcement}\n")

    def run_turret_phase(self):
        """Phase 5: Traitors murder a Faithful."""
        self.state.phase = GamePhase.TURRET
        self.logger.info("--- TURRET PHASE ---")

        traitors = self.state.alive_traitors
        if not traitors:
            self.logger.info("No traitors remain. No murder tonight.\n")
            return

        # Traitors confer and choose victim
        victim = self._traitors_choose_victim()

        # Execute murder
        if victim:
            victim_player = self.state.get_player(victim)
            if victim_player:
                victim_player.alive = False
                self.state.murdered_players.append(victim)
                self.state.last_murder_victim = victim

                self.logger.info(f"The Traitors murdered {victim_player.name}\n")
        else:
            self.logger.warning("No victim selected for murder\n")

    def _collect_votes(self) -> Dict[str, str]:
        """Collect votes from all alive players."""
        votes = {}

        for agent in self._active_agents():
            # Agent decides who to vote for
            target = agent.cast_vote()
            votes[agent.player.id] = target

            target_player = self.state.get_player(target)
            target_name = target_player.name if target_player else target
            self.logger.info(f"  {agent.player.name} votes for {target_name}")

        # Record in history
        self.state.vote_history.append({
            "day": self.state.day,
            "votes": votes.copy()
        })

        return votes

    def _tally_votes(self, votes: Dict[str, str]) -> Optional[str]:
        """Tally votes and determine who is banished."""
        vote_counts: Dict[str, int] = {}

        for voter, target in votes.items():
            vote_counts[target] = vote_counts.get(target, 0) + 1

        if not vote_counts:
            return None

        # Find player with most votes
        max_votes = max(vote_counts.values())
        candidates = [p for p, v in vote_counts.items() if v == max_votes]

        if len(candidates) == 1:
            return candidates[0]
        else:
            # Tie-breaking (MVP: random)
            self.logger.info(f"\nTie between: {', '.join([self.state.get_player(c).name for c in candidates if self.state.get_player(c)])}")
            self.logger.info("Breaking tie randomly...")
            return random.choice(candidates)

    def _process_banishment(self, player_id: str):
        """Remove player from game and reveal role."""
        player = self.state.get_player(player_id)
        if not player:
            return

        player.alive = False
        self.state.banished_players.append(player_id)

        role_emoji = "⚔️" if player.role == Role.TRAITOR else "🛡️"
        self.logger.info(
            f"\n{role_emoji} {player.name} was banished. They were a {player.role.value.upper()}! {role_emoji}"
        )

    def _traitors_choose_victim(self) -> Optional[str]:
        """Traitors collectively choose a victim."""
        traitors = self.state.alive_traitors
        faithful = self.state.alive_faithful

        if not faithful:
            return None

        # MVP: First traitor makes decision
        # Full version would have traitor conference
        traitor_agent = self.player_agents[traitors[0].id]
        victim_id = traitor_agent.choose_murder_victim()

        return victim_id

    def _active_agents(self) -> List[PlayerAgent]:
        """Get agents for alive players."""
        return [self.player_agents[p.id] for p in self.state.alive_players]

    def _create_players(self) -> List[Player]:
        """Create player instances from persona library or random.

        Uses PersonaLoader to load pre-generated personas with archetypes,
        demographics, and backstories from the World Bible system.
        """
        if self.config.personality_generation == "archetype":
            return self._create_players_from_personas()
        else:
            # Should not reach here - archetype is the only mode
            raise ValueError(
                "personality_generation must be 'archetype'. "
                "Random generation is no longer supported."
            )

    def _create_players_from_personas(self) -> List[Player]:
        """Load players from persona library.

        Returns:
            List of Player instances with persona data

        Raises:
            FileNotFoundError: If persona library not found
            ValueError: If not enough personas available
        """
        from ..persona import PersonaLoader

        # Load persona library
        loader = PersonaLoader(persona_dir=self.config.persona_library_path)

        # Sample personas for this game
        persona_cards = loader.sample_personas(
            count=self.config.total_players,
            ensure_diversity=True,
            max_per_archetype=2  # At most 2 of same archetype
        )

        # Create Player objects from persona cards
        players = []

        for i, persona_card in enumerate(persona_cards):
            player_id = f"player_{i+1:02d}"

            # Load archetype to get sampled OCEAN/stats
            from ..core.archetypes import get_archetype

            archetype = get_archetype(persona_card.get("archetype"))

            # Sample fresh OCEAN/stats from archetype ranges
            # (allows variance within archetype even if same archetype selected)
            if archetype:
                personality = archetype.sample_ocean()
                stats = archetype.sample_stats()
            else:
                # Fallback if archetype not found
                personality = persona_card.get("personality", {})
                stats = persona_card.get("stats", {})

            player = Player(
                id=player_id,
                name=persona_card["name"],
                role=Role.FAITHFUL,  # Will be assigned later
                personality=personality,
                stats=stats,
                archetype_id=persona_card.get("archetype"),
                archetype_name=persona_card.get("archetype_name"),
                demographics=persona_card.get("demographics", {}),
                backstory=persona_card.get("backstory"),
                strategic_profile=persona_card.get("strategic_approach")
            )

            players.append(player)

        # Log persona distribution
        from collections import Counter
        archetype_counts = Counter([p.archetype_name for p in players])
        print("\n=== Persona Distribution ===")
        for archetype, count in sorted(archetype_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {archetype:30s}: {count}")
        print()

        return players

    def _assign_roles(self):
        """Assign traitor roles randomly."""
        # Randomly select traitors
        traitor_indices = random.sample(range(len(self.state.players)), self.config.num_traitors)

        for i, player in enumerate(self.state.players):
            if i in traitor_indices:
                player.role = Role.TRAITOR
            else:
                player.role = Role.FAITHFUL

    def end_game(self, winner: Optional[Role]):
        """End game and declare winner."""
        self.state.phase = GamePhase.ENDED

        if winner is None:
            self.logger.info("\n" + "="*60)
            self.logger.info("GAME ENDED - NO WINNER (Max days reached)")
            self.logger.info("="*60 + "\n")
            return

        finale = self.game_master.announce_finale(winner, self.state)
        self.logger.info("\n" + "="*60)
        self.logger.info("GAME ENDED")
        self.logger.info("="*60)
        self.logger.info(f"\n{finale}\n")

        # Show final stats
        if winner == Role.FAITHFUL:
            winners = [p.name for p in self.state.alive_faithful]
            self.logger.info(f"🛡️  FAITHFUL VICTORY! 🛡️")
            self.logger.info(f"Winners: {', '.join(winners)}")
        else:
            winners = [p.name for p in self.state.alive_traitors]
            self.logger.info(f"⚔️  TRAITOR VICTORY! ⚔️")
            self.logger.info(f"Winners: {', '.join(winners)}")

        self.logger.info(f"Final Prize Pot: ${self.state.prize_pot:,.0f}")
        self.logger.info(f"Game lasted {self.state.day} days")
        self.logger.info(f"Players murdered: {len(self.state.murdered_players)}")
        self.logger.info(f"Players banished: {len(self.state.banished_players)}\n")
