# TraitorSim3D — BP_CeremonyDirector HTTP polling (Fable 5, standalone)

> **LEGACY stepped checklist** — Blueprint HTTP/DSL traps. **New work:** `traitorsim3d-fable-session-order.md` + skill **`claude-fable-5`**.

**Use with:** Claude Code on **rkb-mac**, CWD `~/Documents/Unreal Projects/TraitorSim3D`, **`claude-fable-5`**, effort **`high`**.

**Prerequisite:** API deployed or reachable — `GET https://traitorsim.rbnk.uk/api/sessions/{session_id}/projection/world` returns v1 JSON (see `API-CONTRACT.md` on Dockerhost). For offline dev, use a **mock JSON file** or local uvicorn.

**Load:** `unreal-engine-mcp` skill habits (EditorToolset enabled, MCP serial, no Python remote exec on Mac).

---

## COPY FROM HERE ↓

# BP_CeremonyDirector — live world projection (v1)

## Why

TraitorSim3D greybox is done (`L_CastleCourt`, 12 seat mannequins, `LS_RoundTable_Wide`). The Python sim exposes **`WorldProjection`** JSON. Wire **`BP_CeremonyDirector`** to poll that endpoint and drive **phase changes** + **seat visibility** — still **no game logic in UE**.

**Success:** In PIE (or packaged dev), with a valid `session_id`, the director polls every **3s**, calls **`OnPhaseChanged`** when `phase` changes, and updates mannequin visibility from `players[].alive` + `seat_index`. Document config in `BUILD-STATUS.md`.

---

## API contract (v1 — do not invent fields)

**GET** `{BaseUrl}/api/sessions/{SessionId}/projection/world`

| Field | Use in UE |
|-------|-----------|
| `phase` | `breakfast` \| `mission` \| `social` \| `round_table` \| `turret` \| `ended` → `OnPhaseChanged` |
| `location_id` | Log + optional sub-level hook later (`breakfast_hall`, `round_table`, `traitors_turret`, …) |
| `players[]` | `id`, `display_name`, `alive`, `seat_index`, `role_visible` (omniscient v1) |
| `day`, `alive_count`, `prize_pot` | Optional UI/debug |

**Defaults (editable on placed actor):**

- `BaseUrl` = `https://traitorsim.rbnk.uk`
- `SessionId` = e.g. `game_20260104_012251` (report stem for static demo)
- `PollIntervalSeconds` = `3.0`

**404:** Log once, keep polling (session may not exist yet).

---

## Seat mapping

Level has **12** mannequins in folder `CastleCourt/Figures` at the seat ring. In v1:

1. Add **`SeatIndex`** (int 0–11) to each mannequin **or** build an array on the director: `SeatActors[12]`.
2. On each successful poll: for each `players[]` entry with `seat_index`, set actor **hidden** if `alive == false`, **visible** if true.
3. Unmapped seats: leave visible (greybox).

Do **not** implement role-based materials yet unless trivial (optional `role_visible` → debug print only).

---

## Blueprint work (`BP_CeremonyDirector`)

Extend existing stub at `/Game/TraitorSim/Blueprints/BP_CeremonyDirector`:

1. Variables: `BaseUrl`, `SessionId`, `PollIntervalSeconds`, `LastPhase` (string), `SeatActors` (array of Actor refs) or discover via tags `TraitorSim.Seat.0` … `11`.
2. **Timer** on BeginPlay → poll loop (Blueprint **HTTP** node or `VaRest` if project already has plugin — prefer engine **HTTP Request** / `UKismetSystemLibrary` pattern that works in UE 5.8 without new plugins; if HTTP in BP is painful, one **Blueprint Function Library** C++ is **out of scope** — use **Python editor script only** if needed for test, but **runtime polling must be Blueprint**).
3. Parse JSON (Blueprint **JsonUtilities** / `JsonObject` nodes).
4. If `phase != LastPhase` → call **`OnPhaseChanged(phase)`**, update `LastPhase`.
5. Apply seat visibility pass.

**EditorToolset / MCP:** use MCP to place/configure instance in `L_CastleCourt`, set default `SessionId`, save level.

---

## Update docs

- `Content/TraitorSim/README-integration.md` — replace draft with real URL, field list, location_id map from API-CONTRACT.
- `BUILD-STATUS.md` — “Live polling” section + how to test.

---

## Verification

1. **Mock test:** `SessionId` pointed at known prod report → poll returns 200 → phase prints on first fetch.
2. **PIE:** Director instance in level; Output Log shows phase + poll success.
3. **Seat test:** Manually edit mock JSON or use report with eliminations → dead seats hide.
4. Cold open level: no Fatal errors.

---

## Negative prompts

- No rewrite of Python backend.
- No new plugins without asking.
- No multiplayer/replication.
- No C++ module.
- Do not change MCP plugin stack.

---

## If HTTP in Blueprint blocked

Ship **`BP_CeremonyDirector_Mock`** that reads **`Content/TraitorSim/mock_projection.json`** on a timer with the **same** parse/seat logic; document switch to live URL. Still counts as success if mock path is proven and live URL is one variable away.

## COPY UNTIL HERE ↑