"""Tests for the event log + world projection API shim (v1).

Covers: schema round-trips, phase normalization and location mapping,
the JSONL EventBus, projection built from report JSON and live GameState,
and the FastAPI projection endpoint.
"""

import importlib.util
import json
from pathlib import Path

import pytest

from src.traitorsim.core.enums import GamePhase
from src.traitorsim.events import (
    PHASE_LOCATION_MAP,
    EventBus,
    EventType,
    GameEvent,
    ProjectionPhase,
    WorldProjection,
    build_projection_from_report,
    build_projection_from_state,
    build_world_projection,
    normalize_phase,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def report_players_dict():
    """Report fixture matching the real export shape (players keyed by id)."""
    return {
        "name": "Test Season",
        "total_days": 5,
        "prize_pot": 65000.0,
        "winner": "faithful",
        "rule_variant": "uk",
        "players": {
            "player_00": {
                "id": "player_00",
                "name": "Alice",
                "role": "traitor",
                "alive": False,
            },
            "player_01": {
                "id": "player_01",
                "name": "Bob",
                "role": "faithful",
                "alive": True,
            },
            "player_02": {
                "id": "player_02",
                "name": "Cara",
                "role": "faithful",
                "alive": True,
            },
        },
        "events": [
            {"type": "MISSION_COMPLETE", "day": 5, "phase": "mission"},
        ],
    }


# =============================================================================
# Schema round-trips
# =============================================================================

def test_game_event_round_trip():
    event = GameEvent(
        session_id="game_20260101_120000",
        type=EventType.PHASE_CHANGED,
        day=3,
        phase="round_table",
        payload={"phase": "round_table"},
    )
    restored = GameEvent.model_validate_json(event.model_dump_json())
    assert restored == event
    assert restored.type == EventType.PHASE_CHANGED
    assert restored.timestamp  # auto-populated


def test_world_projection_round_trip():
    projection = WorldProjection(
        session_id="game_20260101_120000",
        day=2,
        phase=ProjectionPhase.TURRET,
        location_id="traitors_turret",
        players=[
            {"id": "player_00", "display_name": "Alice", "alive": True,
             "seat_index": 0, "role_visible": "traitor"},
        ],
        prize_pot=20000.0,
        alive_count=1,
    )
    dumped = projection.model_dump(mode="json")
    assert dumped["schema_version"] == "v1"
    assert dumped["phase"] == "turret"
    restored = WorldProjection.model_validate(dumped)
    assert restored == projection


# =============================================================================
# Phase normalization and location map
# =============================================================================

def test_normalize_phase_from_engine_enum():
    assert normalize_phase(GamePhase.ROUNDTABLE) == ProjectionPhase.ROUND_TABLE
    assert normalize_phase(GamePhase.ENDED) == ProjectionPhase.ENDED
    assert normalize_phase(GamePhase.INIT) == ProjectionPhase.BREAKFAST
    assert normalize_phase(GamePhase.TURRET) == ProjectionPhase.TURRET


def test_normalize_phase_from_strings():
    assert normalize_phase("round_table") == ProjectionPhase.ROUND_TABLE
    assert normalize_phase("roundtable") == ProjectionPhase.ROUND_TABLE
    assert normalize_phase("game_ended") == ProjectionPhase.ENDED
    # Unknown/garbage values must not raise
    assert normalize_phase("???") == ProjectionPhase.BREAKFAST
    assert normalize_phase(None) == ProjectionPhase.BREAKFAST


def test_every_projection_phase_has_a_location():
    for phase in ProjectionPhase:
        assert phase.value in PHASE_LOCATION_MAP
    assert PHASE_LOCATION_MAP["round_table"] == "round_table"
    assert PHASE_LOCATION_MAP["turret"] == "traitors_turret"
    assert PHASE_LOCATION_MAP["breakfast"] == "breakfast_hall"


# =============================================================================
# EventBus (JSONL sink)
# =============================================================================

def test_event_bus_appends_jsonl(tmp_path):
    bus = EventBus(session_id="game_test_0001", base_dir=tmp_path)
    bus.emit(EventType.SESSION_STARTED, day=1, phase=GamePhase.INIT)
    bus.emit(EventType.PHASE_CHANGED, day=1, phase=GamePhase.MISSION,
             payload={"phase": "mission"})

    events_path = tmp_path / "game_test_0001" / "events.jsonl"
    lines = events_path.read_text().strip().splitlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["session_id"] == "game_test_0001"
    assert first["type"] == "session_started"
    assert first["phase"] == "initialization"

    replayed = EventBus.read_events(tmp_path / "game_test_0001")
    assert [e.type for e in replayed] == [
        EventType.SESSION_STARTED, EventType.PHASE_CHANGED,
    ]


def test_event_bus_read_skips_malformed_lines(tmp_path):
    bus = EventBus(session_id="game_test_0002", base_dir=tmp_path)
    bus.emit(EventType.DAY_STARTED, day=2, phase="breakfast")
    with open(bus.events_path, "a") as f:
        f.write("not json\n")
    bus.emit(EventType.PHASE_CHANGED, day=2, phase="mission")

    replayed = EventBus.read_events(bus.session_dir)
    assert len(replayed) == 2


# =============================================================================
# Projection builders
# =============================================================================

def test_projection_from_report_players_dict(report_players_dict):
    projection = build_projection_from_report(report_players_dict, "game_test_report")
    assert projection.session_id == "game_test_report"
    assert projection.day == 5
    assert projection.phase == ProjectionPhase.ENDED  # winner present, no phase key
    assert projection.location_id == "round_table"
    assert projection.prize_pot == 65000.0
    assert projection.alive_count == 2
    assert len(projection.players) == 3

    alice = projection.players[0]
    assert alice.id == "player_00"
    assert alice.display_name == "Alice"
    assert alice.alive is False
    assert alice.seat_index == 0
    assert alice.role_visible == "traitor"  # omniscient v1


def test_projection_from_report_players_list(report_players_dict):
    report = dict(report_players_dict)
    report["players"] = list(report_players_dict["players"].values())
    report["phase"] = "turret"
    projection = build_projection_from_report(report, "game_test_list")
    assert projection.phase == ProjectionPhase.TURRET
    assert projection.location_id == "traitors_turret"
    assert [p.id for p in projection.players] == [
        "player_00", "player_01", "player_02",
    ]


def test_projection_from_report_falls_back_to_last_event_phase(report_players_dict):
    report = dict(report_players_dict)
    report["winner"] = None
    projection = build_projection_from_report(report, "game_test_unfinished")
    assert projection.phase == ProjectionPhase.MISSION
    assert projection.location_id == "castle_grounds"


def test_projection_from_live_game_state(game_state):
    game_state.phase = GamePhase.ROUNDTABLE
    game_state.day = 4
    game_state.prize_pot = 30000.0
    game_state.players[0].alive = False

    projection = build_projection_from_state(game_state, "game_live_001")
    assert projection.phase == ProjectionPhase.ROUND_TABLE
    assert projection.location_id == "round_table"
    assert projection.day == 4
    assert projection.prize_pot == 30000.0
    assert len(projection.players) == len(game_state.players)
    assert projection.alive_count == len(game_state.players) - 1
    assert projection.players[0].alive is False
    assert projection.players[0].role_visible in ("traitor", "faithful")


# =============================================================================
# build_world_projection resolution order
# =============================================================================

def test_build_world_projection_prefers_snapshot(tmp_path, report_players_dict, game_state):
    sessions_dir = tmp_path / "sessions"
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    session_id = "game_both_sources"

    # Report says ended...
    (reports_dir / f"{session_id}.json").write_text(json.dumps(report_players_dict))
    # ...but the live snapshot says turret. Snapshot must win.
    game_state.phase = GamePhase.TURRET
    bus = EventBus(session_id=session_id, base_dir=sessions_dir)
    bus.write_snapshot(build_projection_from_state(game_state, session_id))

    projection = build_world_projection(
        session_id, reports_dir=reports_dir, sessions_dir=sessions_dir
    )
    assert projection is not None
    assert projection.phase == ProjectionPhase.TURRET


def test_build_world_projection_from_report_only(tmp_path, report_players_dict):
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    session_id = "game_report_only"
    (reports_dir / f"{session_id}.json").write_text(json.dumps(report_players_dict))

    projection = build_world_projection(
        session_id, reports_dir=reports_dir, sessions_dir=tmp_path / "sessions"
    )
    assert projection is not None
    assert projection.phase == ProjectionPhase.ENDED


def test_build_world_projection_unknown_session(tmp_path):
    assert build_world_projection(
        "game_does_not_exist",
        reports_dir=tmp_path / "reports",
        sessions_dir=tmp_path / "sessions",
    ) is None


# =============================================================================
# FastAPI endpoint (loads the backend router standalone)
# =============================================================================

def _load_projection_router_module():
    router_path = (
        REPO_ROOT / "traitorsim-ui" / "backend" / "app" / "routers" / "projection.py"
    )
    spec = importlib.util.spec_from_file_location("projection_router", router_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def api_client(tmp_path, monkeypatch, report_players_dict):
    fastapi = pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "game_api_test.json").write_text(json.dumps(report_players_dict))
    monkeypatch.setenv("REPORTS_DIR", str(reports_dir))
    monkeypatch.setenv("SESSIONS_DIR", str(tmp_path / "sessions"))

    module = _load_projection_router_module()
    app = fastapi.FastAPI()
    app.include_router(module.router, prefix="/api/sessions")
    return TestClient(app)


def test_projection_endpoint_returns_world_projection(api_client):
    response = api_client.get("/api/sessions/game_api_test/projection/world")
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "v1"
    assert body["session_id"] == "game_api_test"
    assert body["phase"] == "ended"
    assert body["location_id"] == "round_table"
    assert body["prize_pot"] == 65000.0
    assert body["alive_count"] == 2
    assert {p["id"] for p in body["players"]} == {
        "player_00", "player_01", "player_02",
    }
    assert all("role_visible" in p for p in body["players"])


def test_projection_endpoint_404_for_unknown_session(api_client):
    response = api_client.get("/api/sessions/game_missing/projection/world")
    assert response.status_code == 404


def test_projection_endpoint_rejects_path_traversal_ids(api_client):
    response = api_client.get("/api/sessions/a..b/projection/world")
    assert response.status_code == 404
