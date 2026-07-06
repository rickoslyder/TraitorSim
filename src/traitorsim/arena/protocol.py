"""TraitorSim Agent Protocol v1 - Specification and Validation.

Defines the contract between the arena game engine and external AI agents.
Any HTTP-capable agent implementing this protocol can participate in games.

Protocol overview:
    - Agents are HTTP servers that receive requests from the game engine
    - The engine calls agent endpoints when decisions are needed
    - Agents respond with structured JSON matching defined schemas
    - Missing optional endpoints (404/501) trigger personality-based fallbacks
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


# ---------------------------------------------------------------------------
# Protocol version
# ---------------------------------------------------------------------------

class AgentProtocolVersion(str, Enum):
    """Supported protocol versions."""
    V1 = "1.0"


CURRENT_PROTOCOL_VERSION = AgentProtocolVersion.V1

# ---------------------------------------------------------------------------
# Required agent endpoints (agents MUST implement these)
# ---------------------------------------------------------------------------

REQUIRED_ENDPOINTS = [
    ("GET", "/health"),
    ("POST", "/initialize"),
    ("POST", "/vote"),
    ("POST", "/reflect"),
    ("GET", "/get_suspicions"),
]

# Optional endpoints (agents MAY implement; 404 triggers fallback)
OPTIONAL_ENDPOINTS = [
    ("POST", "/choose_murder_victim"),
    ("POST", "/choose_recruit_target"),
    ("POST", "/decide_recruitment"),
    ("POST", "/vote_to_end"),
    ("POST", "/share_or_steal"),
    ("POST", "/choose_seer_target"),
    ("POST", "/seer_result"),
    ("POST", "/create_death_list"),
]


# ---------------------------------------------------------------------------
# Registration schemas
# ---------------------------------------------------------------------------

class AgentRegistration(BaseModel):
    """Schema for agent registration with the arena."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Display name for this agent",
    )
    callback_url: str = Field(
        ...,
        description="Base URL where the agent's HTTP server is accessible (e.g. https://my-agent.example.com)",
    )
    model_info: Optional[str] = Field(
        None,
        max_length=128,
        description="Optional: model identifier (e.g. 'claude-sonnet-4-5', 'gpt-4o', 'grok-3')",
    )
    protocol_version: str = Field(
        default=CURRENT_PROTOCOL_VERSION.value,
        description="Protocol version the agent implements",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata (framework, version, author, etc.)",
    )


class AgentRegistrationResponse(BaseModel):
    """Response returned after successful registration."""

    agent_id: str
    api_key: str  # Bearer token for subsequent API calls
    name: str
    protocol_version: str
    message: str = "Registration successful. Use the api_key as Bearer token for arena API calls."


# ---------------------------------------------------------------------------
# Game state schemas (what agents receive)
# ---------------------------------------------------------------------------

class PlayerView(BaseModel):
    """A player as seen by another agent (role may be hidden)."""

    id: str
    name: str
    alive: bool
    personality: Dict[str, float] = Field(default_factory=dict)
    stats: Dict[str, float] = Field(default_factory=dict)
    archetype_name: Optional[str] = None
    role: Optional[str] = None  # Only present if visible to this agent


class FilteredGameState(BaseModel):
    """Game state filtered for a specific agent's perspective.

    This is what gets sent to agents. Crucially, roles are only visible
    for: the agent's own player, fellow traitors (if traitor), and dead players.
    """

    day: int
    phase: str
    prize_pot: float
    players: List[PlayerView]
    murdered_players: List[str] = Field(default_factory=list)
    banished_players: List[str] = Field(default_factory=list)
    your_player_id: str
    last_murder_victim: Optional[str] = None
    game_id: str = ""
    protocol_version: str = CURRENT_PROTOCOL_VERSION.value


# ---------------------------------------------------------------------------
# Decision request/response schemas
# ---------------------------------------------------------------------------

class AgentDecisionRequest(BaseModel):
    """Generic decision request sent to an agent."""

    game_state: FilteredGameState
    decision_type: str  # "vote", "murder", "recruit", etc.
    eligible_targets: List[str] = Field(
        default_factory=list,
        description="Player IDs that are valid targets for this decision",
    )
    extra: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (e.g. is_ultimatum for recruitment)",
    )
    timeout_seconds: float = 60.0


class AgentDecisionResponse(BaseModel):
    """Generic decision response from an agent."""

    target_player_id: Optional[str] = None
    reasoning: str = ""
    extra: Dict[str, Any] = Field(default_factory=dict)


class VoteResponse(BaseModel):
    """Response for a banishment vote."""

    target_player_id: str
    reasoning: str = ""
    voter_id: Optional[str] = None


