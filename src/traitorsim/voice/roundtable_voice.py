"""Round Table Voice Orchestrator for TraitorSim HITL Mode.

Coordinates multi-speaker voice interaction during the Round Table phase,
managing turn-taking between AI agents and the human player, handling
interruptions, and creating dramatic tension through pacing and narrator
interjections.

The Round Table is the climactic phase where accusations fly, defenses
are mounted, and ultimately one player is banished. This orchestrator
ensures the voice experience captures that drama.

Key responsibilities:
- Speaker queue management with priority ordering
- Turn-taking and interruption handling
- Accusation → Defense → Reaction flow coordination
- Voting sequence orchestration
- Narrator dramatic interjections
- Audio synthesis coordination

Usage:
    from traitorsim.voice import RoundTableOrchestrator

    orchestrator = RoundTableOrchestrator(
        hitl_handler=handler,
        tts_client=elevenlabs_client,
        voice_cache=cache_manager,
    )

    # Start orchestrated round table
    async for audio_chunk in orchestrator.run_round_table(game_state):
        await websocket.send_bytes(audio_chunk)
"""

import asyncio
import logging
import random
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Dict,
    List,
    Optional,
    Any,
    AsyncIterator,
    Callable,
    Tuple,
    Deque,
    Set,
)
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RoundTableState(str, Enum):
    """States within the Round Table phase."""
    OPENING = "opening"                  # Narrator sets the scene
    OPEN_FLOOR = "open_floor"            # Anyone can speak
    ACCUSATION = "accusation"            # Someone has made an accusation
    DEFENSE = "defense"                  # Accused is defending
    DELIBERATION = "deliberation"        # Discussion among all players
    VOTING = "voting"                    # Vote collection
    VOTE_REVEAL = "vote_reveal"          # Dramatic vote revelation
    BANISHMENT = "banishment"            # Final banishment announcement
    CLOSED = "closed"                    # Round table complete


class SpeakerPriority(int, Enum):
    """Priority levels for speaker queue."""
    NARRATOR = 100          # Highest - narrator always interrupts
    HUMAN = 80              # Human player has high priority
    ACCUSED = 70            # Accused player gets to defend
    ACCUSER = 60            # Accuser can follow up
    REACTOR = 40            # Reactions from other players
    AI_SPONTANEOUS = 20     # AI spontaneous statements
    AMBIENT = 10            # Background/ambient sounds


@dataclass
class SpeakerTurn:
    """Represents a speaker's turn in the queue."""
    speaker_id: str
    speaker_name: str
    text: str
    emotion: str = ""
    priority: SpeakerPriority = SpeakerPriority.AI_SPONTANEOUS
    allow_interruption: bool = True
    is_human: bool = False
    turn_type: str = "statement"         # statement, accusation, defense, vote
    target: Optional[str] = None          # Target of accusation/vote
    metadata: Dict[str, Any] = field(default_factory=dict)
    queued_at: datetime = field(default_factory=datetime.now)

    def is_stale(self, max_age_seconds: float = 30.0) -> bool:
        """Check if this turn has been waiting too long."""
        age = (datetime.now() - self.queued_at).total_seconds()
        return age > max_age_seconds


@dataclass
class AccusationContext:
    """Tracks the current accusation flow."""
    accuser_id: str
    accuser_name: str
    target_id: str
    target_name: str
    accusation_text: str
    timestamp: datetime = field(default_factory=datetime.now)
    defense_given: bool = False
    reactions_collected: List[str] = field(default_factory=list)
    resolved: bool = False


@dataclass
class VotingState:
    """Tracks voting progress."""
    votes: Dict[str, str] = field(default_factory=dict)  # voter_id -> target_id
    vote_order: List[str] = field(default_factory=list)  # Order votes were cast
    revealed_votes: Set[str] = field(default_factory=set)  # Already revealed
    all_voted: bool = False


