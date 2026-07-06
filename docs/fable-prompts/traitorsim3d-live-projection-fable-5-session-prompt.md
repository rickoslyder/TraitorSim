# TraitorSim3D — Live prod projection (Fable 5, standalone)

**Use with:** Claude Code on **rkb-mac**, CWD `~/Documents/Unreal Projects/TraitorSim3D`, **`claude-fable-5`**, effort **`high`**.

**Prerequisite:** Dressing/audio/MetaHuman pass complete (`BUILD-STATUS.md`). `BP_CeremonyDirector` polls mock or static session today.

**Hermes coordination:** Richard may paste a **live `SessionId`** from Telegram (game started via `POST /api/games/run` on prod). Use that exact id — runner `game_id` now matches engine via `TRAITORSIM_SESSION_ID`.

---

## COPY FROM HERE ↓

# Live wire — prod API during a running game

## Why

PIE verified against **mock** and **ended** snapshots. Next: prove the ceremony director tracks **real** `alive` / `phase` flips while the Python sim runs on Dockerhost.

**Success:** Editor focused (macOS — no background throttle), PIE with prod `BaseUrl` + live `SessionId`, visible banish/camera/audio on at least one `alive→false` during `round_table`. Document steps in `BUILD-STATUS.md` § Live PIE.

---

## API (do not invent fields)

**GET** `https://traitorsim.rbnk.uk/api/sessions/{SessionId}/projection/world`

| Field | UE use |
|-------|--------|
| `phase` | `breakfast` \| `mission` \| `social` \| `round_table` \| `turret` \| `ended` |
| `players[]` | `seat_index`, `alive`, `display_name` |
| `day` | debug / UI |

**404:** Session not started yet — keep polling. **Wrong id:** Ask Richard for id from `GET /api/games/run/status` or Hermes message.

**Static demo (no live game):** `game_20260706_215618` (ended, 10 players, 8 banished) — use to regression-test banish replay without starting sim.

---

## Tasks (order)

1. **Preflight** — `curl` the session URL from Mac terminal; confirm JSON `schema_version":"v1"`.
2. **Director vars** — On placed `BP_CeremonyDirector`: `BaseUrl=https://traitorsim.rbnk.uk`, `SessionId=<live or static>`, poll interval 3s (or existing).
3. **macOS** — Before PIE: activate editor (`osascript` or focus window). Confirm poll timer fires (debug print or log).
4. **Live run** — Richard starts game from UI/API; paste `game_id` into `SessionId`. PIE until `round_table` and at least one banish beat.
5. **Regression** — Phase debounce, seat hide, MetaHuman seats 0–1, host banish wide shot, sting/ambient.
6. **Deliverables** — Update `BUILD-STATUS.md`, one `highresshot` or viewport capture during live banish if possible.

---

## Out of scope

- Rewriting backend sim, new API fields, packaging, full 12× MetaHuman.

---

## Harness reminders

- `create_node` for graph edits — not `get_node_type_pins` transients.
- One asset per `run_python_script` when using ProgrammaticToolset.
- MCP serial; no modal dialogs during PIE.

## End task

Report: session id used, phases observed, banish count, blockers. List follow-up: Fab wardrobe pass, sculpt pass, seats 2–11.

## COPY TO HERE ↑