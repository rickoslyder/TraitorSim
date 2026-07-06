"""Event log + world projection package (API shim v1).

Provides the typed event schema, the JSONL event sink, and the projection
builder behind GET /api/sessions/{session_id}/projection/world.
See API-CONTRACT.md for the external contract.
"""

from .bus import EventBus, default_sessions_dir, generate_session_id
from .projection import (
    build_projection_from_report,
    build_projection_from_state,
    build_world_projection,
    default_reports_dir,
    load_report,
)
from .schemas import (
    PHASE_LOCATION_MAP,
    SCHEMA_VERSION,
    EventType,
    GameEvent,
    PlayerProjection,
    ProjectionPhase,
    WorldProjection,
    location_for_phase,
    normalize_phase,
)

__all__ = [
    "EventBus",
    "EventType",
    "GameEvent",
    "PHASE_LOCATION_MAP",
    "PlayerProjection",
    "ProjectionPhase",
    "SCHEMA_VERSION",
    "WorldProjection",
    "build_projection_from_report",
    "build_projection_from_state",
    "build_world_projection",
    "default_reports_dir",
    "default_sessions_dir",
    "generate_session_id",
    "load_report",
    "location_for_phase",
    "normalize_phase",
]