@dataclass
class RoundTableSession:
    """Session state for a Round Table voice interaction."""
    day: int
    state: RoundTableState = RoundTableState.OPENING
    speaker_queue: Deque[SpeakerTurn] = field(default_factory=deque)
    current_speaker: Optional[SpeakerTurn] = None
    current_accusation: Optional[AccusationContext] = None
    voting_state: Optional[VotingState] = None

    # Tracking
    statements_made: Dict[str, int] = field(default_factory=dict)  # speaker -> count
    accusations_this_round: int = 0
    human_has_spoken: bool = False
    started_at: datetime = field(default_factory=datetime.now)

    # Configuration
    max_statements_per_player: int = 5
    max_total_statements: int = 30
    voting_timeout_seconds: float = 60.0

    def get_speaker_statement_count(self, speaker_id: str) -> int:
        """Get how many times a speaker has spoken."""
        return self.statements_made.get(speaker_id, 0)

    def increment_speaker_count(self, speaker_id: str):
        """Increment speaker's statement count."""
        self.statements_made[speaker_id] = self.statements_made.get(speaker_id, 0) + 1

    def total_statements(self) -> int:
        """Get total statements made."""
        return sum(self.statements_made.values())


class RoundTableOrchestrator:
    """Orchestrates multi-speaker voice interaction during Round Table.

    This is the conductor of the Round Table drama, managing:
    - Who speaks and when
    - The flow from accusations to defenses to votes
    - Dramatic narrator interjections
    - Human player interruptions
    - Audio synthesis timing
    """

    # Narrator opening lines
    OPENING_LINES = [
        "The Round Table convenes. Suspicion hangs heavy in the air.",
        "As the candles flicker, accusations begin to form in hushed whispers.",
        "The moment of truth approaches. Someone will not survive this table.",
        "Fear and paranoia fill the room. Who among you is a traitor?",
        "Another Round Table. Another soul to be cast out. Let the games begin.",
    ]

    # Narrator voting transition lines
    VOTING_LINES = [
        "The time for talk is over. Cast your votes.",
        "No more words. No more excuses. Vote now.",
        "The table demands a sacrifice. Choose wisely.",
        "Point your finger. Seal someone's fate.",
    ]

    # Narrator vote reveal lines
    VOTE_REVEAL_LINES = [
        "The votes are in. Let us see who you have condemned.",
        "Your choices have been made. Now face the consequences.",
        "The die is cast. Who will be banished tonight?",
    ]

    # Narrator tension interjections
    TENSION_INTERJECTIONS = [
        "[pause] The room grows silent...",
        "[pause] Glances are exchanged across the table...",
        "[pause] The weight of accusation hangs in the air...",
        "[pause] Trust is a fragile thing...",
    ]

    def __init__(
        self,
        hitl_handler: Any = None,     # HITLVoiceHandler
        tts_client: Any = None,        # ElevenLabsClient
        voice_cache: Any = None,       # VoiceCacheManager
        game_engine: Any = None,       # GameEngine
        narrator_voice_id: str = "narrator",
    ):
        """Initialize Round Table orchestrator.

        Args:
            hitl_handler: HITL voice handler for processing human input
            tts_client: ElevenLabs client for TTS
            voice_cache: Voice cache for common phrases
            game_engine: Game engine for state access
            narrator_voice_id: Voice ID for narrator
        """
        self.hitl_handler = hitl_handler
        self.tts = tts_client
        self.voice_cache = voice_cache
        self.engine = game_engine
        self.narrator_voice_id = narrator_voice_id

        # Session state
        self.session: Optional[RoundTableSession] = None

        # Audio synthesis lock (only one speaker at a time)
        self._audio_lock = asyncio.Lock()

        # Event for signaling state changes
        self._state_changed = asyncio.Event()

        # Interruption handling
        self._interrupt_current = False
        self._pending_human_input: Optional[str] = None

        # Voice configs cache
        self._voice_configs: Dict[str, Dict[str, Any]] = {}

        logger.info("RoundTableOrchestrator initialized")

    def configure_voices(self, voice_configs: Dict[str, Dict[str, Any]]):
        """Configure voice settings for all players.

        Args:
            voice_configs: Mapping of player_id -> voice config
        """
        self._voice_configs = voice_configs

    async def run_round_table(
        self,
        day: int,
        players: List[Dict[str, Any]],
        human_player_id: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        """Run a complete Round Table phase with voice orchestration.

        This is the main entry point. It yields audio chunks as the
        Round Table progresses through all its dramatic stages.

        Args:
            day: Current game day
            players: List of alive players
            human_player_id: ID of the human player (if any)

        Yields:
            Audio chunks for playback
        """
        # Initialize session
        self.session = RoundTableSession(day=day)
        logger.info(f"Starting Round Table for Day {day}")

        try:
            # === Stage 1: Opening ===
            self.session.state = RoundTableState.OPENING
            async for chunk in self._play_opening():
                yield chunk

            # === Stage 2: Open Floor / Accusations ===
            self.session.state = RoundTableState.OPEN_FLOOR
            async for chunk in self._run_deliberation_phase(
                players, human_player_id
            ):
                yield chunk

            # === Stage 3: Voting ===
            self.session.state = RoundTableState.VOTING
            async for chunk in self._run_voting_phase(players, human_player_id):
                yield chunk

            # === Stage 4: Vote Reveal & Banishment ===
            self.session.state = RoundTableState.VOTE_REVEAL
            async for chunk in self._run_reveal_phase():
                yield chunk

            self.session.state = RoundTableState.CLOSED
            logger.info("Round Table complete")

        except Exception as e:
            logger.error(f"Round Table error: {e}")
            raise
        finally:
            self.session = None

    async def _play_opening(self) -> AsyncIterator[bytes]:
        """Play the dramatic Round Table opening."""
        opening_line = random.choice(self.OPENING_LINES)

        async for chunk in self._synthesize_narrator(opening_line, "[dramatic]"):
            yield chunk

        # Brief pause for effect
        await asyncio.sleep(1.5)

    async def _run_deliberation_phase(
        self,
        players: List[Dict[str, Any]],
        human_player_id: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        """Run the main deliberation phase with accusations and defenses.

        This is where the drama happens - accusations fly, defenses are
        mounted, and alliances are tested.
        """
        logger.debug("Starting deliberation phase")

        # Prime the speaker queue with some AI opening statements
        await self._queue_ai_opening_statements(players)

        # Main deliberation loop
        max_rounds = 15  # Safety limit
        round_count = 0

        while (
            round_count < max_rounds
            and self.session.total_statements() < self.session.max_total_statements
        ):
            round_count += 1

            # Check for pending human input
            if self._pending_human_input:
                async for chunk in self._process_human_statement(
                    self._pending_human_input,
                    human_player_id,
                ):
                    yield chunk
                self._pending_human_input = None

            # Process next speaker from queue
            if self.session.speaker_queue:
                turn = self.session.speaker_queue.popleft()

                # Skip stale turns
                if turn.is_stale():
                    logger.debug(f"Skipping stale turn from {turn.speaker_name}")
                    continue

                async for chunk in self._process_speaker_turn(turn, players):
                    yield chunk

            else:
                # Queue is empty - either prompt human or add AI chatter
                if not self.session.human_has_spoken and human_player_id:
                    # Narrator prompts the human
                    async for chunk in self._prompt_human_to_speak():
                        yield chunk

                    # Wait briefly for human input
                    await asyncio.sleep(3.0)

                    if not self._pending_human_input:
                        # Human didn't respond - add AI filler
                        await self._queue_ai_filler_statement(players)
                else:
                    # Add random AI statement
                    await self._queue_ai_filler_statement(players)

            # Occasional narrator interjection for drama
            if random.random() < 0.15 and self.session.total_statements() > 3:
                async for chunk in self._play_tension_interjection():
                    yield chunk

            # Small pause between speakers
            await asyncio.sleep(0.5)

        # Transition to voting
        async for chunk in self._synthesize_narrator(
            random.choice(self.VOTING_LINES),
            "[commanding]"
        ):
            yield chunk

    async def _run_voting_phase(
        self,
        players: List[Dict[str, Any]],
        human_player_id: Optional[str] = None,
    ) -> AsyncIterator[bytes]:
        """Run the voting phase.

        Each player declares their vote, building tension before
        the final reveal.
        """
        logger.debug("Starting voting phase")

        self.session.voting_state = VotingState()

        # Determine vote order (human goes last for drama)
        vote_order = [p["id"] for p in players if p.get("alive", True)]
        if human_player_id and human_player_id in vote_order:
            vote_order.remove(human_player_id)
            vote_order.append(human_player_id)

        self.session.voting_state.vote_order = vote_order

        # Collect votes
        for player_id in vote_order:
            player = next((p for p in players if p["id"] == player_id), None)
            if not player:
                continue

            if player_id == human_player_id:
                # Human vote - wait for input
                async for chunk in self._collect_human_vote(player):
                    yield chunk
            else:
                # AI vote
                async for chunk in self._collect_ai_vote(player, players):
                    yield chunk

            # Brief pause between votes
            await asyncio.sleep(0.8)

        self.session.voting_state.all_voted = True

    async def _run_reveal_phase(self) -> AsyncIterator[bytes]:
        """Run the dramatic vote reveal and banishment."""
        logger.debug("Starting reveal phase")

        # Narrator announces vote reveal
        async for chunk in self._synthesize_narrator(
            random.choice(self.VOTE_REVEAL_LINES),
            "[dramatic]"
        ):
            yield chunk

        await asyncio.sleep(2.0)

        # Count votes
        if self.session.voting_state:
            vote_counts: Dict[str, int] = {}
            for target_id in self.session.voting_state.votes.values():
                vote_counts[target_id] = vote_counts.get(target_id, 0) + 1

            # Find the banished player
            if vote_counts:
                banished_id = max(vote_counts.keys(), key=lambda k: vote_counts[k])
                banished_count = vote_counts[banished_id]

                # Get banished player name
                banished_name = await self._get_player_name(banished_id)

                # Dramatic announcement
                self.session.state = RoundTableState.BANISHMENT

                banishment_text = (
                    f"By a vote of {banished_count}... "
                    f"[pause] {banished_name}... "
                    f"[long pause] You have been banished."
                )

                async for chunk in self._synthesize_narrator(
                    banishment_text,
                    "[dramatic][slow]"
                ):
                    yield chunk

                await asyncio.sleep(2.0)

                # Role reveal
                role = await self._get_player_role(banished_id)
                role_text = (
                    f"{banished_name} was... "
                    f"[dramatic pause] a {role.upper()}."
                )

                async for chunk in self._synthesize_narrator(
                    role_text,
                    "[revelation]"
                ):
                    yield chunk

    # === Speaker Queue Management ===

    def queue_speaker(
        self,
        speaker_id: str,
        speaker_name: str,
        text: str,
        emotion: str = "",
        priority: SpeakerPriority = SpeakerPriority.AI_SPONTANEOUS,
        turn_type: str = "statement",
        target: Optional[str] = None,
        allow_interruption: bool = True,
        is_human: bool = False,
    ):
        """Add a speaker to the queue."""
        turn = SpeakerTurn(
            speaker_id=speaker_id,
            speaker_name=speaker_name,
            text=text,
            emotion=emotion,
            priority=priority,
            turn_type=turn_type,
            target=target,
            allow_interruption=allow_interruption,
            is_human=is_human,
        )

        # Insert based on priority (higher priority goes first)
        inserted = False
        for i, existing in enumerate(self.session.speaker_queue):
            if turn.priority.value > existing.priority.value:
                self.session.speaker_queue.insert(i, turn)
                inserted = True
                break

        if not inserted:
            self.session.speaker_queue.append(turn)

        logger.debug(f"Queued speaker: {speaker_name} (priority: {priority.name})")

    async def _queue_ai_opening_statements(self, players: List[Dict[str, Any]]):
        """Queue opening statements from AI players."""
        # Select 2-3 players to make opening statements
        ai_players = [p for p in players if not p.get("is_human", False)]
        openers = random.sample(ai_players, min(3, len(ai_players)))

        opening_statements = [
            "I've been watching everyone closely...",
            "Something doesn't feel right today.",
            "We need to be more careful about who we trust.",
            "I have my suspicions, but I'm keeping them close.",
            "Let's think about this logically.",
        ]

        for player in openers:
            statement = random.choice(opening_statements)
            self.queue_speaker(
                speaker_id=player["id"],
                speaker_name=player.get("name", "Unknown"),
                text=statement,
                emotion="[thoughtful]",
                priority=SpeakerPriority.AI_SPONTANEOUS,
            )

    async def _queue_ai_filler_statement(self, players: List[Dict[str, Any]]):
        """Queue a filler statement to keep conversation moving."""
        ai_players = [
            p for p in players
            if not p.get("is_human", False) and p.get("alive", True)
        ]

        if not ai_players:
            return

        # Select a player who hasn't spoken much
        least_spoken = min(
            ai_players,
            key=lambda p: self.session.get_speaker_statement_count(p["id"])
        )

        filler_statements = [
            "I'm not sure what to think anymore.",
            "We're running out of time.",
            "Someone here is lying to all of us.",
            "I wish I knew who to trust.",
            "The traitors are getting desperate.",
            "We can't afford another mistake.",
        ]

        self.queue_speaker(
            speaker_id=least_spoken["id"],
            speaker_name=least_spoken.get("name", "Unknown"),
            text=random.choice(filler_statements),
            emotion="[uncertain]",
            priority=SpeakerPriority.AI_SPONTANEOUS,
        )

    # === Turn Processing ===

    async def _process_speaker_turn(
        self,
        turn: SpeakerTurn,
        players: List[Dict[str, Any]],
    ) -> AsyncIterator[bytes]:
        """Process a single speaker's turn."""
        self.session.current_speaker = turn
        self.session.increment_speaker_count(turn.speaker_id)

        logger.debug(f"Processing turn: {turn.speaker_name} - {turn.turn_type}")

        try:
            # Synthesize and play the statement
            async for chunk in self._synthesize_speaker(
                turn.speaker_id,
                turn.speaker_name,
                turn.text,
                turn.emotion,
            ):
                # Check for interruption
                if self._interrupt_current and turn.allow_interruption:
                    logger.debug(f"Turn interrupted: {turn.speaker_name}")
                    self._interrupt_current = False
                    break

                yield chunk

            # Handle turn type-specific logic
            if turn.turn_type == "accusation" and turn.target:
                await self._handle_accusation_turn(turn, players)

            elif turn.turn_type == "defense":
                await self._handle_defense_turn(turn)

        finally:
            self.session.current_speaker = None

    async def _handle_accusation_turn(
        self,
        turn: SpeakerTurn,
        players: List[Dict[str, Any]],
    ):
        """Handle an accusation by queueing defense and reactions."""
        # Create accusation context
        target_player = next(
            (p for p in players if p.get("name", "").lower() == turn.target.lower()),
            None
        )

        if not target_player:
            return

        self.session.current_accusation = AccusationContext(
            accuser_id=turn.speaker_id,
            accuser_name=turn.speaker_name,
            target_id=target_player["id"],
            target_name=target_player.get("name", "Unknown"),
            accusation_text=turn.text,
        )

        self.session.accusations_this_round += 1
        self.session.state = RoundTableState.ACCUSATION

        # Queue defense from accused
        defense_text = await self._generate_defense(
            target_player,
            turn.text,
            turn.speaker_name,
        )

        self.queue_speaker(
            speaker_id=target_player["id"],
            speaker_name=target_player.get("name", "Unknown"),
            text=defense_text,
            emotion="[defensive]",
            priority=SpeakerPriority.ACCUSED,
            turn_type="defense",
        )

        # Queue reactions from other players
        await self._queue_accusation_reactions(turn, players)

    async def _handle_defense_turn(self, turn: SpeakerTurn):
        """Handle a defense, potentially queueing follow-up challenges."""
        if self.session.current_accusation:
            self.session.current_accusation.defense_given = True
            self.session.state = RoundTableState.DELIBERATION

    async def _queue_accusation_reactions(
        self,
        accusation_turn: SpeakerTurn,
        players: List[Dict[str, Any]],
    ):
        """Queue reactions from other players to an accusation."""
        # Select 1-2 players to react (excluding accuser and target)
        reactors = [
            p for p in players
            if p["id"] != accusation_turn.speaker_id
            and p.get("name", "").lower() != accusation_turn.target.lower()
            and p.get("alive", True)
            and not p.get("is_human", False)
        ]

        if not reactors:
            return

        selected = random.sample(reactors, min(2, len(reactors)))

        reaction_templates = {
            "support": [
                f"I've been thinking the same thing about {accusation_turn.target}.",
                f"There might be something to that.",
                f"{accusation_turn.target} has been acting suspicious.",
            ],
            "oppose": [
                f"Hold on, let's not jump to conclusions.",
                f"I'm not convinced. {accusation_turn.target} has been helpful.",
                f"Are we sure about this?",
            ],
            "neutral": [
                f"Interesting point...",
                f"Let's hear what {accusation_turn.target} has to say.",
                f"We should consider all the evidence.",
            ],
        }

        for player in selected:
            stance = random.choice(["support", "oppose", "neutral"])
            reaction = random.choice(reaction_templates[stance])

            self.queue_speaker(
                speaker_id=player["id"],
                speaker_name=player.get("name", "Unknown"),
                text=reaction,
                emotion="[thoughtful]",
                priority=SpeakerPriority.REACTOR,
            )

    # === Human Interaction ===

    async def _process_human_statement(
        self,
        text: str,
        human_player_id: str,
    ) -> AsyncIterator[bytes]:
        """Process a statement from the human player."""
        self.session.human_has_spoken = True

        # Use HITL handler for intent classification
        if self.hitl_handler:
            intent = self.hitl_handler.classifier.classify(text)

            # Handle based on intent
            if intent.type.value == "accusation" and intent.target:
                self.queue_speaker(
                    speaker_id=human_player_id,
                    speaker_name="You",
                    text=text,
                    priority=SpeakerPriority.HUMAN,
                    turn_type="accusation",
                    target=intent.target,
                    is_human=True,
                )
            elif intent.type.value == "defense":
                self.queue_speaker(
                    speaker_id=human_player_id,
                    speaker_name="You",
                    text=text,
                    priority=SpeakerPriority.HUMAN,
                    turn_type="defense",
                    is_human=True,
                )
            elif intent.type.value == "vote" and intent.target:
                if self.session.voting_state:
                    self.session.voting_state.votes[human_player_id] = intent.target
                    yield b""  # Signal vote recorded
        else:
            # No HITL handler - just acknowledge
            async for chunk in self._synthesize_narrator(
                "The table considers your words.",
                "[neutral]"
            ):
                yield chunk

    async def _prompt_human_to_speak(self) -> AsyncIterator[bytes]:
        """Narrator prompts the human player to speak."""
        prompts = [
            "And what say you?",
            "You've been quiet. Do you have something to share?",
            "Perhaps you have an observation?",
            "The floor is yours, if you wish to speak.",
        ]

        async for chunk in self._synthesize_narrator(
            random.choice(prompts),
            "[inviting]"
        ):
            yield chunk

    async def _collect_human_vote(
        self,
        player: Dict[str, Any],
    ) -> AsyncIterator[bytes]:
        """Collect vote from human player."""
        prompt = "It's your turn to vote. Who do you banish?"

        async for chunk in self._synthesize_narrator(prompt, "[expectant]"):
            yield chunk

        # Wait for human input (with timeout)
        timeout = self.session.voting_timeout_seconds
        start = datetime.now()

        while (datetime.now() - start).total_seconds() < timeout:
            if self._pending_human_input:
                # Process the vote
                if self.hitl_handler:
                    intent = self.hitl_handler.classifier.classify(
                        self._pending_human_input
                    )
                    if intent.target:
                        self.session.voting_state.votes[player["id"]] = intent.target

                        # Narrator confirms
                        async for chunk in self._synthesize_narrator(
                            f"Your vote is cast.",
                            "[formal]"
                        ):
                            yield chunk

                        self._pending_human_input = None
                        return

                self._pending_human_input = None

            await asyncio.sleep(0.5)

        # Timeout - random vote
        async for chunk in self._synthesize_narrator(
            "Time has run out. A vote is cast on your behalf.",
            "[warning]"
        ):
            yield chunk

    async def _collect_ai_vote(
        self,
        player: Dict[str, Any],
        all_players: List[Dict[str, Any]],
    ) -> AsyncIterator[bytes]:
        """Collect and announce vote from AI player."""
        # Generate AI vote (would integrate with game engine)
        targets = [
            p for p in all_players
            if p["id"] != player["id"] and p.get("alive", True)
        ]

        if not targets:
            return

        target = random.choice(targets)
        target_name = target.get("name", "Unknown")

        # Record vote
        self.session.voting_state.votes[player["id"]] = target["id"]

        # Announce vote
        vote_text = f"I vote for {target_name}."

        async for chunk in self._synthesize_speaker(
            player["id"],
            player.get("name", "Unknown"),
            vote_text,
            "[decisive]",
        ):
            yield chunk

    # === Audio Synthesis ===

    async def _synthesize_narrator(
        self,
        text: str,
        emotion: str = "",
    ) -> AsyncIterator[bytes]:
        """Synthesize narrator audio."""
        async for chunk in self._synthesize_speaker(
            "narrator",
            "Narrator",
            text,
            emotion,
        ):
            yield chunk

    async def _synthesize_speaker(
        self,
        speaker_id: str,
        speaker_name: str,
        text: str,
        emotion: str = "",
    ) -> AsyncIterator[bytes]:
        """Synthesize audio for a speaker.

        Args:
            speaker_id: Speaker's player ID
            speaker_name: Speaker's display name
            text: Text to speak
            emotion: Emotion tags for TTS

        Yields:
            Audio chunks
        """
        async with self._audio_lock:
            # Check voice cache first
            if self.voice_cache:
                cached = await self.voice_cache.get(speaker_id, text)
                if cached:
                    logger.debug(f"Cache hit for {speaker_name}: {text[:30]}...")
                    yield cached
                    return

            # Get voice config
            voice_config = self._voice_configs.get(speaker_id, {})
            voice_id = voice_config.get("voice_id", self.narrator_voice_id)

            # Synthesize with TTS
            if self.tts:
                try:
                    # Add emotion tags to text
                    tagged_text = f"{emotion} {text}" if emotion else text

                    # Stream synthesis
                    async for chunk in self.tts.synthesize_stream(
                        text=tagged_text,
                        voice_id=voice_id,
                        model_id="eleven_flash_v2_5",  # Low latency model
                    ):
                        yield chunk

                except Exception as e:
                    logger.error(f"TTS error for {speaker_name}: {e}")
                    # Yield empty on error (client will handle silence)
                    yield b""
            else:
                # No TTS client - log only
                logger.info(f"[{speaker_name}] {text}")
                yield b""

    async def _play_tension_interjection(self) -> AsyncIterator[bytes]:
        """Play a random tension-building narrator interjection."""
        interjection = random.choice(self.TENSION_INTERJECTIONS)

        async for chunk in self._synthesize_narrator(interjection, "[whispered]"):
            yield chunk

    # === Helper Methods ===

    async def _generate_defense(
        self,
        player: Dict[str, Any],
        accusation: str,
        accuser_name: str,
    ) -> str:
        """Generate a defense statement for the accused."""
        # Would integrate with game engine / AI agent
        defense_templates = [
            f"Me? A traitor? {accuser_name}, that's absurd!",
            f"I've been nothing but loyal! Look at my contributions!",
            f"Why would I? I have no reason to betray anyone.",
            f"You're pointing fingers to deflect from yourself!",
            f"This is ridiculous. I demand evidence!",
        ]
        return random.choice(defense_templates)

    async def _get_player_name(self, player_id: str) -> str:
        """Get player name from ID."""
        if self.engine:
            try:
                player = self.engine.game_state.get_player(player_id)
                if player:
                    return player.name
            except Exception:
                pass
        return player_id

    async def _get_player_role(self, player_id: str) -> str:
        """Get player role from ID."""
        if self.engine:
            try:
                player = self.engine.game_state.get_player(player_id)
                if player:
                    return player.role.value
            except Exception:
                pass
        return "unknown"

    def handle_human_interruption(self, text: str):
        """Handle an interruption from the human player.

        Called when human starts speaking during AI turn.
        """
        if (
            self.session
            and self.session.current_speaker
            and self.session.current_speaker.allow_interruption
        ):
            self._interrupt_current = True
            self._pending_human_input = text
            logger.debug(f"Human interrupted: {text[:50]}...")

    def receive_human_input(self, text: str):
        """Receive input from the human player.

        Called when human finishes speaking.
        """
        self._pending_human_input = text
        logger.debug(f"Human input received: {text[:50]}...")


# === Convenience Functions ===


def create_roundtable_orchestrator(
    hitl_handler: Any = None,
    tts_client: Any = None,
    voice_cache: Any = None,
    game_engine: Any = None,
) -> RoundTableOrchestrator:
    """Create a configured Round Table orchestrator.

    Args:
        hitl_handler: HITL voice handler
        tts_client: ElevenLabs TTS client
        voice_cache: Voice cache manager
        game_engine: Game engine instance

    Returns:
        Configured RoundTableOrchestrator
    """
    return RoundTableOrchestrator(
        hitl_handler=hitl_handler,
        tts_client=tts_client,
        voice_cache=voice_cache,
        game_engine=game_engine,
    )


async def run_orchestrated_roundtable(
    orchestrator: RoundTableOrchestrator,
    day: int,
    players: List[Dict[str, Any]],
    human_player_id: Optional[str] = None,
    audio_callback: Optional[Callable[[bytes], None]] = None,
) -> Dict[str, Any]:
    """Run an orchestrated Round Table and collect results.

    Args:
        orchestrator: Configured orchestrator
        day: Game day number
        players: List of player dicts
        human_player_id: Human player ID (if any)
        audio_callback: Optional callback for audio chunks

    Returns:
        Dict with Round Table results (votes, banished player, etc.)
    """
    async for chunk in orchestrator.run_round_table(day, players, human_player_id):
        if audio_callback and chunk:
            audio_callback(chunk)

    # Return results from the session
    results = {
        "day": day,
        "total_statements": orchestrator.session.total_statements() if orchestrator.session else 0,
    }

    if orchestrator.session and orchestrator.session.voting_state:
        results["votes"] = dict(orchestrator.session.voting_state.votes)

    return results
