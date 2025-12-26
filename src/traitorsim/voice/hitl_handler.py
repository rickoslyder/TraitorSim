"""HITL (Human-in-the-Loop) Voice Handler for TraitorSim.

Processes human player voice input in real-time, routes it based on game phase,
classifies intent, and orchestrates AI agent responses.

The handler bridges:
- Deepgram STT (speech → text)
- Game engine (phase routing, state access)
- Claude agents (AI response generation)
- ElevenLabs TTS (text → speech)

Usage:
    from traitorsim.voice import HITLVoiceHandler

    handler = HITLVoiceHandler(
        stt_client=deepgram_client,
        tts_client=elevenlabs_client,
        game_engine=engine,
    )

    # Process voice input stream
    async for audio_chunk in handler.process_voice_input(audio_stream):
        await websocket.send_bytes(audio_chunk)
"""

import asyncio
import logging
import re
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
    Union,
)
from datetime import datetime

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Classified intent types from human speech."""
    ACCUSATION = "accusation"           # "I think X is a traitor"
    DEFENSE = "defense"                 # "I'm not a traitor because..."
    AGREEMENT = "agreement"             # "I agree with X"
    DISAGREEMENT = "disagreement"       # "I don't think that's right"
    QUESTION = "question"               # "Why did you vote for X?"
    VOTE = "vote"                       # "I vote for X"
    VOTE_TO_END = "vote_to_end"         # "I vote to end the game"
    VOTE_TO_CONTINUE = "vote_to_continue"  # "I vote to continue"
    SMALL_TALK = "small_talk"           # General conversation
    STRATEGIC = "strategic"             # Alliance proposals, strategy discussion
    EMOTIONAL = "emotional"             # Expressions of grief, anger, etc.
    UNKNOWN = "unknown"                 # Could not classify


class GamePhase(str, Enum):
    """Game phases that accept voice input."""
    BREAKFAST = "breakfast"
    MISSION = "mission"
    SOCIAL = "social"
    ROUNDTABLE = "roundtable"
    TURRET = "turret"
    FINALE = "finale"
    INACTIVE = "inactive"  # Spectating or waiting


@dataclass
class IntentResult:
    """Result of intent classification."""
    type: IntentType
    confidence: float                   # 0.0-1.0
    target: Optional[str] = None        # Target player name if applicable
    evidence: Optional[str] = None      # Supporting reasoning if provided
    raw_text: str = ""                  # Original transcribed text
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_actionable(self) -> bool:
        """Check if this intent requires game action."""
        return self.type in {
            IntentType.ACCUSATION,
            IntentType.VOTE,
            IntentType.VOTE_TO_END,
            IntentType.VOTE_TO_CONTINUE,
        }


@dataclass
class ConversationResponse:
    """Response to be spoken by AI."""
    speaker: str                        # Speaker ID or "narrator"
    text: str                           # Text to speak
    emotion: str = ""                   # Emotion tags for TTS
    allow_interruption: bool = True     # Can human interrupt?
    followup_speakers: List[Dict[str, str]] = field(default_factory=list)
    priority: int = 0                   # Higher = more important
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HITLSession:
    """Tracks state for a human player's HITL session."""
    human_player_id: str
    human_player_name: str
    is_traitor: bool = False
    connected_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    # Conversation context
    recent_statements: List[str] = field(default_factory=list)
    pending_responses: List[ConversationResponse] = field(default_factory=list)

    # Statistics
    statements_made: int = 0
    votes_cast: int = 0
    accusations_made: int = 0

    def record_statement(self, text: str):
        """Record a statement from the human player."""
        self.recent_statements.append(text)
        if len(self.recent_statements) > 10:
            self.recent_statements.pop(0)
        self.statements_made += 1
        self.last_activity = datetime.now()


