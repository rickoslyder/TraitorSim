"""Arena Game Engine - extends containerized engine for remote AI agents.

Replaces Docker container HTTP calls with RemoteAgentProxy-mediated
communication to external agents. Supports a mix of remote agents
and local AI backfill agents.

Key differences from GameEngineContainerized:
- Agent URLs are replaced by RemoteAgentProxy instances
- Game state is filtered per-agent (information isolation)
- All responses are validated with fallback to random valid actions
- Timeouts are enforced per-agent with graceful degradation
- Reasoning is captured for spectator display but never shared between agents
"""

import asyncio
import logging
import random
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from ..core.config import GameConfig
from ..core.enums import GamePhase, Role
from ..core.game_state import GameState, Player, TrustMatrix
from ..core.game_engine_containerized import GameEngineContainerized
from .remote_agent import RemoteAgentProxy

logger = logging.getLogger(__name__)


class GameEngineArena(GameEngineContainerized):
    """Game engine for arena mode with remote and local AI agents.

    Extends the containerized engine by replacing direct HTTP calls
    with RemoteAgentProxy instances that handle information filtering,
    validation, timeouts, and fallbacks.

    Attributes:
        remote_agents: Dict mapping player_id -> RemoteAgentProxy
        game_id: Unique arena game identifier
        spectator_events: Events emitted for live spectators
    """

    def __init__(
        self,
        config: Optional[GameConfig] = None,
        game_id: str = "",
    ):
        super().__init__(config)
        self.game_id = game_id
        self.remote_agents: Dict[str, RemoteAgentProxy] = {}
        self.spectator_events: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Agent registration (called before game starts)
    # ------------------------------------------------------------------

    def register_remote_agent(
        self,
        agent_id: str,
        callback_url: str,
        player: Player,
        **proxy_kwargs,
    ) -> RemoteAgentProxy:
        """Register a remote agent for a player slot.

        Args:
            agent_id: Unique arena agent identifier
            callback_url: Agent's HTTP server URL
            player: The Player object this agent will control
            **proxy_kwargs: Additional RemoteAgentProxy options

        Returns:
            The created RemoteAgentProxy
        """
        proxy = RemoteAgentProxy(
            agent_id=agent_id,
            callback_url=callback_url,
            player=player,
            **proxy_kwargs,
        )
        self.remote_agents[player.id] = proxy

        # Also set the agent URL for compatibility with parent class methods
        # that might reference self.agent_urls directly
        self.agent_urls[player.id] = callback_url

        logger.info(
            f"Registered remote agent '{agent_id}' for {player.name} "
            f"at {callback_url}"
        )
        return proxy

    def _is_remote(self, player_id: str) -> bool:
        """Check if a player is controlled by a remote agent."""
        return player_id in self.remote_agents

    def _get_proxy(self, player_id: str) -> Optional[RemoteAgentProxy]:
        """Get the RemoteAgentProxy for a player."""
        return self.remote_agents.get(player_id)

    # ------------------------------------------------------------------
    # Override: Agent initialization
    # ------------------------------------------------------------------

    async def _initialize_agent_containers(self) -> None:
        """Override: Initialize remote agents + local AI backfill.

        Remote agents are initialized via their proxy (with filtered state).
        Non-remote agents use the parent class initialization (Docker containers
        or in-process AI).
        """
        logger.info(f"Initializing arena agents for game {self.game_id}...")
        logger.info(
            f"  Remote agents: {len(self.remote_agents)}, "
            f"  Local agents: {len(self.game_state.players) - len(self.remote_agents)}"
        )

        # Initialize remote agents in parallel
        remote_tasks = []
        for player_id, proxy in self.remote_agents.items():
            # Update proxy's player reference with current game state player
            player = self.game_state.get_player(player_id)
            if player:
                proxy.player = player
                remote_tasks.append(proxy.initialize(self.game_state, self.game_id))

        if remote_tasks:
            results = await asyncio.gather(*remote_tasks, return_exceptions=True)
            for proxy, result in zip(self.remote_agents.values(), results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to initialize remote agent {proxy.agent_id}: {result}")
                elif result:
                    logger.info(f"Initialized remote agent {proxy.agent_id} ({proxy.player.name})")
                else:
                    logger.warning(f"Remote agent {proxy.agent_id} initialization returned False")

        # Initialize non-remote agents via parent class method
        # (only if there are Docker-based agents)
        local_player_ids = [
            p.id for p in self.game_state.players
            if p.id not in self.remote_agents
        ]

        if local_player_ids and any(pid in self.agent_urls for pid in local_player_ids):
            # There are local Docker agents - use parent's initialization for them
            # Note: parent method initializes ALL agents, so we need selective init
            await self._initialize_local_agents(local_player_ids)

    async def _initialize_local_agents(self, player_ids: List[str]) -> None:
        """Initialize local (non-remote) agents via HTTP.

        These are AI backfill agents running as Docker containers or in-process.
        """
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = []
            players = []
            for pid in player_ids:
                player = self.game_state.get_player(pid)
                if not player or pid not in self.agent_urls:
                    continue

                url = self.agent_urls[pid]
                payload = {
                    "player": {
                        "id": player.id,
                        "name": player.name,
                        "role": player.role.value,
                        "alive": player.alive,
                        "personality": player.personality,
                        "stats": player.stats,
                        "archetype_id": player.archetype_id,
                        "archetype_name": player.archetype_name,
                        "demographics": player.demographics,
                        "backstory": player.backstory,
                        "strategic_profile": player.strategic_profile,
                    }
                }
                tasks.append(client.post(f"{url}/initialize", json=payload))
                players.append(player)

            if tasks:
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                for player, response in zip(players, responses):
                    if isinstance(response, Exception):
                        logger.error(f"Failed to initialize local agent {player.name}: {response}")
                    else:
                        logger.info(f"Initialized local agent for {player.name}")

    # ------------------------------------------------------------------
    # Override: Vote collection with information isolation
    # ------------------------------------------------------------------

    async def _collect_votes_parallel_async(self) -> Dict[str, str]:
        """Override: Collect votes using RemoteAgentProxy for remote agents.

        Key difference: each remote agent receives a FILTERED game state
        that only shows information appropriate for that agent.
        """
        alive_players = self.game_state.alive_players
        votes: Dict[str, str] = {}

        # Separate remote and local agents
        remote_tasks = []
        remote_player_ids = []
        local_players = []

        for player in alive_players:
            if self._is_remote(player.id):
                proxy = self._get_proxy(player.id)
                remote_tasks.append(
                    proxy.request_vote(self.game_state, self.game_id)
                )
                remote_player_ids.append(player.id)
            else:
                local_players.append(player)

        # Collect remote votes in parallel
        if remote_tasks:
            remote_results = await asyncio.gather(*remote_tasks, return_exceptions=True)
            for pid, result in zip(remote_player_ids, remote_results):
                if isinstance(result, Exception):
                    logger.error(f"Remote vote error for {pid}: {result}")
                    votes[pid] = self._emergency_vote(pid)
                else:
                    votes[pid] = result

                # Capture reasoning for spectators
                proxy = self._get_proxy(pid)
                if proxy:
                    self._store_reasoning(pid, "vote_result", {
                        "target_player_id": votes[pid],
                        "reasoning": proxy.last_reasoning.get("vote", ""),
                    })

        # Collect local votes via parent's HTTP method
        if local_players:
            game_state_data = self._serialize_game_state()
            import httpx

            async with httpx.AsyncClient(timeout=120.0) as client:
                async def vote_local(player: Player) -> Tuple[str, str, Dict]:
                    try:
                        url = self.agent_urls.get(player.id)
                        if not url:
                            return (player.id, self._emergency_vote(player.id), {})
                        response = await client.post(
                            f"{url}/vote",
                            json={"game_state": game_state_data},
                        )
                        response.raise_for_status()
                        data = response.json()
                        return (player.id, data["target_player_id"], data)
                    except Exception as e:
                        logger.error(f"Local vote error for {player.name}: {e}")
                        return (player.id, self._emergency_vote(player.id), {})

                local_results = await asyncio.gather(
                    *[vote_local(p) for p in local_players]
                )
                for pid, target, data in local_results:
                    votes[pid] = target
                    self._store_reasoning(pid, "vote_result", {
                        "target_player_id": target,
                        "reasoning": data.get("reasoning", ""),
                    })

        return votes

    # ------------------------------------------------------------------
    # Override: Reflection with information isolation
    # ------------------------------------------------------------------

    async def _parallel_reflection_async(self, events: List[str]) -> None:
        """Override: Trigger agent reflection with filtered game state per agent."""
        alive_players = self.game_state.alive_players

        # Remote reflections (each gets filtered state)
        remote_tasks = []
        for player in alive_players:
            if self._is_remote(player.id):
                proxy = self._get_proxy(player.id)
                remote_tasks.append(
                    proxy.request_reflect(self.game_state, events, self.game_id)
                )

        # Local reflections (use parent's unfiltered method)
        local_players = [p for p in alive_players if not self._is_remote(p.id)]

        # Execute in parallel
        all_tasks = []
        if remote_tasks:
            all_tasks.extend(remote_tasks)

        if local_players:
            game_state_data = self._serialize_game_state()
            import httpx

            async def reflect_local(player: Player):
                try:
                    url = self.agent_urls.get(player.id)
                    if not url:
                        return
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        await client.post(
                            f"{url}/reflect",
                            json={"game_state": game_state_data, "events": events},
                        )
                except Exception as e:
                    logger.error(f"Local reflection error for {player.name}: {e}")

            all_tasks.extend([reflect_local(p) for p in local_players])

        if all_tasks:
            await asyncio.gather(*all_tasks, return_exceptions=True)

    # ------------------------------------------------------------------
    # Override: Murder victim selection with information isolation
    # ------------------------------------------------------------------

    async def _choose_murder_victim_http(
        self,
        traitor_id: str,
        death_list: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Override: Use RemoteAgentProxy for remote traitor agents."""
        if self._is_remote(traitor_id):
            proxy = self._get_proxy(traitor_id)
            target = await proxy.request_murder_victim(
                self.game_state, death_list, self.game_id
            )
            if target:
                self._store_reasoning(traitor_id, "murder_result", {
                    "target_player_id": target,
                    "reasoning": proxy.last_reasoning.get("murder", ""),
                })
            return target

        # Fall through to parent's HTTP method for local agents
        return await super()._choose_murder_victim_http(traitor_id, death_list)

    # ------------------------------------------------------------------
    # Override: Recruitment with information isolation
    # ------------------------------------------------------------------

    async def _choose_recruit_target_http(self, traitor_id: str) -> str:
        """Override: Use RemoteAgentProxy for remote traitor agents."""
        if self._is_remote(traitor_id):
            proxy = self._get_proxy(traitor_id)
            target = await proxy.request_recruit_target(self.game_state, self.game_id)
            if target:
                return target
            # Fallback to highest social_influence Faithful
            faithful = self.game_state.alive_faithful
            if faithful:
                return max(faithful, key=lambda p: p.stats.get("social_influence", 0.5)).id
            return ""

        return await super()._choose_recruit_target_http(traitor_id)

    async def _offer_recruitment_http(self, faithful_id: str, is_ultimatum: bool) -> bool:
        """Override: Use RemoteAgentProxy for remote faithful agents."""
        if self._is_remote(faithful_id):
            proxy = self._get_proxy(faithful_id)
            return await proxy.request_recruitment_decision(
                self.game_state, is_ultimatum, self.game_id
            )

        return await super()._offer_recruitment_http(faithful_id, is_ultimatum)

    # ------------------------------------------------------------------
    # Override: Game state serialization (filtered per agent)
    # ------------------------------------------------------------------

    def _serialize_game_state_for_agent(self, player_id: str) -> Dict[str, Any]:
        """Create a filtered game state view for a specific agent.

        This is the core security function for the arena. Each agent
        receives only the information they should have access to.
        """
        proxy = self._get_proxy(player_id)
        if proxy:
            return proxy._filter_game_state(self.game_state, self.game_id)

        # Non-remote agents get the standard (unfiltered) serialization
        # This is safe because local agents are trusted
        return self._serialize_game_state()

    # ------------------------------------------------------------------
    # Spectator event emission
    # ------------------------------------------------------------------

    def _emit_spectator_event(
        self,
        event_type: str,
        data: Dict[str, Any],
        *,
        spoiler: bool = False,
    ) -> None:
        """Emit an event for live spectators.

        Args:
            event_type: Type of spectator event
            data: Event payload
            spoiler: If True, event contains traitor identity info
                     (only shown in omniscient mode)
        """
        event = {
            "type": event_type,
            "game_id": self.game_id,
            "day": self.game_state.day,
            "phase": self.game_state.phase.value if hasattr(self.game_state.phase, "value") else str(self.game_state.phase),
            "data": data,
            "spoiler": spoiler,
        }
        self.spectator_events.append(event)

    # ------------------------------------------------------------------
    # Agent status monitoring
    # ------------------------------------------------------------------

    async def health_check_all_agents(self) -> Dict[str, bool]:
        """Run health checks on all remote agents.

        Returns:
            Dict mapping agent_id -> is_healthy
        """
        results = {}
        tasks = []
        agent_ids = []

        for pid, proxy in self.remote_agents.items():
            tasks.append(proxy.health_check())
            agent_ids.append(proxy.agent_id)

        if tasks:
            health_results = await asyncio.gather(*tasks, return_exceptions=True)
            for aid, result in zip(agent_ids, health_results):
                if isinstance(result, Exception):
                    results[aid] = False
                else:
                    results[aid] = result

        return results

    def get_arena_status(self) -> Dict[str, Any]:
        """Get overall arena game status for monitoring."""
        return {
            "game_id": self.game_id,
            "day": self.game_state.day,
            "phase": self.game_state.phase.value if hasattr(self.game_state.phase, "value") else str(self.game_state.phase),
            "alive_count": len(self.game_state.alive_players),
            "remote_agents": {
                pid: proxy.get_status()
                for pid, proxy in self.remote_agents.items()
            },
            "total_spectator_events": len(self.spectator_events),
        }
