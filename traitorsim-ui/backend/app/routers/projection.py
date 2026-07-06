"""Projection router - World-state projection for UE/dashboard clients.

Serves GET /api/sessions/{session_id}/projection/world (see API-CONTRACT.md
at the repo root). A session_id is the report filename stem for completed
games (e.g. game_20260104_012251) or the live session id for running games.

Schemas and the projection builder live in src/traitorsim/events/ (core
package). Like lobby.py, the core import is resolved lazily so the backend
still boots in environments where the core package is not on the path.
"""

import logging
import os
import re
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()

# Session ids are filename stems; reject anything that could traverse paths.
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_\-]+$")

# Candidate project roots, mirroring runner.py: Docker mount, local dev,
# and the repo root relative to this file (traitorsim-ui/backend/app/routers/).
def _project_root_candidates():
    """Roots that may contain src/traitorsim/events (lazy — safe in /app image)."""
    roots = [
        Path("/app/traitorsim"),
        Path("/home/rkb/projects/TraitorSim"),
    ]
    try:
        roots.append(Path(__file__).resolve().parents[4])
    except IndexError:
        pass
    return roots


def _import_projection_builder():
    """Import build_world_projection from the core package, extending
    sys.path with the project root if needed."""
    try:
        from src.traitorsim.events.projection import build_world_projection
        return build_world_projection
    except ImportError:
        pass

    for root in _project_root_candidates():
        if (root / "src" / "traitorsim" / "events").is_dir():
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            break

    from src.traitorsim.events.projection import build_world_projection
    return build_world_projection


def _resolve_data_dirs() -> tuple:
    """Resolve (reports_dir, sessions_dir) from the environment.

    REPORTS_DIR matches the existing games router convention. SESSIONS_DIR
    defaults to the data/sessions sibling of the project root when unset.
    """
    reports_dir = Path(os.environ.get("REPORTS_DIR", "/app/reports"))

    sessions_env = os.environ.get("SESSIONS_DIR")
    if sessions_env:
        sessions_dir = Path(sessions_env)
    else:
        sessions_dir = None
        for root in _project_root_candidates():
            candidate = root / "data" / "sessions"
            if candidate.is_dir():
                sessions_dir = candidate
                break
        if sessions_dir is None:
            sessions_dir = Path("/app/data/sessions")

    return reports_dir, sessions_dir


@router.get("/{session_id}/projection/world")
async def get_world_projection(session_id: str):
    """Return the WorldProjection (v1) for a session.

    Resolution order: live world_snapshot.json under data/sessions/, then
    the completed report JSON under the reports directory. 404 if neither
    exists.
    """
    if not SESSION_ID_PATTERN.match(session_id):
        raise HTTPException(status_code=404, detail=f"Unknown session: {session_id}")

    try:
        build_world_projection = _import_projection_builder()
    except ImportError as exc:
        logger.error("Core events package unavailable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Projection service unavailable: core package not importable",
        )

    reports_dir, sessions_dir = _resolve_data_dirs()
    projection = build_world_projection(
        session_id, reports_dir=reports_dir, sessions_dir=sessions_dir
    )
    if projection is None:
        raise HTTPException(status_code=404, detail=f"Unknown session: {session_id}")

    return projection.model_dump(mode="json")
