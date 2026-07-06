"""Typed event and world-projection schemas for the TraitorSim API shim (v1).

These models define the stable HTTP contract consumed by TraitorSim3D (Unreal)
and the web dashboard. See API-CONTRACT.md at the repo root for the full
contract documentation.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

SCHEMA_VERSION = "v1"


class EventType(str, Enum):
    """Minimum event vocabulary for the append-only game event log."""

    SESSION_STARTED = "session_started"
    DAY_STARTED = "day_started"
    PHASE_CHANGED = "phase_changed"
    PLAYER_BANISHED = "player_banished"
    PLAYER_MURDERED = "player_murdered"
    VOTE_COMPLETED = "vote_completed"
    GAME_ENDED = "game_ended"


class ProjectionPhase(str, Enum):
    """Normalized phase names exposed to external clients."""

    BREAKFAST = "breakfast"
    MISSION = "mission"
    SOCIAL = "social"
    ROUND_TABLE = "round_table"
    TURRET = "turret"
    ENDED = "ended"


# Phase -> location mapping. Location ids follow the WORLD_BIBLE.md
# "Spatial Graph and Castle Layout" section: canon defines Breakfast Hall
# (not a great hall) and the Traitors' Turret (not a tower). The social
# phase has no canonical room, so `drawing_room` is used by convention.
PHASE_LOCATION_MAP: Dict[str, str] = {
    ProjectionPhase.BREAKFAST.value: "breakfast_hall",
    ProjectionPhase.MISSION.value: "castle_grounds",
    ProjectionPhase.SOCIAL.value: "drawing_room",
    ProjectionPhase.ROUND_TABLE.value: "round_table",
    ProjectionPhase.TURRET.value: "traitors_turret",
    ProjectionPhase.ENDED.value: "round_table",
}

# Raw engine/report phase strings (GamePhase enum values plus historical
# spellings seen in exported reports) -> normalized projection phase.
_RAW_PHASE_ALIASES: Dict[str, str] = {
    "initialization": ProjectionPhase.BREAKFAST.value,
    "breakfast": ProjectionPhase.BREAKFAST.value,
    "mission": ProjectionPhase.MISSION.value,
    "social": ProjectionPhase.SOCIAL.value,
    "round_table": ProjectionPhase.ROUND_TABLE.value,
    "roundtable": ProjectionPhase.ROUND_TABLE.value,
    "turret": ProjectionPhase.TURRET.value,
    "game_ended": ProjectionPhase.ENDED.value,
    "ended": ProjectionPhase.ENDED.value,
}


def normalize_phase(raw: Any) -> ProjectionPhase:
    """Map an engine GamePhase value or raw report string to a ProjectionPhase.

    Unknown values fall back to BREAKFAST (start-of-day) rather than raising,
    so a schema drift in old reports can never 500 the projection endpoint.
    """
    value = getattr(raw, "value", raw)
    if not isinstance(value, str):
        return ProjectionPhase.BREAKFAST
    normalized = _RAW_PHASE_ALIASES.get(value.strip().lower())
    return ProjectionPhase(normalized) if normalized else ProjectionPhase.BREAKFAST


def location_for_phase(phase: ProjectionPhase) -> str:
    """Return the canonical location id for a projection phase."""
    return PHASE_LOCATION_MAP[phase.value]


def utc_now_iso() -> str:
    """ISO-8601 UTC timestamp used on all emitted events."""
    return datetime.now(timezone.utc).isoformat()


class GameEvent(BaseModel):
    """One entry in the append-only event log (data/sessions/{id}/events.jsonl)."""

    session_id: str
    timestamp: str = Field(default_factory=utc_now_iso)
    type: EventType
    day: int
    phase: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class PlayerProjection(BaseModel):
    """Player entry in a WorldProjection.

    v1 is omniscient: `role_visible` carries the true role for every player.
    A POV-filtered variant (hide traitor roles from faithful clients) is a
    documented TODO for v2.
    """

    id: str
    display_name: str
    alive: bool
    seat_index: Optional[int] = None
    role_visible: Optional[str] = None  # "traitor" | "faithful"


class WorldProjection(BaseModel):
    """World-state snapshot served at GET /api/sessions/{id}/projection/world."""

    schema_version: str = SCHEMA_VERSION
    session_id: str
    day: int
    phase: ProjectionPhase
    location_id: str
    players: List[PlayerProjection] = Field(default_factory=list)
    prize_pot: float = 0.0
    alive_count: int = 0