class MurderResponse(BaseModel):
    """Response for a murder victim selection."""

    target_player_id: str
    reasoning: str = ""
    traitor_id: Optional[str] = None


class RecruitmentDecisionResponse(BaseModel):
    """Response for a recruitment offer."""

    accepts: bool
    reasoning: str = ""


class VoteToEndResponse(BaseModel):
    """Response for vote-to-end decision."""

    vote: str = Field(..., pattern="^(END|BANISH)$")
    reasoning: str = ""


class ShareOrStealResponse(BaseModel):
    """Response for Traitor's Dilemma."""

    decision: str = Field(..., pattern="^(SHARE|STEAL)$")
    reasoning: str = ""


class SeerTargetResponse(BaseModel):
    """Response for Seer target selection."""

    target_player_id: str
    reasoning: str = ""


class DeathListResponse(BaseModel):
    """Response for Death List creation."""

    death_list: List[str]
    reasoning: str = ""


class SuspicionsResponse(BaseModel):
    """Response for get_suspicions."""

    player_id: str
    suspicions: Dict[str, float] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    """Response for health check."""

    status: str
    agent_name: Optional[str] = None
    protocol_version: Optional[str] = None


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def validate_vote_response(
    response: Dict[str, Any],
    eligible_target_ids: List[str],
) -> Optional[str]:
    """Validate a vote response and return the target player ID, or None if invalid.

    Args:
        response: Raw JSON response from agent
        eligible_target_ids: Valid player IDs that can be voted for

    Returns:
        Valid target player ID, or None if response is invalid
    """
    target = response.get("target_player_id")
    if not target or target not in eligible_target_ids:
        return None
    return target


def validate_murder_response(
    response: Dict[str, Any],
    eligible_target_ids: List[str],
) -> Optional[str]:
    """Validate a murder response and return the target player ID, or None if invalid.

    Args:
        response: Raw JSON response from agent
        eligible_target_ids: Valid player IDs (alive Faithful only)

    Returns:
        Valid target player ID, or None if response is invalid
    """
    target = response.get("target_player_id")
    if not target or target not in eligible_target_ids:
        return None
    return target


def validate_death_list_response(
    response: Dict[str, Any],
    eligible_target_ids: List[str],
    required_count: int,
) -> Optional[List[str]]:
    """Validate a death list response.

    Returns:
        Valid list of player IDs, or None if invalid
    """
    death_list = response.get("death_list", [])
    if not isinstance(death_list, list):
        return None

    # Filter to valid targets
    valid = [pid for pid in death_list if pid in eligible_target_ids]
    if len(valid) < required_count:
        return None

    return valid[:required_count]


def validate_vote_to_end_response(response: Dict[str, Any]) -> Optional[str]:
    """Validate a vote-to-end response. Returns 'END' or 'BANISH', or None."""
    vote = response.get("vote", "").upper()
    if vote in ("END", "BANISH"):
        return vote
    return None


def validate_share_or_steal_response(response: Dict[str, Any]) -> Optional[str]:
    """Validate a share-or-steal response. Returns 'SHARE' or 'STEAL', or None."""
    decision = response.get("decision", "").upper()
    if decision in ("SHARE", "STEAL"):
        return decision
    return None


# ---------------------------------------------------------------------------
# Protocol capability check
# ---------------------------------------------------------------------------

@dataclass
class AgentCapabilities:
    """Discovered capabilities of a remote agent based on endpoint probing."""

    health: bool = False
    initialize: bool = False
    vote: bool = False
    reflect: bool = False
    get_suspicions: bool = False
    choose_murder_victim: bool = False
    choose_recruit_target: bool = False
    decide_recruitment: bool = False
    vote_to_end: bool = False
    share_or_steal: bool = False
    choose_seer_target: bool = False
    seer_result: bool = False
    create_death_list: bool = False

    @property
    def meets_minimum_requirements(self) -> bool:
        """Check if agent implements all required endpoints."""
        return all([
            self.health,
            self.initialize,
            self.vote,
            self.reflect,
            self.get_suspicions,
        ])

    def to_dict(self) -> Dict[str, bool]:
        """Export capabilities as dict."""
        return {
            "health": self.health,
            "initialize": self.initialize,
            "vote": self.vote,
            "reflect": self.reflect,
            "get_suspicions": self.get_suspicions,
            "choose_murder_victim": self.choose_murder_victim,
            "choose_recruit_target": self.choose_recruit_target,
            "decide_recruitment": self.decide_recruitment,
            "vote_to_end": self.vote_to_end,
            "share_or_steal": self.share_or_steal,
            "choose_seer_target": self.choose_seer_target,
            "seer_result": self.seer_result,
            "create_death_list": self.create_death_list,
        }
