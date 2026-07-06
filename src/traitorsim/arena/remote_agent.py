"""Remote Agent Proxy - communicates with external AI agents via HTTP.

Each RemoteAgentProxy wraps a single external agent's callback URL and provides:
- Validated requests with filtered game state (information isolation)
- Configurable timeouts with graceful fallback to random valid actions
- Response validation ensuring agents can't submit invalid moves
- Health monitoring with automatic disconnection detection
- Reasoning capture for spectator display (never shared between agents)
"""

import asyncio
import logging
import random
import time
from typing import Any, Dict, List, Optional

import httpx

from ..core.enums import GamePhase, Role
from ..core.game_state import GameState, Player
from .protocol import (
    AgentCapabilities,
    FilteredGameState,
    PlayerView,
    validate_death_list_response,
    validate_murder_response,
    validate_share_or_steal_response,
    validate_vote_response,
    validate_vote_to_end_response,
)

logger = logging.getLogger(__name__)


class RemoteAgentProxy:
    """Proxy for a remote AI agent participating in an arena game.

    Acts as the interface between the game engine and an external HTTP agent.
    All game state sent to the agent is filtered to prevent information leaks.
    All responses are validated before being accepted.

    Attributes:
        agent_id: Unique arena agent identifier
        callback_url: Base URL of the agent's HTTP server
        player: The Player object this agent controls
        timeout_decision: Seconds to wait for decision responses
        timeout_reflect: Seconds to wait for reflect responses
        timeout_health: Seconds to wait for health checks
        max_consecutive_failures: Failures before marking as disconnected
    """

    def __init__(
        self,
        agent_id: str,
        callback_url: str,
        player: Player,
        *,
        timeout_decision: float = 60.0,
        timeout_reflect: float = 30.0,
        timeout_health: float = 10.0,
        max_consecutive_failures: int = 3,
    ):
        self.agent_id = agent_id
        self.callback_url = callback_url.rstrip("/")
        self.player = player

        self.timeout_decision = timeout_decision
        self.timeout_reflect = timeout_reflect
        self.timeout_health = timeout_health
        self.max_consecutive_failures = max_consecutive_failures

        # State tracking
        self.is_connected = True
        self.consecutive_failures = 0
        self.total_requests = 0
        self.total_failures = 0
        self.total_fallbacks = 0
        self.capabilities = AgentCapabilities()
        self.last_seen: Optional[float] = None

        # Reasoning capture (for spectator display, NEVER shared with other agents)
        self.last_reasoning: Dict[str, str] = {}

    # ------------------------------------------------------------------
    # Game state filtering (information isolation)
    # ------------------------------------------------------------------

    def _filter_game_state(
        self,
        game_state: GameState,
        game_id: str = "",
    ) -> Dict[str, Any]:
        """Create a filtered view of game state for this specific agent.

        Critical security function:
        - Only reveals this agent's own role
        - Reveals fellow traitor identities IF this agent is a traitor
        - Reveals dead players' roles (public knowledge after elimination)
        - Hides all other players' roles

        Args:
            game_state: Full game state from the engine
            game_id: Arena game identifier

        Returns:
            Dict suitable for JSON serialization and sending to the agent
        """
        players_view = []
        for p in game_state.players:
            view = PlayerView(
                id=p.id,
                name=p.name,
                alive=p.alive,
                personality=p.personality,
                stats=p.stats,
                archetype_name=p.archetype_name,
            )

            # Role visibility rules:
            if p.id == self.player.id:
                # Own role: always visible
                view.role = p.role.value
            elif self.player.role == Role.TRAITOR and p.role == Role.TRAITOR:
                # Fellow traitors: visible to traitors
                view.role = p.role.value
            elif not p.alive:
                # Dead players: role revealed publicly
                view.role = p.role.value
            # else: role is None (hidden)

            players_view.append(view)

        filtered = FilteredGameState(
            day=game_state.day,
            phase=game_state.phase.value,
            prize_pot=game_state.prize_pot,
            players=players_view,
            murdered_players=game_state.murdered_players,
            banished_players=game_state.banished_players,
            your_player_id=self.player.id,
            last_murder_victim=game_state.last_murder_victim,
            game_id=game_id,
        )

        return filtered.model_dump()

    # ------------------------------------------------------------------
    # HTTP communication helpers
    # ------------------------------------------------------------------

    async def _post(
        self,
        endpoint: str,
        payload: Dict[str, Any],
        timeout: float,
    ) -> Optional[Dict[str, Any]]:
        """Send a POST request to the agent and return parsed JSON response.

        Returns None on any failure (timeout, connection error, invalid JSON).
        """
        url = f"{self.callback_url}{endpoint}"
        self.total_requests += 1

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(url, json=payload)

                if response.status_code == 404 or response.status_code == 501:
                    # Endpoint not implemented - not a failure, just unsupported
                    logger.debug(f"Agent {self.agent_id}: {endpoint} not implemented (HTTP {response.status_code})")
                    return None

                if response.status_code != 200:
                    logger.warning(
                        f"Agent {self.agent_id}: {endpoint} returned HTTP {response.status_code}"
                    )
                    self._record_failure()
                    return None

                data = response.json()
                self._record_success()
                return data

        except httpx.TimeoutException:
            logger.warning(f"Agent {self.agent_id}: {endpoint} timed out after {timeout}s")
            self._record_failure()
            return None
        except httpx.ConnectError:
            logger.warning(f"Agent {self.agent_id}: connection refused at {url}")
            self._record_failure()
            return None
        except Exception as e:
            logger.error(f"Agent {self.agent_id}: {endpoint} error: {e}")
            self._record_failure()
            return None

    async def _get(
        self,
        endpoint: str,
        timeout: float,
    ) -> Optional[Dict[str, Any]]:
        """Send a GET request to the agent and return parsed JSON response."""
        url = f"{self.callback_url}{endpoint}"
        self.total_requests += 1

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, timeout=timeout)

                if response.status_code == 404 or response.status_code == 501:
                    return None

                if response.status_code != 200:
                    self._record_failure()
                    return None

                data = response.json()
                self._record_success()
                return data

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(f"Agent {self.agent_id}: GET {endpoint} failed: {e}")
            self._record_failure()
            return None
        except Exception as e:
            logger.error(f"Agent {self.agent_id}: GET {endpoint} error: {e}")
            self._record_failure()
            return None

    def _record_success(self) -> None:
        """Record a successful communication."""
        self.consecutive_failures = 0
        self.last_seen = time.time()
        if not self.is_connected:
            logger.info(f"Agent {self.agent_id}: reconnected")
            self.is_connected = True

    def _record_failure(self) -> None:
        """Record a failed communication and check disconnect threshold."""
        self.consecutive_failures += 1
        self.total_failures += 1

        if self.consecutive_failures >= self.max_consecutive_failures:
            if self.is_connected:
                logger.warning(
                    f"Agent {self.agent_id}: marking as disconnected after "
                    f"{self.consecutive_failures} consecutive failures"
                )
                self.is_connected = False

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    async def health_check(self, challenge_nonce: Optional[str] = None) -> bool:
        """Check if the agent is responsive.

        Args:
            challenge_nonce: Optional nonce the agent should echo back

        Returns:
            True if agent is healthy
        """
        data = await self._get("/health", self.timeout_health)
        if data and data.get("status") == "ok":
            self.capabilities.health = True
            return True
        return False

    async def initialize(
        self,
        game_state: GameState,
        game_id: str = "",
    ) -> bool:
        """Initialize the agent with its player configuration.

        Sends the player's identity, role, personality, and stats.
        Fellow traitor identities are included if this agent is a traitor.

        Returns:
            True if initialization succeeded
        """
        payload = {
            "player": {
                "id": self.player.id,
                "name": self.player.name,
                "role": self.player.role.value,
                "alive": self.player.alive,
                "personality": self.player.personality,
                "stats": self.player.stats,
                "archetype_id": self.player.archetype_id,
                "archetype_name": self.player.archetype_name,
                "demographics": self.player.demographics,
                "backstory": self.player.backstory,
                "strategic_profile": self.player.strategic_profile,
            },
            "game_id": game_id,
        }

        # If traitor, include fellow traitor identities
        if self.player.role == Role.TRAITOR:
            fellow_traitors = [
                {"id": p.id, "name": p.name}
                for p in game_state.alive_traitors
                if p.id != self.player.id
            ]
            payload["fellow_traitors"] = fellow_traitors

        data = await self._post("/initialize", payload, self.timeout_decision)
        if data and data.get("status") == "initialized":
            self.capabilities.initialize = True
            return True

        logger.error(f"Agent {self.agent_id}: initialization failed")
        return False

    # ------------------------------------------------------------------
    # Decision endpoints (with validation and fallback)
    # ------------------------------------------------------------------

    async def request_vote(
        self,
        game_state: GameState,
        game_id: str = "",
    ) -> str:
        """Request a banishment vote from the agent.

        Returns:
            Valid target player ID (falls back to random if agent fails)
        """
        eligible = [
            p.id for p in game_state.alive_players
            if p.id != self.player.id
        ]

        if not eligible:
            return self.player.id  # Edge case: only player left

        filtered_state = self._filter_game_state(game_state, game_id)
        payload = {
            "game_state": filtered_state,
            "eligible_targets": eligible,
        }

        data = await self._post("/vote", payload, self.timeout_decision)

        if data:
            target = validate_vote_response(data, eligible)
            if target:
                self.last_reasoning["vote"] = data.get("reasoning", "")
                self.capabilities.vote = True
                return target
            else:
                logger.warning(
                    f"Agent {self.agent_id}: invalid vote target "
                    f"'{data.get('target_player_id')}', falling back to random"
                )

        # Fallback: random vote
        self.total_fallbacks += 1
        self.last_reasoning["vote"] = "(fallback: agent timeout/error)"
        return random.choice(eligible)

    async def request_murder_victim(
        self,
        game_state: GameState,
        death_list: Optional[List[str]] = None,
        game_id: str = "",
    ) -> str:
        """Request a murder victim selection from a Traitor agent.

        Args:
            game_state: Current game state
            death_list: If set, restricts valid targets (Death List mechanic)
            game_id: Arena game identifier

        Returns:
            Valid target player ID (alive Faithful only)
        """
        if death_list:
            eligible = [
                pid for pid in death_list
                if game_state.get_player(pid)
                and game_state.get_player(pid).alive
                and game_state.get_player(pid).role == Role.FAITHFUL
            ]
        else:
            eligible = [p.id for p in game_state.alive_faithful]

        if not eligible:
            # No valid targets (all Faithful eliminated)
            return ""

        filtered_state = self._filter_game_state(game_state, game_id)
        payload = {
            "game_state": filtered_state,
        }
        if death_list:
            payload["death_list"] = death_list

        data = await self._post("/choose_murder_victim", payload, self.timeout_decision)

        if data:
            target = validate_murder_response(data, eligible)
            if target:
                self.last_reasoning["murder"] = data.get("reasoning", "")
                self.capabilities.choose_murder_victim = True
                return target

        # Fallback: random Faithful
        self.total_fallbacks += 1
        self.last_reasoning["murder"] = "(fallback: agent timeout/error)"
        return random.choice(eligible)

    async def request_reflect(
        self,
        game_state: GameState,
        events: List[str],
        game_id: str = "",
    ) -> bool:
        """Ask the agent to reflect on recent events.

        Non-blocking: if the agent fails to reflect, the game continues.

        Returns:
            True if reflection succeeded
        """
        filtered_state = self._filter_game_state(game_state, game_id)
        payload = {
            "game_state": filtered_state,
            "events": events,
        }

        data = await self._post("/reflect", payload, self.timeout_reflect)
        if data and data.get("status") == "completed":
            self.capabilities.reflect = True
            return True

        return False

    async def get_suspicions(self) -> Dict[str, float]:
        """Get the agent's current suspicion scores.

        Returns:
            Dict mapping player_id -> suspicion_score (0.0 to 1.0)
        """
        data = await self._get("/get_suspicions", self.timeout_health)
        if data and "suspicions" in data:
            self.capabilities.get_suspicions = True
            return data["suspicions"]

        return {}

    async def request_recruit_target(
        self,
        game_state: GameState,
        game_id: str = "",
    ) -> Optional[str]:
        """Request a recruitment target from a Traitor agent.

        Returns:
            Target player ID, or None if agent can't/won't recruit
        """
        eligible = [p.id for p in game_state.alive_faithful]
        if not eligible:
            return None

        filtered_state = self._filter_game_state(game_state, game_id)
        payload = {"game_state": filtered_state}

        data = await self._post("/choose_recruit_target", payload, self.timeout_decision)
        if data:
            target = data.get("target_player_id")
            if target in eligible:
                self.last_reasoning["recruit"] = data.get("reasoning", "")
                self.capabilities.choose_recruit_target = True
                return target

        # Fallback: recruit highest social_influence Faithful
        self.total_fallbacks += 1
        faithful = [p for p in game_state.alive_faithful]
        if faithful:
            return max(faithful, key=lambda p: p.stats.get("social_influence", 0.5)).id
        return None

    async def request_recruitment_decision(
        self,
        game_state: GameState,
        is_ultimatum: bool = False,
        game_id: str = "",
    ) -> bool:
        """Ask a Faithful agent whether they accept recruitment.

        Args:
            game_state: Current game state
            is_ultimatum: True if this is a "join or die" scenario

        Returns:
            True if agent accepts recruitment
        """
        filtered_state = self._filter_game_state(game_state, game_id)
        payload = {
            "game_state": filtered_state,
            "is_ultimatum": is_ultimatum,
        }

        data = await self._post("/decide_recruitment", payload, self.timeout_decision)
        if data:
            self.capabilities.decide_recruitment = True
            self.last_reasoning["recruitment"] = data.get("reasoning", "")
            return data.get("accepts", False)

        # Fallback: personality-based (same logic as agent_service.py)
        self.total_fallbacks += 1
        if is_ultimatum:
            return True  # Rational choice: accept ultimatum

        agreeableness = self.player.personality.get("agreeableness", 0.5)
        neuroticism = self.player.personality.get("neuroticism", 0.5)
        return (agreeableness + neuroticism) / 2 > 0.6

    async def request_vote_to_end(
        self,
        game_state: GameState,
        game_id: str = "",
    ) -> str:
        """Ask agent whether to END the game or BANISH again.

        Returns:
            "END" or "BANISH"
        """
        filtered_state = self._filter_game_state(game_state, game_id)
        payload = {"game_state": filtered_state}

        data = await self._post("/vote_to_end", payload, self.timeout_decision)
        if data:
            vote = validate_vote_to_end_response(data)
            if vote:
                self.last_reasoning["vote_to_end"] = data.get("reasoning", "")
                self.capabilities.vote_to_end = True
                return vote

        # Fallback: role-based
        self.total_fallbacks += 1
        if self.player.role == Role.TRAITOR:
            traitor_count = len(game_state.alive_traitors)
            faithful_count = len(game_state.alive_faithful)
            return "END" if traitor_count >= faithful_count else "BANISH"
        else:
            return "BANISH"  # Faithful default: keep hunting

    async def request_share_or_steal(
        self,
        game_state: GameState,
        game_id: str = "",
    ) -> str:
        """Ask a Traitor agent for their Prisoner's Dilemma decision.

        Returns:
            "SHARE" or "STEAL"
        """
        filtered_state = self._filter_game_state(game_state, game_id)
        payload = {"game_state": filtered_state}

        data = await self._post("/share_or_steal", payload, self.timeout_decision)
        if data:
            decision = validate_share_or_steal_response(data)
            if decision:
                self.last_reasoning["share_or_steal"] = data.get("reasoning", "")
                self.capabilities.share_or_steal = True
                return decision

        # Fallback: personality-based
        self.total_fallbacks += 1
        agreeableness = self.player.personality.get("agreeableness", 0.5)
        return "SHARE" if agreeableness > 0.5 else "STEAL"

    async def request_seer_target(
        self,
        game_state: GameState,
        game_id: str = "",
    ) -> Optional[str]:
        """Ask agent to choose a Seer investigation target.

        Returns:
            Target player ID, or None (fallback: most suspicious)
        """
        eligible = [
            p.id for p in game_state.alive_players
            if p.id != self.player.id
        ]
        if not eligible:
            return None

        filtered_state = self._filter_game_state(game_state, game_id)
        payload = {"game_state": filtered_state}

        data = await self._post("/choose_seer_target", payload, self.timeout_decision)
        if data:
            target = data.get("target_player_id")
            if target in eligible:
                self.last_reasoning["seer"] = data.get("reasoning", "")
                self.capabilities.choose_seer_target = True
                return target

        # Fallback: random target
        self.total_fallbacks += 1
        return random.choice(eligible)

    async def notify_seer_result(
        self,
        target_player_id: str,
        true_role: str,
    ) -> bool:
        """Notify agent of Seer investigation result.

        Returns:
            True if agent acknowledged
        """
        payload = {
            "target_player_id": target_player_id,
            "true_role": true_role,
        }

        data = await self._post("/seer_result", payload, self.timeout_reflect)
        if data and data.get("status") == "acknowledged":
            self.capabilities.seer_result = True
            return True
        return False

    async def request_death_list(
        self,
        game_state: GameState,
        num_candidates: int = 3,
        game_id: str = "",
    ) -> List[str]:
        """Request Death List creation from a Traitor agent.

        Returns:
            List of player IDs for the death list
        """
        eligible = [p.id for p in game_state.alive_faithful]
        if not eligible:
            return []

        filtered_state = self._filter_game_state(game_state, game_id)
        payload = {
            "game_state": filtered_state,
            "num_candidates": num_candidates,
        }

        data = await self._post("/create_death_list", payload, self.timeout_decision)
        if data:
            death_list = validate_death_list_response(data, eligible, num_candidates)
            if death_list:
                self.last_reasoning["death_list"] = data.get("reasoning", "")
                self.capabilities.create_death_list = True
                return death_list

        # Fallback: highest social_influence Faithful
        self.total_fallbacks += 1
        sorted_faithful = sorted(
            [p for p in game_state.alive_faithful],
            key=lambda p: p.stats.get("social_influence", 0.5),
            reverse=True,
        )
        return [p.id for p in sorted_faithful[:num_candidates]]

    # ------------------------------------------------------------------
    # Status and diagnostics
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get agent proxy status for monitoring/spectators."""
        return {
            "agent_id": self.agent_id,
            "player_id": self.player.id,
            "player_name": self.player.name,
            "callback_url": self.callback_url,
            "is_connected": self.is_connected,
            "consecutive_failures": self.consecutive_failures,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "total_fallbacks": self.total_fallbacks,
            "last_seen": self.last_seen,
            "capabilities": self.capabilities.to_dict(),
        }
