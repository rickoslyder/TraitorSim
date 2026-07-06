# TraitorSim API Contract — World Projection (v1)

Stable HTTP contract for world-state projection, consumed by **TraitorSim3D
(Unreal)** and the web dashboard. This is an additive shim over the existing
engines — it does not replace the report JSON import path or any existing
`/api/games` endpoint.

- **Version:** `v1` (every projection response carries `"schema_version": "v1"`)
- **Schemas:** [`src/traitorsim/events/schemas.py`](src/traitorsim/events/schemas.py) (Pydantic v2)
- **UE polling:** poll the projection endpoint every **1–5 seconds**. Responses
  are small (~1–5 KB for 22 players). There is no push channel in v1; a
  WebSocket feed is a candidate for v2.
- **TraitorSim3D stub path:** point the UE HTTP client at
  `GET {base_url}/api/sessions/{session_id}/projection/world` (production base:
  `https://traitorsim.rbnk.uk`). Local dev base: `http://127.0.0.1:8000` (or
  whatever port uvicorn runs on).

---

## Session IDs

A `session_id` identifies one game run. It equals the **report filename stem**
for completed games (e.g. `game_20260104_012251` for
`data/reports/game_20260104_012251.json`) — the same convention the UI
database uses for `game_id`. Live runs of `GameEngineAsync` generate ids in
the identical `game_YYYYMMDD_HHMMSS` format.

Allowed characters: `[A-Za-z0-9_-]+`. Anything else is a 404.

## Endpoint

```
GET /api/sessions/{session_id}/projection/world
```

| Status | Meaning |
|--------|---------|
| `200`  | `WorldProjection` JSON (below) |
| `404`  | Unknown session (no live snapshot and no report on disk) |
| `503`  | Core `src/traitorsim/events` package not importable in this deployment |

**Resolution order** (server side):

1. **Live snapshot** — `data/sessions/{session_id}/world_snapshot.json`,
   refreshed by the engine on every emitted event. Serves running games and
   is the freshest source.
2. **Completed report** — `{REPORTS_DIR}/{session_id}.json`, mapped to a
   projection on the fly. Serves any historical game.

### Example response

```json
{
  "schema_version": "v1",
  "session_id": "game_20260104_012251",
  "day": 11,
  "phase": "round_table",
  "location_id": "round_table",
  "players": [
    {
      "id": "player_00",
      "display_name": "Rae Sinclair",
      "alive": true,
      "seat_index": 0,
      "role_visible": "traitor"
    },
    {
      "id": "player_01",
      "display_name": "Gemma Ashworth-Clarke",
      "alive": false,
      "seat_index": 1,
      "role_visible": "faithful"
    }
  ],
  "prize_pot": 47280.49,
  "alive_count": 3
}
```

### Field reference — `WorldProjection`

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | string | Always `"v1"` for this contract |
| `session_id` | string | Echoes the path parameter |
| `day` | int | Game day (1-based) |
| `phase` | string enum | `breakfast` \| `mission` \| `social` \| `round_table` \| `turret` \| `ended` |
| `location_id` | string | Derived from `phase` via the table below |
| `players` | array | One entry per player, stable `seat_index` ordering |
| `prize_pot` | float | Current prize pot |
| `alive_count` | int | Count of players with `alive: true` |

### Field reference — player entry

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | Engine player id, e.g. `player_07` |
| `display_name` | string | Persona name |
| `alive` | bool | |
| `seat_index` | int \| null | Stable ordering for seating/placement in UE |
| `role_visible` | string \| null | `"traitor"` \| `"faithful"`. **v1 is omniscient**: the true role is exposed for every player. A POV-filtered mode (hide traitor roles from faithful-view clients) is a documented TODO for v2 — do not build spoiler-sensitive UI against v1 without your own filtering. |

## Phase → location map

Location ids follow the `WORLD_BIBLE.md` *Spatial Graph and Castle Layout*
section. Two ids differ from the original draft table because canon demands
it: the morning gathering room is the **Breakfast Hall** (no "great hall"
exists in canon) and the traitors meet in the **Traitors' Turret** (not a
"tower").

| Phase | `location_id` |
|-------|----------------|
| `breakfast` | `breakfast_hall` |
| `mission` | `castle_grounds` |
| `social` | `drawing_room` |
| `round_table` | `round_table` |
| `turret` | `traitors_turret` |
| `ended` | `round_table` |

Engine-internal phase strings are normalized before they reach clients:
`game_ended` → `ended`, `initialization` → `breakfast`, `roundtable` →
`round_table`. Clients only ever see the six values above.

## Event log (persistence format)

The event sink is **append-only JSONL** (chosen over SQLite to keep the UI
database untouched and the log trivially replayable/tail-able):

```
data/sessions/{session_id}/
├── events.jsonl          # one GameEvent per line, append-only
└── world_snapshot.json   # latest WorldProjection, atomically replaced
```

`GameEvent` line format:

```json
{
  "session_id": "game_20260706_120000",
  "timestamp": "2026-07-06T12:00:01.123456+00:00",
  "type": "phase_changed",
  "day": 3,
  "phase": "turret",
  "payload": {"phase": "turret"}
}
```

Event `type` vocabulary (v1): `session_started`, `day_started`,
`phase_changed`, `player_banished`, `player_murdered`, `vote_completed`,
`game_ended`. The `payload` dict is event-specific and may gain keys without
a version bump; removing or renaming keys requires `v2`.

Events are emitted by `GameEngineAsync` (guarded — event logging can never
alter game outcomes; failures degrade to a warning log). Disable with
`GameConfig(enable_event_log=False)` or inject a custom bus via
`GameEngineAsync(config, event_bus=...)`.

## Versioning

- `v1` is additive-stable: new optional fields and new event types may appear;
  existing fields will not be removed or change meaning.
- Breaking changes bump `schema_version` and will be served alongside `v1`
  during a deprecation window.

## Server configuration

| Env var | Default | Used for |
|---------|---------|----------|
| `REPORTS_DIR` | `/app/reports` | Completed report JSONs (backend convention) |
| `SESSIONS_DIR` | auto-detected `data/sessions` under the project root | Live snapshots + event logs |
| `TRAITORSIM_SESSIONS_DIR` | `<repo>/data/sessions` | Engine-side sink location |
