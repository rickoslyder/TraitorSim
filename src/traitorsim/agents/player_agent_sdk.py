"""Claude Agent SDK-based player agent for TraitorSim.

This module uses the proper Claude Agent SDK with MCP tools for
autonomous, structured decision-making.

Training Data Integration:
    The agent uses training data extracted from The Traitors UK Season 1
    to provide realistic behavioral patterns:
    - Phase-appropriate behavior guidance
    - Personality-modulated strategy recommendations
    - Emotional reactions based on real player patterns
    - Dialogue suggestions matching context and role

Voice Integration:
    The player agent can optionally emit confessional voice events
    when making decisions (voting, murder selection). This captures
    the agent's private reasoning for episode mode playback.

    Example:
        from traitorsim.voice import create_voice_emitter, VoiceMode

        voice_emitter = create_voice_emitter(mode=VoiceMode.EPISODE)
        agent = PlayerAgentSDK(player, game_state, voice_emitter=voice_emitter)
"""

import asyncio
import os
from contextlib import contextmanager
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from dataclasses import dataclass

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, AssistantMessage

from ..core.game_state import Player, GameState
from ..core.config import GameConfig
from ..memory.memory_manager import MemoryManager
from ..mcp.sdk_tools import create_game_mcp_server

if TYPE_CHECKING:
    from ..voice.voice_emitter import VoiceEmitter
    from ..training import TrainingDataLoader, StrategyAdvisor, BehaviorModulator


# Model provider configuration
#
# IMPORTANT: Anthropic uses CLAUDE_CODE_OAUTH_TOKEN for authentication (not ANTHROPIC_API_KEY)
# Z.AI requires ANTHROPIC_API_KEY to be set with the ZAI_API_KEY value
MODEL_PROVIDER_CONFIG = {
    "anthropic": {
        "base_url": None,  # Use default Anthropic URL
        "auth_env": "CLAUDE_CODE_OAUTH_TOKEN",  # SDK uses OAuth token
        "model_map": {
            # Direct model names - no mapping needed
        },
    },
    "zai": {
        "base_url": "https://api.z.ai/api/anthropic",
        "auth_env": "ZAI_API_KEY",  # Z.AI uses its own API key
        "model_map": {
            # Z.AI GLM models that map to Claude equivalents
            "GLM-4.7": "GLM-4.7",  # Maps to Opus-level
            "GLM-4.5-Air": "GLM-4.5-Air",  # Maps to Haiku-level
            # Also accept Claude model names (Z.AI handles mapping internally)
            "claude-opus-4-5-20251101": "GLM-4.7",
            "claude-sonnet-4-5-20250929": "GLM-4.7",
            "claude-haiku-3-5-20241022": "GLM-4.5-Air",
        },
    },
}

# Default Z.AI API key loaded from environment (for auto-mode fallback)
# Set ZAI_API_KEY_DEFAULT in .env for seamless fallback without per-run config
_DEFAULT_ZAI_API_KEY = os.environ.get("ZAI_API_KEY_DEFAULT", "")


# Lazy load training components
_training_components = None


def _get_training_components():
    """Lazy load training data components."""
    global _training_components

    if _training_components is None:
        try:
            from ..training import (
                TrainingDataLoader,
                StrategyAdvisor,
                BehaviorModulator,
                DialogueGenerator,
            )
            loader = TrainingDataLoader().load()
            _training_components = {
                "loader": loader,
                "advisor": StrategyAdvisor(loader),
                "modulator": BehaviorModulator(loader),
                "dialogue": DialogueGenerator(loader),
            }
        except Exception as e:
            print(f"Warning: Could not load training components: {e}")
            _training_components = {}

    return _training_components


@dataclass
class AgentDecision:
    """Result from an agent decision-making process."""

    action: str  # "vote", "murder", "reflect"
    target: Optional[str] = None  # Player ID for vote/murder
    reasoning: str = ""  # Agent's explanation
    raw_response: Optional[str] = None  # Full SDK response


