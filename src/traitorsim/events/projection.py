"""Build WorldProjection snapshots from live game state or exported reports.

Resolution order for ``build_world_projection``:
1. Live/last snapshot: data/sessions/{session_id}/world_snapshot.json
   (written by EventBus during a running or completed game).
2. Completed report: {reports_dir}/{session_id}.json (the report filename
   stem IS the session_id — same convention the UI database uses).
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .bus import SNAPSHOT_FILENAME, default_sessions_dir
from .schemas import (
    PlayerProjection,
    ProjectionPhase,
    WorldProjection,
    location_for_phase,
    normalize_phase,
)

logger = logging.getLogger(__name__)


def default_reports_dir() -> Path:
    """Resolve the reports directory.

    Honors TRAITORSIM_REPORTS_DIR then REPORTS_DIR, falling back to
    <repo_root>/data/reports (where the engines actually write reports;
    the top-level reports/ dir is a legacy stub).
    """
    env = os.environ.get("TRAITORSIM_REPORTS_DIR") or os.environ.get("REPORTS_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "data" / "reports"


def _player_projections(raw_players: Any) -> List[PlayerProjection]:
    """Normalize a report's players (dict keyed by id, or list) to projections.

    Report schemas have drifted across engine versions, so every field access
    is defensive. seat_index is the stable iteration order (insertion order
    for dicts, list order for lists).
    """
    if isinstance(raw_players, dict):
        entries = [dict(p, id=p.get("id", pid)) for pid, p in raw_players.items()]
    elif isinstance(raw_players, list):
        entries = list(raw_players)
    else:
        return []

    projections = []
    for seat, p in enumerate(entries):
        if not isinstance(p, dict):
            continue
        role = p.get("role")
        projections.append(
            PlayerProjection(
                id=str(p.get("id", f"player_{seat:02d}")),
                display_name=str(p.get("name", p.get("id", f"Player {seat + 1}"))),
                alive=bool(p.get("alive", True)),
                seat_index=seat,
                role_visible=str(role).lower() if role else None,
            )
        )
    return projections


def build_projection_from_state(game_state: Any, session_id: str) -> WorldProjection:
    """Project a live GameState (duck-typed; no core imports to avoid cycles)."""
    phase = normalize_phase(getattr(game_state, "phase", None))
    players = [
        PlayerProjection(
            id=player.id,
            display_name=player.name,
            alive=bool(player.alive),
            seat_index=seat,
            role_visible=getattr(getattr(player, "role", None), "value", None),
        )
        for seat, player in enumerate(getattr(game_state, "players", []))
    ]
    return WorldProjection(
        session_id=session_id,
        day=int(getattr(game_state, "day", 1)),
        phase=phase,
        location_id=location_for_phase(phase),
        players=players,
        prize_pot=float(getattr(game_state, "prize_pot", 0.0)),
        alive_count=sum(1 for p in players if p.alive),
    )


def build_projection_from_report(
    report: Dict[str, Any], session_id: str
) -> WorldProjection:
    """Project an exported report JSON (a completed game)."""
    raw_phase = report.get("phase")
    if raw_phase is not None:
        phase = normalize_phase(raw_phase)
    elif report.get("winner"):
        phase = ProjectionPhase.ENDED
    else:
        # No explicit phase and no winner: fall back to the last event's phase.
        events = report.get("events") or []
        last_phase = events[-1].get("phase") if events and isinstance(events[-1], dict) else None
        phase = normalize_phase(last_phase) if last_phase else ProjectionPhase.ENDED

    players = _player_projections(report.get("players"))
    day = report.get("day") or report.get("total_days") or 1
    return WorldProjection(
        session_id=session_id,
        day=int(day),
        phase=phase,
        location_id=location_for_phase(phase),
        players=players,
        prize_pot=float(report.get("prize_pot") or 0.0),
        alive_count=sum(1 for p in players if p.alive),
    )


def load_report(
    session_id: str, reports_dir: Optional[Union[str, Path]] = None
) -> Optional[Dict[str, Any]]:
    """Load {reports_dir}/{session_id}.json, or None if absent/unreadable."""
    reports_dir = Path(reports_dir) if reports_dir else default_reports_dir()
    report_path = reports_dir / f"{session_id}.json"
    if not report_path.is_file():
        return None
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load report %s: %s", report_path, exc)
        return None


def _load_snapshot(
    session_id: str, sessions_dir: Optional[Union[str, Path]] = None
) -> Optional[WorldProjection]:
    sessions_dir = Path(sessions_dir) if sessions_dir else default_sessions_dir()
    snapshot_path = sessions_dir / session_id / SNAPSHOT_FILENAME
    if not snapshot_path.is_file():
        return None
    try:
        with open(snapshot_path, "r", encoding="utf-8") as f:
            return WorldProjection.model_validate(json.load(f))
    except Exception as exc:
        logger.warning("Failed to load snapshot %s: %s", snapshot_path, exc)
        return None


def build_world_projection(
    session_id: str,
    reports_dir: Optional[Union[str, Path]] = None,
    sessions_dir: Optional[Union[str, Path]] = None,
) -> Optional[WorldProjection]:
    """Resolve a WorldProjection for a session, or None if unknown.

    Prefers the live snapshot (fresh for running games), then falls back to
    the completed report JSON.
    """
    snapshot = _load_snapshot(session_id, sessions_dir)
    if snapshot is not None:
        return snapshot

    report = load_report(session_id, reports_dir)
    if report is not None:
        return build_projection_from_report(report, session_id)

    return None
