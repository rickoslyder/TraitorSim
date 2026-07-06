"""Append-only JSONL event sink for game sessions.

Events are persisted under ``data/sessions/{session_id}/events.jsonl`` and the
latest world snapshot under ``data/sessions/{session_id}/world_snapshot.json``.
The bus is intentionally dumb: no game logic, no in-memory subscribers — just
durable, replayable persistence for the projection endpoint.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .schemas import EventType, GameEvent, WorldProjection

logger = logging.getLogger(__name__)

EVENTS_FILENAME = "events.jsonl"
SNAPSHOT_FILENAME = "world_snapshot.json"


def default_sessions_dir() -> Path:
    """Resolve the sessions directory.

    Honors TRAITORSIM_SESSIONS_DIR, falling back to <repo_root>/data/sessions
    (this file lives at src/traitorsim/events/bus.py, three levels below root).
    """
    env = os.environ.get("TRAITORSIM_SESSIONS_DIR")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[3] / "data" / "sessions"


def generate_session_id() -> str:
    """Session ids match the report filename convention: game_YYYYMMDD_HHMMSS."""
    return datetime.now().strftime("game_%Y%m%d_%H%M%S")


class EventBus:
    """Emit typed GameEvents to an append-only JSONL log for one session."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        base_dir: Optional[Union[str, Path]] = None,
    ):
        self.session_id = session_id or generate_session_id()
        self.base_dir = Path(base_dir) if base_dir else default_sessions_dir()
        self.session_dir = self.base_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.events_path = self.session_dir / EVENTS_FILENAME
        self.snapshot_path = self.session_dir / SNAPSHOT_FILENAME

    def emit(
        self,
        event_type: Union[EventType, str],
        day: int,
        phase: Any,
        payload: Optional[Dict[str, Any]] = None,
    ) -> GameEvent:
        """Append one event to events.jsonl and return it.

        `phase` accepts a GamePhase enum member or a raw string.
        """
        event = GameEvent(
            session_id=self.session_id,
            type=EventType(event_type),
            day=day,
            phase=str(getattr(phase, "value", phase)),
            payload=payload or {},
        )
        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")
        return event

    def write_snapshot(self, projection: WorldProjection) -> None:
        """Persist the latest world snapshot (atomic via temp file + rename)."""
        tmp_path = self.snapshot_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(projection.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(self.snapshot_path)

    @staticmethod
    def read_events(session_dir: Union[str, Path]) -> List[GameEvent]:
        """Load all events for a session directory; skips malformed lines."""
        events_path = Path(session_dir) / EVENTS_FILENAME
        events: List[GameEvent] = []
        if not events_path.exists():
            return events
        with open(events_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(GameEvent.model_validate_json(line))
                except Exception as exc:  # malformed line must not kill replay
                    logger.warning("Skipping malformed event line: %s", exc)
        return events