class IntentClassifier:
    """Classifies human speech into actionable intents.

    Uses pattern matching for common phrases with LLM fallback
    for ambiguous cases.
    """

    # Pattern-based classification (fast path)
    ACCUSATION_PATTERNS = [
        r"i think (\w+) is (?:a )?traitor",
        r"i believe (\w+) is (?:a )?traitor",
        r"i'm suspicious of (\w+)",
        r"(\w+) is definitely (?:a )?traitor",
        r"i don't trust (\w+)",
        r"(\w+) has been acting suspicious",
        r"we should vote for (\w+)",
        r"(\w+) is lying",
    ]

    DEFENSE_PATTERNS = [
        r"i'm not (?:a )?traitor",
        r"i am (?:a )?faithful",
        r"i would never",
        r"that's not true",
        r"i can explain",
        r"you're wrong about me",
        r"i've been loyal",
    ]

    VOTE_PATTERNS = [
        r"i vote (?:for )?(\w+)",
        r"my vote is (?:for )?(\w+)",
        r"i'm voting (?:for )?(\w+)",
        r"(\w+) gets my vote",
    ]

    AGREEMENT_PATTERNS = [
        r"i agree",
        r"you're right",
        r"that makes sense",
        r"i think so too",
        r"absolutely",
        r"exactly",
    ]

    DISAGREEMENT_PATTERNS = [
        r"i disagree",
        r"that's wrong",
        r"i don't think so",
        r"that doesn't make sense",
        r"no way",
        r"that's ridiculous",
    ]

    QUESTION_PATTERNS = [
        r"why did you",
        r"what do you think",
        r"who do you suspect",
        r"can you explain",
        r"where were you",
    ]

    VOTE_TO_END_PATTERNS = [
        r"i vote to end",
        r"let's end (?:the game|it)",
        r"i'm ready to end",
        r"we should end",
    ]

    VOTE_TO_CONTINUE_PATTERNS = [
        r"i vote to continue",
        r"let's continue",
        r"we should keep going",
        r"not yet",
    ]

    def __init__(self, player_names: List[str] = None):
        """Initialize classifier with known player names."""
        self.player_names = [n.lower() for n in (player_names or [])]
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self._patterns = {
            IntentType.ACCUSATION: [
                re.compile(p, re.IGNORECASE) for p in self.ACCUSATION_PATTERNS
            ],
            IntentType.DEFENSE: [
                re.compile(p, re.IGNORECASE) for p in self.DEFENSE_PATTERNS
            ],
            IntentType.VOTE: [
                re.compile(p, re.IGNORECASE) for p in self.VOTE_PATTERNS
            ],
            IntentType.AGREEMENT: [
                re.compile(p, re.IGNORECASE) for p in self.AGREEMENT_PATTERNS
            ],
            IntentType.DISAGREEMENT: [
                re.compile(p, re.IGNORECASE) for p in self.DISAGREEMENT_PATTERNS
            ],
            IntentType.QUESTION: [
                re.compile(p, re.IGNORECASE) for p in self.QUESTION_PATTERNS
            ],
            IntentType.VOTE_TO_END: [
                re.compile(p, re.IGNORECASE) for p in self.VOTE_TO_END_PATTERNS
            ],
            IntentType.VOTE_TO_CONTINUE: [
                re.compile(p, re.IGNORECASE) for p in self.VOTE_TO_CONTINUE_PATTERNS
            ],
        }

    def update_player_names(self, names: List[str]):
        """Update known player names."""
        self.player_names = [n.lower() for n in names]

    def classify(self, text: str) -> IntentResult:
        """Classify text into an intent.

        Args:
            text: Transcribed speech from human player

        Returns:
            IntentResult with classification
        """
        text_lower = text.lower().strip()

        # Try pattern matching first (fast path)
        for intent_type, patterns in self._patterns.items():
            for pattern in patterns:
                match = pattern.search(text_lower)
                if match:
                    target = None
                    if match.groups():
                        potential_target = match.group(1)
                        target = self._resolve_player_name(potential_target)

                    return IntentResult(
                        type=intent_type,
                        confidence=0.85,
                        target=target,
                        raw_text=text,
                    )

        # Check for emotional content
        if self._is_emotional(text_lower):
            return IntentResult(
                type=IntentType.EMOTIONAL,
                confidence=0.7,
                raw_text=text,
            )

        # Default to small talk for conversational content
        if len(text.split()) > 3:
            return IntentResult(
                type=IntentType.SMALL_TALK,
                confidence=0.5,
                raw_text=text,
            )

        return IntentResult(
            type=IntentType.UNKNOWN,
            confidence=0.3,
            raw_text=text,
        )

    def _resolve_player_name(self, text: str) -> Optional[str]:
        """Resolve a name reference to a known player."""
        text_lower = text.lower()

        # Exact match
        for name in self.player_names:
            if name == text_lower:
                return name.title()

        # Partial match (first name)
        for name in self.player_names:
            if text_lower in name or name in text_lower:
                return name.title()

        # Could be unknown player reference
        return text.title() if text else None

    def _is_emotional(self, text: str) -> bool:
        """Check if text is primarily emotional expression."""
        emotional_words = [
            "sad", "angry", "frustrated", "scared", "worried",
            "happy", "relieved", "shocked", "devastated", "furious",
            "can't believe", "oh no", "oh my god", "what",
        ]
        return any(word in text for word in emotional_words)