class PlayerAgentSDK:
    """Claude SDK-powered player agent with MCP tools.

    Uses the Claude Agent SDK properly:
    - MCP tools via create_sdk_mcp_server()
    - query() function for stateless queries
    - Async methods for parallel execution
    - Tool-based decision making (no regex extraction)

    Model Provider Support:
        Supports multiple model providers via configuration:
        - "anthropic": Claude models via Anthropic API (default)
        - "zai": GLM-4.7 via Z.AI API (Claude-compatible drop-in)
        - "auto": Try Anthropic first, fallback to Z.AI on failure

        Set via GameConfig.agent_model_provider or environment variable
        TRAITORSIM_AGENT_PROVIDER.
    """

    def __init__(
        self,
        player: Player,
        game_state: GameState,
        memory_manager: Optional[MemoryManager] = None,
        voice_emitter: Optional["VoiceEmitter"] = None,
        config: Optional[GameConfig] = None,
    ):
        """Initialize player agent with Claude SDK.

        Args:
            player: Player instance this agent controls
            game_state: Current game state (shared reference)
            memory_manager: File-based memory system
            voice_emitter: Optional VoiceEmitter for confessional voice synthesis
            config: Game configuration with model provider settings
        """
        self.player = player
        self.game_state = game_state
        self.memory_manager = memory_manager
        self.voice_emitter = voice_emitter
        self.config = config or GameConfig()

        # Resolve model provider from config or environment
        self._model_provider = self._resolve_model_provider()
        self._current_provider = self._model_provider  # Track active provider for fallback

        # Create tool context (shared with MCP tools via closure)
        self.tool_context = {
            "player_id": player.id,
            "player": player,
            "game_state": game_state,
            "memory_manager": memory_manager,
        }

        # Create MCP server config for this player
        # Note: We'll recreate this for each query to get fresh context
        self.mcp_server = None

    def _resolve_model_provider(self) -> str:
        """Resolve the model provider from config or environment.

        Priority:
        1. TRAITORSIM_AGENT_PROVIDER environment variable
        2. GameConfig.agent_model_provider
        3. Default to "anthropic"

        Returns:
            Model provider string: "anthropic", "zai", or "auto"
        """
        env_provider = os.environ.get("TRAITORSIM_AGENT_PROVIDER", "").lower()
        if env_provider in ("anthropic", "zai", "auto"):
            return env_provider
        return self.config.agent_model_provider

    @contextmanager
    def _model_provider_context(self, provider: str):
        """Context manager to configure environment for a specific model provider.

        For Anthropic: Uses CLAUDE_CODE_OAUTH_TOKEN (no changes needed - SDK default)
        For Z.AI: Sets ANTHROPIC_BASE_URL and ANTHROPIC_API_KEY with Z.AI credentials

        Args:
            provider: Model provider ("anthropic" or "zai")

        Yields:
            The model name to use with this provider
        """
        provider_config = MODEL_PROVIDER_CONFIG.get(provider, MODEL_PROVIDER_CONFIG["anthropic"])

        # Save original environment (only for Z.AI overrides)
        original_base_url = os.environ.get("ANTHROPIC_BASE_URL")
        original_api_key = os.environ.get("ANTHROPIC_API_KEY")

        try:
            if provider == "zai":
                # Z.AI requires ANTHROPIC_BASE_URL and ANTHROPIC_API_KEY
                # (it's a Claude-compatible API endpoint)
                base_url = self.config.zai_base_url or provider_config["base_url"]
                os.environ["ANTHROPIC_BASE_URL"] = base_url

                # Get Z.AI API key from config, environment, or default (for auto-mode fallback)
                api_key = (
                    self.config.zai_api_key
                    or os.environ.get("ZAI_API_KEY")
                    or _DEFAULT_ZAI_API_KEY  # Fallback to default for auto mode
                )
                os.environ["ANTHROPIC_API_KEY"] = api_key

                # Map model name for Z.AI
                model = self.config.agent_model
                model = provider_config["model_map"].get(model, "GLM-4.7")
                yield model

            else:  # anthropic (default)
                # Anthropic uses CLAUDE_CODE_OAUTH_TOKEN automatically
                # Just ensure we're not using Z.AI's base URL
                if "ANTHROPIC_BASE_URL" in os.environ:
                    del os.environ["ANTHROPIC_BASE_URL"]
                # Don't touch ANTHROPIC_API_KEY - SDK uses CLAUDE_CODE_OAUTH_TOKEN

                yield self.config.agent_model

        finally:
            # Restore original environment
            if original_base_url is not None:
                os.environ["ANTHROPIC_BASE_URL"] = original_base_url
            elif "ANTHROPIC_BASE_URL" in os.environ:
                del os.environ["ANTHROPIC_BASE_URL"]

            if original_api_key is not None:
                os.environ["ANTHROPIC_API_KEY"] = original_api_key
            elif provider == "zai" and "ANTHROPIC_API_KEY" in os.environ:
                # Only clean up if we set it for Z.AI
                del os.environ["ANTHROPIC_API_KEY"]

    def _get_system_prompt(self) -> str:
        """Generate system prompt with role, personality, and persona backstory.

        Returns:
            System prompt string with integrated persona context
        """
        role_description = {
            "faithful": "You are a FAITHFUL contestant. Your goal is to identify and banish all Traitors to win the prize pot.",
            "traitor": "You are a TRAITOR. Your goal is to eliminate Faithfuls while avoiding detection. Coordinate murders strategically.",
        }

        personality_desc = "\n".join(
            [
                f"- **{trait.title()}**: {value:.2f} (0.0=low, 1.0=high)"
                for trait, value in self.player.personality.items()
            ]
        )

        stats_desc = "\n".join(
            [
                f"- **{stat.replace('_', ' ').title()}**: {value:.2f}"
                for stat, value in self.player.stats.items()
            ]
        )

        # Build persona context section
        persona_context = ""
        if self.player.backstory:
            persona_context = f"""
**Your Background**:
{self.player.backstory}

**Your Demographics**:
- Age: {self.player.demographics.get('age', 'Unknown')}
- From: {self.player.demographics.get('location', 'UK')}
- Occupation: {self.player.demographics.get('occupation', 'Unknown')}

**What Motivates You**:
{self.player.strategic_profile or 'Win the prize money'}

**How This Affects Your Gameplay**:
- Your {self.player.archetype_name or 'personality'} means you tend toward: {self._get_archetype_gameplay_hint()}
- Your background in {self.player.demographics.get('occupation', 'your field')} gives you {self._get_occupational_advantage()}
- Use language and references appropriate to {self.player.demographics.get('location', 'UK')} when speaking
"""

        return f"""You are **{self.player.name}**, a contestant on "The Traitors" filmed at Ardross Castle in the Scottish Highlands.

**Your Role**: {role_description[self.player.role.value]}
{persona_context}
**Your Personality** (Big Five traits):
{personality_desc}

**Your Stats**:
{stats_desc}

**Important**:
- Use the MCP tools provided to make decisions
- Always call tools - do NOT just state your decision in text
- Roleplay your character authentically based on your background and personality
- Your personality AND life experiences should influence your reasoning and strategy
- High neuroticism = more paranoid; high agreeableness = less confrontational
- High extraversion = more vocal accusations; high openness = consider new theories

**Remember**: You must use tools to take actions. Stating "I vote for X" without calling cast_vote will NOT register your vote."""

    async def _emit_confessional(
        self,
        text: str,
        action: str,
        target: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a confessional voice event (private player thoughts).

        Args:
            text: The player's private reasoning/thoughts
            action: What action this confessional is about (vote, murder, reflection)
            target: Target player ID if applicable
            metadata: Additional context
        """
        if not self.voice_emitter or not text:
            return

        try:
            from ..voice.voice_emitter import VoiceEvent, VoiceEventType, EmotionHint

            # Determine emotion based on role and action
            if self.player.role.value == "traitor":
                emotion = EmotionHint.CONSPIRATORIAL
            elif action == "vote":
                emotion = EmotionHint.SUSPICIOUS
            else:
                emotion = EmotionHint.NEUTRAL

            event = VoiceEvent(
                event_type=VoiceEventType.CONFESSIONAL,
                text=text,
                speaker_id=self.player.id,
                speaker_name=self.player.name,
                emotion=emotion,
                day=self.game_state.day,
                phase="confessional",
                priority=4,  # Medium priority
                metadata={
                    "action": action,
                    "target": target,
                    "role": self.player.role.value,
                    "archetype": self.player.archetype_name,
                    **(metadata or {}),
                },
            )

            await self.voice_emitter.emit(event)

        except Exception as e:
            # Voice emission should never break agent logic
            print(f"Warning: Failed to emit confessional voice: {e}")

    def _get_archetype_gameplay_hint(self) -> str:
        """Get gameplay hint from archetype definition."""
        if not self.player.archetype_id:
            return "strategic and observant play"

        from ..core.archetypes import get_archetype
        archetype = get_archetype(self.player.archetype_id)

        if archetype:
            return archetype.gameplay_tendency
        else:
            return "strategic and observant play"

    def _get_occupational_advantage(self) -> str:
        """Derive gameplay advantage from occupation."""
        occupation = self.player.demographics.get('occupation', '').lower()

        # Map common occupations to advantages
        if any(x in occupation for x in ['nurse', 'doctor', 'therapist', 'counselor']):
            return "strong people-reading skills and empathy"
        elif any(x in occupation for x in ['teacher', 'professor', 'lecturer']):
            return "ability to read group dynamics and influence opinions"
        elif any(x in occupation for x in ['engineer', 'analyst', 'programmer', 'scientist']):
            return "logical pattern recognition and systematic analysis"
        elif any(x in occupation for x in ['police', 'detective', 'investigator']):
            return "interrogation instincts (though possibly overconfident)"
        elif any(x in occupation for x in ['lawyer', 'barrister', 'solicitor']):
            return "argumentative skills and logical persuasion"
        elif any(x in occupation for x in ['actor', 'performer', 'entertainer']):
            return "deception detection and performance skills"
        elif any(x in occupation for x in ['sales', 'marketing', 'business']):
            return "persuasion and reading buying signals"
        elif any(x in occupation for x in ['military', 'soldier', 'officer']):
            return "strategic thinking and discipline (but may be rigid)"
        else:
            return "a unique perspective on human behavior"

    def _get_phase_guidance(self, phase: str) -> str:
        """Get phase-specific behavioral guidance from training data.

        Args:
            phase: Current game phase (breakfast, mission, social, roundtable, turret)

        Returns:
            Phase-specific guidance string
        """
        components = _get_training_components()
        if not components or "modulator" not in components:
            return ""

        try:
            from ..training.training_data_loader import OCEANTraits
            ocean = OCEANTraits.from_dict(self.player.personality)

            modulator = components["modulator"]
            guidance = modulator.get_phase_guidance(
                phase=phase,
                role=self.player.role.value,
                personality=ocean,
                game_context={
                    "day": self.game_state.day,
                    "alive_count": len(list(self.game_state.alive_players)),
                },
            )

            if guidance:
                return f"\n**Phase Guidance for {phase.title()}**:\n{guidance.personality_summary}\n\nExpected behaviors:\n" + \
                       "\n".join(f"- {b}" for b in guidance.expected_behaviors[:3]) + \
                       "\n\nAvoid:\n" + \
                       "\n".join(f"- {b}" for b in guidance.avoid_behaviors[:3])
        except Exception as e:
            pass  # Silently fall back to no guidance

        return ""

    def _get_strategy_recommendation(self, phase: str) -> str:
        """Get strategy recommendation for the current context.

        Args:
            phase: Current game phase

        Returns:
            Strategy recommendation string
        """
        components = _get_training_components()
        if not components or "advisor" not in components:
            return ""

        try:
            from ..training.training_data_loader import OCEANTraits
            ocean = OCEANTraits.from_dict(self.player.personality)

            advisor = components["advisor"]
            recommendations = advisor.get_recommendations(
                role=self.player.role.value,
                phase=phase,
                personality=ocean,
                game_context={
                    "day": self.game_state.day,
                    "alive_count": len(list(self.game_state.alive_players)),
                },
                top_k=2,
            )

            if recommendations:
                rec = recommendations[0]
                return f"\n**Recommended Strategy**: {rec.strategy.name}\n{rec.strategy.description[:150]}...\n\n{rec.example_application}"
        except Exception:
            pass

        return ""

    def _build_options(self, model: Optional[str] = None) -> ClaudeAgentOptions:
        """Build Claude Agent options with MCP server.

        Creates a fresh MCP server with the current tool context.

        Args:
            model: Model name to use (defaults to config.agent_model)

        Returns:
            ClaudeAgentOptions configured for this agent
        """
        # Import here to avoid circular import
        from ..mcp.sdk_tools import create_game_tools_for_player, create_sdk_mcp_server

        # Create tools with shared context
        tools = create_game_tools_for_player(self.tool_context)

        # Create MCP server
        mcp_server = create_sdk_mcp_server(
            name=f"traitorsim_game_{self.player.id}",
            version="1.0.0",
            tools=tools,
        )

        # Use provided model or default from config
        model_name = model or self.config.agent_model

        return ClaudeAgentOptions(
            mcp_servers={"game": mcp_server},
            allowed_tools=[
                "get_game_state",
                "get_my_suspicions",
                "cast_vote",
                "choose_murder_victim",
                "update_suspicion",
                "get_player_info",
            ],
            system_prompt=self._get_system_prompt(),
            model=model_name,
            permission_mode="bypassPermissions",  # Auto-approve tool use (requires non-root)
            max_turns=10,  # Allow tool loops
        )

    async def _query_with_fallback(self, prompt: str) -> Optional[ResultMessage]:
        """Execute a query with automatic fallback to alternate provider.

        Tries the primary provider first. If it fails and fallback is enabled,
        retries with the fallback provider.

        Args:
            prompt: The prompt to send to the model

        Returns:
            The ResultMessage from successful query, or None if all attempts failed
        """
        providers_to_try = []

        if self._model_provider == "auto":
            # Auto mode: try anthropic first, then zai
            providers_to_try = ["anthropic", "zai"]
        elif self._model_provider == "anthropic" and self.config.agent_fallback_enabled:
            # Anthropic with fallback enabled
            providers_to_try = ["anthropic", "zai"]
        elif self._model_provider == "zai" and self.config.agent_fallback_enabled:
            # Z.AI with fallback enabled (fallback to anthropic)
            providers_to_try = ["zai", "anthropic"]
        else:
            # Single provider, no fallback
            providers_to_try = [self._model_provider]

        last_error = None

        for provider in providers_to_try:
            try:
                with self._model_provider_context(provider) as model:
                    self._current_provider = provider
                    options = self._build_options(model=model)

                    async for message in query(prompt=prompt, options=options):
                        if isinstance(message, ResultMessage):
                            return message

                    # If we get here without a ResultMessage, query completed
                    return None

            except Exception as e:
                last_error = e
                provider_name = "Z.AI GLM-4.7" if provider == "zai" else "Anthropic Claude"
                print(f"Warning: {provider_name} failed for {self.player.name}: {e}")

                if provider != providers_to_try[-1]:
                    next_provider = providers_to_try[providers_to_try.index(provider) + 1]
                    next_name = "Z.AI GLM-4.7" if next_provider == "zai" else "Anthropic Claude"
                    print(f"  Falling back to {next_name}...")
                continue

        # All providers failed
        if last_error:
            raise last_error
        return None

    async def cast_vote_async(self) -> Optional[str]:
        """Make Round Table voting decision using MCP tools.

        Returns:
            Player ID of vote target, or None if failed
        """
        # Get training-data-driven guidance
        phase_guidance = self._get_phase_guidance("roundtable")
        strategy_rec = self._get_strategy_recommendation("roundtable")

        prompt = f"""It's Round Table voting time. You must vote to banish someone.

**Steps**:
1. Call `get_game_state` to see who's alive
2. Call `get_my_suspicions` to check your current suspicion scores
3. Call `cast_vote` with your target_player_id and reasoning
{phase_guidance}
{strategy_rec}

Think strategically based on your role and personality. You MUST call the cast_vote tool."""

        try:
            # Clear previous results
            self.tool_context.pop("vote_result", None)

            # Query with automatic fallback support
            await self._query_with_fallback(prompt)

            # Extract vote from shared context (cast_vote tool stored it)
            vote_result = self.tool_context.get("vote_result")

            if vote_result:
                target = vote_result["target"]
                reasoning = vote_result.get("reasoning", "No reasoning provided")

                # Emit confessional voice event with reasoning
                await self._emit_confessional(
                    text=reasoning,
                    action="vote",
                    target=target,
                )

                return target
            else:
                # Fallback: emergency random vote
                print(f"Warning: {self.player.name} didn't call cast_vote tool, using fallback")
                return self._emergency_fallback_vote()

        except Exception as e:
            print(f"Error in cast_vote_async for {self.player.name}: {e}")
            import traceback
            traceback.print_exc()
            return self._emergency_fallback_vote()

    async def choose_murder_victim_async(self) -> Optional[str]:
        """Choose murder victim (Traitors only).

        Returns:
            Player ID of murder victim, or None if failed/not traitor
        """
        if self.player.role.value != "traitor":
            return None

        # Get training-data-driven guidance
        phase_guidance = self._get_phase_guidance("turret")
        strategy_rec = self._get_strategy_recommendation("turret")

        prompt = f"""It's the Turret phase. You must choose a Faithful to murder tonight.

**Steps**:
1. Call `get_game_state` to see alive Faithfuls
2. Call `get_my_suspicions` to see who suspects you
3. Call `choose_murder_victim` with victim_player_id and strategic reasoning
{phase_guidance}
{strategy_rec}

Consider: Who is the biggest threat? Who suspects you? What creates chaos?
You MUST call the choose_murder_victim tool."""

        try:
            # Clear previous results
            self.tool_context.pop("murder_choice", None)

            # Query with automatic fallback support
            await self._query_with_fallback(prompt)

            # Extract murder choice from shared context
            murder_choice = self.tool_context.get("murder_choice")

            if murder_choice:
                victim = murder_choice["victim"]
                reasoning = murder_choice.get("reasoning", "Strategic elimination")

                # Emit confessional voice event with reasoning (Traitor-only)
                await self._emit_confessional(
                    text=reasoning,
                    action="murder",
                    target=victim,
                )

                return victim
            else:
                print(f"Warning: {self.player.name} didn't call choose_murder_victim tool, using fallback")
                return self._emergency_fallback_murder()

        except Exception as e:
            print(f"Error in choose_murder_victim_async for {self.player.name}: {e}")
            import traceback
            traceback.print_exc()
            return self._emergency_fallback_murder()

    async def reflect_on_day_async(self, events: List[str]) -> None:
        """Reflect on day's events and update suspicions.

        Args:
            events: List of event descriptions from the day
        """
        events_text = "\n".join([f"- {event}" for event in events])

        # Get training-data-driven guidance for social reflection
        phase_guidance = self._get_phase_guidance("social")

        prompt = f"""Reflect on today's events and update your suspicions.

**Events**:
{events_text}

**Steps**:
1. Call `get_game_state` to see current situation
2. Call `get_my_suspicions` to see your current scores
3. Analyze events based on your personality
4. Call `update_suspicion` for any players whose suspicion changed
{phase_guidance}

**Key Observation Patterns** (from real Traitors games):
- **Voting Clusters**: Do certain players always vote together?
- **Defense Patterns**: Who rushes to defend whom?
- **Survival Patterns**: Who never gets murdered? (Traitors protect Traitors)
- **Breakfast Tells**: Who enters last but survives night after night?
- **Mission Sabotage**: Unexplained failures may indicate Traitors

Think about:
- Who defended whom?
- Who voted with/against the group?
- If there was a murder, why wasn't X killed? (Are they a traitor?)
- Mission performance patterns

Update suspicions as needed using the update_suspicion tool."""

        try:
            # Query with automatic fallback support
            await self._query_with_fallback(prompt)

            # Reflection complete (updates written to trust matrix via tools)

        except Exception as e:
            print(f"Error in reflect_on_day_async for {self.player.name}: {e}")

    def _emergency_fallback_vote(self) -> Optional[str]:
        """Emergency fallback: Random valid vote target.

        Returns:
            Random alive player ID (not self)
        """
        import random

        valid_targets = [
            p.id for p in self.game_state.alive_players if p.id != self.player.id
        ]
        return random.choice(valid_targets) if valid_targets else None

    def _emergency_fallback_murder(self) -> Optional[str]:
        """Emergency fallback: Random Faithful for murder.

        Returns:
            Random Faithful player ID
        """
        import random

        faithfuls = [p.id for p in self.game_state.alive_faithful]
        return random.choice(faithfuls) if faithfuls else None
