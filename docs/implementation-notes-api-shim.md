# Implementation Notes — Event Log + World Projection API Shim (v1)

Date: 2026-07-06. Companion to [API-CONTRACT.md](../API-CONTRACT.md).

## Unknowns pass (map-vs-territory gaps found, and the defaults chosen)

1. **Reports are written to `data/reports/`, not `reports/`** — and only by
   `game_engine_containerized.py::save_game_report()`. The top-level
   `reports/` dir is a stub with a `.gitkeep`. → Projection loads from
   `data/reports/` (overridable via `REPORTS_DIR`).
2. **`GameEngineAsync` had zero structured event emission and zero report
   persistence** — only text logs. `GameState.add_event()` exists but is only
   called by the containerized engine. → The new EventBus is the first
   structured trail for async-engine games.
3. **No session_id concept existed anywhere** (voice `session_id` is
   unrelated). → session_id = report filename stem (`game_YYYYMMDD_HHMMSS`),
   matching the UI DB's `game_id` derivation (`json_path.stem` in
   `backend/app/db/database.py`). Live runs generate the same format.
4. **Phase enum mismatch**: `GamePhase.ENDED = "game_ended"`,
   `ROUNDTABLE = "round_table"`, plus an `INIT = "initialization"` value the
   contract doesn't expose. → Normalization layer in
   `src/traitorsim/events/schemas.py` (`normalize_phase`); unknown values
   degrade to `breakfast` rather than raising.
5. **WORLD_BIBLE canon vs. draft location table**: canon defines *Breakfast
   Hall* and *Traitors' Turret*; no "great hall" or "traitors tower" exist.
   → `breakfast → breakfast_hall`, `turret → traitors_turret`. Canon is
   silent on a social room, so the draft's `drawing_room` was kept.
6. **Report schema drift**: real reports store `players` as a dict keyed by
   player id (older samples as well), some lack top-level `day`/`phase`.
   → `_player_projections()` accepts dict-or-list; day falls back to
   `total_days`; phase falls back to `winner`-implies-`ended`, then the last
   event's phase.
7. **Backend↔core coupling already exists** (`lobby.py`, `websocket/hub.py`
   import `src.traitorsim`; prod sets `PYTHONPATH=/app/traitorsim:/app`).
   → The projection router imports the core package lazily with a
   project-root sys.path fallback (same root candidates as `runner.py`), so
   the backend still boots where the core package is absent (503 on use).
8. **The untracked `arena/` work is disjoint** — external-agent protocol with
   in-memory state, no event bus/projection overlap. Its uncommitted
   `main.py` edit was preserved untouched; the projection router registration
   was added alongside it.
9. **Runner starts games via `python3 -m src.traitorsim` subprocess** (which
   uses `GameEngineAsync`), so engine-side hooks are the correct single place
   to emit events for UI-launched games too.
10. **Pydantic v2 (2.12.5) available in both environments**; precedent for
    Pydantic inside `src/traitorsim/` set by `arena/protocol.py`.

## What was built

| Piece | Location |
|-------|----------|
| Schemas (`GameEvent`, `WorldProjection`, phase/location maps) | `src/traitorsim/events/schemas.py` |
| JSONL event sink (`EventBus`) | `src/traitorsim/events/bus.py` |
| Projection builders (state / report / resolver) | `src/traitorsim/events/projection.py` |
| Engine hooks (guarded emits at phase boundaries) | `src/traitorsim/core/game_engine_async.py` |
| Config flag `enable_event_log` (default `True`) | `src/traitorsim/core/config.py` |
| FastAPI route `GET /api/sessions/{id}/projection/world` | `traitorsim-ui/backend/app/routers/projection.py` (+ registration in `main.py`) |
| Tests (17) | `tests/test_world_projection.py` |

## Design decisions

- **JSONL over SQLite** for the event sink: keeps the UI database schema
  untouched (additive-only requirement), trivially replayable/tail-able, no
  migration risk. The UI DB's existing `events` table continues to be fed
  from report imports, unchanged.
- **Snapshot-on-every-emit** (`world_snapshot.json`, atomic tmp+rename):
  gives the projection endpoint a live-game source without the backend
  needing engine access. Resolution order: snapshot → report.
- **Emits can never change game outcomes**: `_emit_event()` no-ops without a
  bus and swallows all exceptions to a warning log. Tests that instantiate
  `GameEngineAsync` directly are unaffected (no bus is created until
  `run_game_async()` runs with `enable_event_log=True`).
- **`GamePhase.ENDED` is now set at finale** in `GameEngineAsync` (it never
  was before). Nothing reads phase after the loop, so this is
  outcome-neutral, and it makes the final snapshot correct.
- **Omniscient v1**: `role_visible` exposes true roles for all players.
  POV filtering (faithful-safe view) is a v2 TODO — the UI's
  `usePOVVisibility` semantics are the reference for that design.
- **Path-traversal guard**: session ids must match `[A-Za-z0-9_-]+` at the
  router; anything else 404s before touching the filesystem.

## Known gaps / next steps

- **No report JSON is written by the async engine** — still true. The event
  log + snapshot now capture async games, but `/api/games` (report-based)
  won't see them. Next step: port `save_game_report()` into
  `GameEngineAsync` or derive a report from the event log at `game_ended`.
- **POV filtering (v2)**: faithful-safe projections, per-client role masking.
- **Push channel (v2)**: WebSocket event feed to replace UE polling; the
  JSONL log is already the natural source to tail.
- **Recruitment/shield/seer events**: not in the v1 vocabulary; add as new
  event types (additive, no version bump needed).
- **Containerized engine not wired**: only `GameEngineAsync` emits events (as
  scoped). Games run via `./run.sh` / `game_engine_containerized.py` produce
  reports but no live snapshots, so their projections come from the report
  path only. Wiring `EventBus` into the containerized engine is a small,
  mechanical follow-up (same `_emit_event` pattern).
- **Docker**: prod compose does not currently mount `data/sessions/` into the
  backend container; the projection endpoint serves report-based projections
  there today. Mount `../data/sessions:/app/data/sessions` (or set
  `SESSIONS_DIR`) when live-game projection is needed in prod.
- **Full event-sourced rebuild** (the deferred `traitorsim-rules` greenfield):
  the `GameEvent` vocabulary here was kept engine-agnostic so it can become
  the ingestion format for that rebuild later.

## Verification performed (2026-07-06)

- `pytest tests/ -q` → **125 passed** (108 pre-existing + 17 new); warning
  set identical to the unmodified engine (checked via stash).
- Local uvicorn (`PYTHONPATH=<repo> REPORTS_DIR=../../data/reports`, port
  8099): `sample_complete_game` and `game_20260104_012251` both return valid
  `WorldProjection` JSON; unknown session → 404; synthetic live session via
  `EventBus` + snapshot served correctly through the API (then cleaned up).
- Note: booting the backend locally requires `PYTHONPATH` to include the repo
  root because of the **pre-existing** module-level `src.traitorsim` import
  in `websocket/hub.py` (prod already sets this).