class HITLVoiceHandler:
    """Handles human voice input and orchestrates AI responses.

    Central hub for HITL mode that connects:
    - Speech recognition (Deepgram)
    - Game engine (phase routing)
    - AI agents (response generation)
    - Speech synthesis (ElevenLabs)
    """

    def __init__(
        self,
        stt_client: Any = None,         # DeepgramClient
        tts_client: Any = None,         # ElevenLabsClient
        game_engine: Any = None,        # GameEngineAsync/HITL
        voice_cache: Any = None,        # VoiceCacheManager
        human_player_id: str = "player_human",
        human_player_name: str = "Human Player",
    ):
        """Initialize HITL voice handler.

        Args:
            stt_client: Deepgram client for speech-to-text
            tts_client: ElevenLabs client for text-to-speech
            game_engine: Game engine instance
            voice_cache: Voice cache for low-latency responses
            human_player_id: ID of the human player
            human_player_name: Display name of human player
        """
        self.stt = stt_client
        self.tts = tts_client
        self.engine = game_engine
        self.voice_cache = voice_cache

        # Session tracking
        self.session = HITLSession(
            human_player_id=human_player_id,
            human_player_name=human_player_name,
        )

        # Intent classification
        self.classifier = IntentClassifier()

        # Response queue
        self._response_queue: asyncio.Queue[ConversationResponse] = asyncio.Queue()

        # State
        self._is_processing = False
        self._current_speaker: Optional[str] = None

        logger.info(f"HITLVoiceHandler initialized for {human_player_name}")

    def set_human_role(self, is_traitor: bool):
        """Set whether the human player is a traitor."""
        self.session.is_traitor = is_traitor
        logger.info(f"Human player role set: {'Traitor' if is_traitor else 'Faithful'}")

    def update_player_names(self, names: List[str]):
        """Update known player names for intent classification."""
        self.classifier.update_player_names(names)

    async def process_voice_input(
        self,
        audio_stream: AsyncIterator[bytes],
    ) -> AsyncIterator[bytes]:
        """Process human voice input and yield AI response audio.

        Main entry point for voice interaction. Takes raw audio stream,
        transcribes it, classifies intent, generates responses, and
        yields synthesized response audio.

        Args:
            audio_stream: Async iterator of audio chunks

        Yields:
            Audio chunks of AI responses
        """
        if self.stt is None:
            raise ValueError("STT client not configured")

        self._is_processing = True

        try:
            # Transcribe incoming audio
            async for transcript in self.stt.transcribe_stream(audio_stream):
                if not transcript.is_final:
                    continue  # Wait for final transcript

                if not transcript.text.strip():
                    continue  # Skip empty transcripts

                logger.debug(f"Human said: {transcript.text}")
                self.session.record_statement(transcript.text)

                # Get current game phase
                phase = self._get_current_phase()

                # Route to appropriate handler
                response = await self._route_to_phase_handler(
                    transcript.text,
                    phase,
                )

                if response:
                    # Generate and yield response audio
                    async for audio_chunk in self._generate_response_audio(response):
                        yield audio_chunk

                    # Handle followup speakers
                    for followup in response.followup_speakers:
                        followup_response = ConversationResponse(
                            speaker=followup.get("speaker", "narrator"),
                            text=followup.get("text", ""),
                            emotion=followup.get("emotion", ""),
                        )
                        async for audio_chunk in self._generate_response_audio(followup_response):
                            yield audio_chunk

        finally:
            self._is_processing = False

    def _get_current_phase(self) -> GamePhase:
        """Get the current game phase."""
        if self.engine is None:
            return GamePhase.INACTIVE

        try:
            phase_str = self.engine.game_state.phase.lower()
            phase_map = {
                "breakfast": GamePhase.BREAKFAST,
                "mission": GamePhase.MISSION,
                "social": GamePhase.SOCIAL,
                "roundtable": GamePhase.ROUNDTABLE,
                "round_table": GamePhase.ROUNDTABLE,
                "turret": GamePhase.TURRET,
                "finale": GamePhase.FINALE,
            }
            return phase_map.get(phase_str, GamePhase.INACTIVE)
        except Exception:
            return GamePhase.INACTIVE

    async def _route_to_phase_handler(
        self,
        text: str,
        phase: GamePhase,
    ) -> Optional[ConversationResponse]:
        """Route human input to appropriate phase handler.

        Args:
            text: Transcribed human speech
            phase: Current game phase

        Returns:
            Response to be spoken, or None
        """
        # Classify intent
        intent = self.classifier.classify(text)
        logger.debug(f"Classified intent: {intent.type} (confidence: {intent.confidence})")

        # Phase-specific routing
        handlers = {
            GamePhase.ROUNDTABLE: self._handle_roundtable_input,
            GamePhase.SOCIAL: self._handle_social_input,
            GamePhase.TURRET: self._handle_turret_input,
            GamePhase.BREAKFAST: self._handle_breakfast_input,
            GamePhase.MISSION: self._handle_mission_input,
            GamePhase.FINALE: self._handle_finale_input,
        }

        handler = handlers.get(phase, self._handle_passive_input)
        return await handler(text, intent)

    async def _handle_roundtable_input(
        self,
        text: str,
        intent: IntentResult,
    ) -> Optional[ConversationResponse]:
        """Handle human input during Round Table phase."""

        if intent.type == IntentType.ACCUSATION:
            return await self._process_accusation(text, intent)

        elif intent.type == IntentType.DEFENSE:
            return await self._process_defense(text, intent)

        elif intent.type == IntentType.VOTE:
            return await self._process_vote(text, intent)

        elif intent.type == IntentType.QUESTION:
            return await self._process_question(text, intent)

        elif intent.type in {IntentType.AGREEMENT, IntentType.DISAGREEMENT}:
            return await self._process_reaction(text, intent)

        else:
            # General statement - generate acknowledgment
            return await self._generate_ai_reaction(text, "general")

    async def _handle_social_input(
        self,
        text: str,
        intent: IntentResult,
    ) -> Optional[ConversationResponse]:
        """Handle human input during Social phase."""

        if intent.type == IntentType.STRATEGIC:
            return await self._process_strategic_talk(text, intent)

        elif intent.type == IntentType.QUESTION:
            return await self._process_question(text, intent)

        else:
            # Social conversation
            return await self._generate_social_response(text)

    async def _handle_turret_input(
        self,
        text: str,
        intent: IntentResult,
    ) -> Optional[ConversationResponse]:
        """Handle human input during Turret phase (traitors only)."""

        if not self.session.is_traitor:
            # Human is not a traitor - they shouldn't be in turret
            return ConversationResponse(
                speaker="narrator",
                text="You rest peacefully, unaware of the dark deeds being plotted.",
                emotion="[whispered]",
                allow_interruption=False,
            )

        # Traitor discussion
        if intent.type == IntentType.VOTE:
            return await self._process_murder_vote(text, intent)

        else:
            return await self._process_traitor_deliberation(text, intent)

    async def _handle_breakfast_input(
        self,
        text: str,
        intent: IntentResult,
    ) -> Optional[ConversationResponse]:
        """Handle human input during Breakfast phase."""

        # Breakfast is mostly reactive - players process the murder
        if intent.type == IntentType.EMOTIONAL:
            return await self._generate_empathy_response(text)

        else:
            return await self._generate_social_response(text)

    async def _handle_mission_input(
        self,
        text: str,
        intent: IntentResult,
    ) -> Optional[ConversationResponse]:
        """Handle human input during Mission phase."""

        # Mission phase - mostly task-focused
        return ConversationResponse(
            speaker="narrator",
            text="Focus on the mission at hand.",
            emotion="[calm]",
            allow_interruption=True,
        )

    async def _handle_finale_input(
        self,
        text: str,
        intent: IntentResult,
    ) -> Optional[ConversationResponse]:
        """Handle human input during Finale phase."""

        if intent.type == IntentType.VOTE_TO_END:
            return await self._process_vote_to_end(text, "end")

        elif intent.type == IntentType.VOTE_TO_CONTINUE:
            return await self._process_vote_to_end(text, "continue")

        else:
            return await self._handle_roundtable_input(text, intent)

    async def _handle_passive_input(
        self,
        text: str,
        intent: IntentResult,
    ) -> Optional[ConversationResponse]:
        """Handle human input during passive/spectating phases."""
        return ConversationResponse(
            speaker="narrator",
            text="Please wait for the next phase to begin.",
            emotion="[calm]",
            allow_interruption=False,
        )

    # === Action Processors ===

    async def _process_accusation(
        self,
        text: str,
        intent: IntentResult,
    ) -> ConversationResponse:
        """Process an accusation from the human player."""
        target = intent.target
        self.session.accusations_made += 1

        if not target:
            return ConversationResponse(
                speaker="narrator",
                text="Who specifically are you accusing?",
                emotion="[curious]",
            )

        # Get the accused agent to generate a defense
        defense = await self._get_agent_defense(target, text)

        # Get reactions from other players
        reactions = await self._get_reactions_to_accusation(target, text)

        return ConversationResponse(
            speaker=target,
            text=defense,
            emotion="[defensive]",
            followup_speakers=reactions[:2],  # Limit to 2 reactions
        )

    async def _process_defense(
        self,
        text: str,
        intent: IntentResult,
    ) -> ConversationResponse:
        """Process a defense statement from the human player."""

        # Generate challenges from AI agents
        challenges = await self._get_challenges_to_defense(text)

        if challenges:
            return ConversationResponse(
                speaker=challenges[0]["speaker"],
                text=challenges[0]["text"],
                emotion="[suspicious]",
                followup_speakers=challenges[1:2],
            )

        return ConversationResponse(
            speaker="narrator",
            text="The room considers your words carefully.",
            emotion="[tense]",
        )

    async def _process_vote(
        self,
        text: str,
        intent: IntentResult,
    ) -> ConversationResponse:
        """Process a vote from the human player."""
        target = intent.target
        self.session.votes_cast += 1

        if not target:
            return ConversationResponse(
                speaker="narrator",
                text="Who are you voting for?",
                emotion="[expectant]",
            )

        # Register vote with game engine
        if self.engine:
            try:
                self.engine.register_vote(
                    self.session.human_player_id,
                    target
                )
            except Exception as e:
                logger.error(f"Failed to register vote: {e}")

        return ConversationResponse(
            speaker="narrator",
            text=f"Your vote for {target} has been recorded.",
            emotion="[formal]",
            allow_interruption=False,
        )

    async def _process_question(
        self,
        text: str,
        intent: IntentResult,
    ) -> ConversationResponse:
        """Process a question from the human player."""

        # Determine who should answer
        target = intent.target or await self._select_best_responder(text)

        if target:
            response = await self._get_agent_response(target, text)
            return ConversationResponse(
                speaker=target,
                text=response,
                emotion="[thoughtful]",
            )

        return ConversationResponse(
            speaker="narrator",
            text="No one seems ready to answer.",
            emotion="[awkward]",
        )

    async def _process_reaction(
        self,
        text: str,
        intent: IntentResult,
    ) -> ConversationResponse:
        """Process agreement/disagreement from the human player."""

        # Generate response from a relevant AI
        response = await self._generate_ai_reaction(
            text,
            "agreement" if intent.type == IntentType.AGREEMENT else "disagreement"
        )

        return response

    async def _process_vote_to_end(
        self,
        text: str,
        vote_type: str,
    ) -> ConversationResponse:
        """Process vote to end/continue during finale."""

        if self.engine:
            try:
                self.engine.register_finale_vote(
                    self.session.human_player_id,
                    vote_type
                )
            except Exception as e:
                logger.error(f"Failed to register finale vote: {e}")

        return ConversationResponse(
            speaker="narrator",
            text=f"You vote to {vote_type} the game.",
            emotion="[dramatic]",
            allow_interruption=False,
        )

    async def _process_murder_vote(
        self,
        text: str,
        intent: IntentResult,
    ) -> ConversationResponse:
        """Process murder target vote during Turret (traitors only)."""
        target = intent.target

        if not target:
            return ConversationResponse(
                speaker="fellow_traitor",
                text="[whispered] Who should we target tonight?",
                emotion="[cold][whispered]",
            )

        return ConversationResponse(
            speaker="fellow_traitor",
            text=f"[whispered] {target}... an interesting choice. They won't see it coming.",
            emotion="[cold][whispered]",
        )

    async def _process_traitor_deliberation(
        self,
        text: str,
        intent: IntentResult,
    ) -> ConversationResponse:
        """Process traitor deliberation during Turret."""

        return ConversationResponse(
            speaker="fellow_traitor",
            text="[whispered] We must be careful. The Faithful are growing suspicious.",
            emotion="[whispered][calculating]",
        )

    async def _process_strategic_talk(
        self,
        text: str,
        intent: IntentResult,
    ) -> ConversationResponse:
        """Process strategic conversation during Social phase."""

        response = await self._generate_social_response(text)
        return response

    # === AI Response Generation ===

    async def _get_agent_defense(
        self,
        target_name: str,
        accusation: str,
    ) -> str:
        """Get defense from an accused AI agent."""
        if self.engine is None:
            return f"I... I don't know what you're talking about."

        try:
            agent = self._find_agent_by_name(target_name)
            if agent and hasattr(agent, 'generate_defense_async'):
                return await agent.generate_defense_async(
                    accusation=accusation,
                    accuser=self.session.human_player_name,
                )
        except Exception as e:
            logger.error(f"Failed to generate defense: {e}")

        # Fallback defense
        return f"That's... that's not fair. I've been loyal this whole time."

    async def _get_agent_response(
        self,
        target_name: str,
        question: str,
    ) -> str:
        """Get response from a specific AI agent."""
        if self.engine is None:
            return "I'm not sure what to say."

        try:
            agent = self._find_agent_by_name(target_name)
            if agent and hasattr(agent, 'generate_response_async'):
                return await agent.generate_response_async(
                    prompt=question,
                    context="question_from_human",
                )
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")

        return "I need to think about that..."

    async def _get_reactions_to_accusation(
        self,
        target_name: str,
        accusation: str,
    ) -> List[Dict[str, str]]:
        """Get reactions from AI agents to an accusation."""
        reactions = []

        if self.engine is None:
            return reactions

        try:
            agents = self._get_alive_agents()
            # Select 2-3 agents to react (excluding target)
            reactors = [
                a for a in agents
                if a.player.name.lower() != target_name.lower()
            ][:3]

            for agent in reactors:
                try:
                    reaction = await agent.generate_reaction_async(
                        event="accusation",
                        target=target_name,
                        context=accusation,
                    )
                    reactions.append({
                        "speaker": agent.player.name,
                        "text": reaction,
                        "emotion": "[thoughtful]",
                    })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Failed to generate reactions: {e}")

        return reactions

    async def _get_challenges_to_defense(
        self,
        defense: str,
    ) -> List[Dict[str, str]]:
        """Get challenges from AI agents to a defense."""
        challenges = []

        if self.engine is None:
            return challenges

        try:
            # Select 1-2 skeptical agents
            agents = self._get_alive_agents()[:2]

            for agent in agents:
                try:
                    challenge = await agent.challenge_defense_async(defense)
                    challenges.append({
                        "speaker": agent.player.name,
                        "text": challenge,
                        "emotion": "[suspicious]",
                    })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Failed to generate challenges: {e}")

        return challenges

    async def _generate_ai_reaction(
        self,
        text: str,
        context: str,
    ) -> ConversationResponse:
        """Generate a general AI reaction to human statement."""

        # Select a random agent to respond
        if self.engine:
            agents = self._get_alive_agents()
            if agents:
                import random
                agent = random.choice(agents)

                try:
                    response = await agent.generate_reaction_async(
                        event=context,
                        context=text,
                    )
                    return ConversationResponse(
                        speaker=agent.player.name,
                        text=response,
                        emotion="[thoughtful]",
                    )
                except Exception:
                    pass

        return ConversationResponse(
            speaker="narrator",
            text="The room falls silent, considering the words spoken.",
            emotion="[tense]",
        )

    async def _generate_social_response(
        self,
        text: str,
    ) -> ConversationResponse:
        """Generate a social conversation response."""

        if self.engine:
            agents = self._get_alive_agents()
            if agents:
                import random
                agent = random.choice(agents)

                return ConversationResponse(
                    speaker=agent.player.name,
                    text="That's an interesting perspective. I've been thinking the same thing.",
                    emotion="[friendly]",
                )

        return ConversationResponse(
            speaker="narrator",
            text="The conversation continues...",
            emotion="[calm]",
        )

    async def _generate_empathy_response(
        self,
        text: str,
    ) -> ConversationResponse:
        """Generate empathetic response to emotional statement."""

        return ConversationResponse(
            speaker="narrator",
            text="A moment of silence hangs in the air. The weight of loss is felt by all.",
            emotion="[somber]",
        )

    async def _select_best_responder(
        self,
        question: str,
    ) -> Optional[str]:
        """Select the best AI agent to respond to a question."""
        if self.engine is None:
            return None

        agents = self._get_alive_agents()
        if agents:
            import random
            return random.choice(agents).player.name

        return None

    # === Audio Generation ===

    async def _generate_response_audio(
        self,
        response: ConversationResponse,
    ) -> AsyncIterator[bytes]:
        """Generate audio for a response.

        Uses voice cache for common phrases, falls back to real-time
        synthesis for unique content.
        """
        if self.tts is None:
            logger.warning("TTS client not configured")
            return

        # Get voice ID for speaker
        voice_id = self._get_voice_for_speaker(response.speaker)

        # Apply emotion tags to text
        text = f"{response.emotion} {response.text}".strip()

        # Try cache first
        if self.voice_cache:
            try:
                cached = await self.voice_cache.get(
                    text=response.text,
                    voice_id=voice_id,
                )
                if cached:
                    yield cached
                    return
            except Exception as e:
                logger.debug(f"Cache miss: {e}")

        # Real-time synthesis
        try:
            # Use streaming for low latency
            async for chunk in self.tts.text_to_speech_stream(
                text=text,
                voice_id=voice_id,
                model="eleven_flash_v2_5",
            ):
                yield chunk
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")

    def _get_voice_for_speaker(self, speaker: str) -> str:
        """Get voice ID for a speaker."""
        if speaker == "narrator":
            return "narrator_alan"  # Default narrator

        if speaker == "fellow_traitor":
            return "traitor_whisper"

        # Look up agent voice
        if self.engine:
            agent = self._find_agent_by_name(speaker)
            if agent and hasattr(agent, 'voice_id'):
                return agent.voice_id

        return "default_voice"

    # === Helpers ===

    def _find_agent_by_name(self, name: str) -> Optional[Any]:
        """Find an agent by name."""
        if self.engine is None:
            return None

        try:
            for agent in self.engine.player_agents:
                if agent.player.name.lower() == name.lower():
                    return agent
        except Exception:
            pass

        return None

    def _get_alive_agents(self) -> List[Any]:
        """Get list of alive AI agents."""
        if self.engine is None:
            return []

        try:
            return [
                a for a in self.engine.player_agents
                if a.player.id != self.session.human_player_id
                and a.player.is_alive
            ]
        except Exception:
            return []


# Convenience factory

def create_hitl_handler(
    stt_client: Any = None,
    tts_client: Any = None,
    game_engine: Any = None,
    voice_cache: Any = None,
    human_player_id: str = "player_human",
    human_player_name: str = "Human Player",
) -> HITLVoiceHandler:
    """Create a configured HITL voice handler.

    Args:
        stt_client: Deepgram client
        tts_client: ElevenLabs client
        game_engine: Game engine instance
        voice_cache: Voice cache manager
        human_player_id: Human player ID
        human_player_name: Human player display name

    Returns:
        Configured HITLVoiceHandler
    """
    return HITLVoiceHandler(
        stt_client=stt_client,
        tts_client=tts_client,
        game_engine=game_engine,
        voice_cache=voice_cache,
        human_player_id=human_player_id,
        human_player_name=human_player_name,
    )
