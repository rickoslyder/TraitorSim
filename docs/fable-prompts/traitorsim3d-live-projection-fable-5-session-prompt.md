# TraitorSim3D — Live prod projection (Fable 5, standalone)

**Machine:** `rkb-mac` · **CWD:** `~/Documents/Unreal Projects/TraitorSim3D`  
**CLI:** `claude-fable-5` · **effort:** `high`  
**Harness:** Paste blocks from `~/.hermes/references/claude-fable-5-cheatsheet.md` (anti-overplanning, scope/YAGNI, brevity, autonomous) at session start.

**Prerequisite:** Dressing/audio/MH pass in `BUILD-STATUS.md`. `BP_CeremonyDirector` polls mock or static session.

**Hermes:** Richard may paste a **live `SessionId`** from Telegram (`POST https://traitorsim.rbnk.uk/api/games/run`). Runner `game_id` matches engine (`TRAITORSIM_SESSION_ID` on Dockerhost).

---

## COPY FROM HERE ↓

# Live wire — prod API during a running game

## Why

PIE verified against **mock** and **ended** snapshots. Prove the ceremony director tracks **real** `alive` / `phase` while Python sim runs on Dockerhost.

**Success:** Editor **focused** on macOS (no background poll throttle), PIE with prod `BaseUrl` + live `SessionId`, visible banish/camera/audio on ≥1 `alive→false` during `round_table`. Document in `BUILD-STATUS.md` § Live PIE.

---

## API (do not invent fields)

**GET** `https://traitorsim.rbnk.uk/api/sessions/{SessionId}/projection/world`

| Field | UE use |
|-------|--------|
| `phase` | `breakfast` \| `mission` \| `social` \| `round_table` \| `turret` \| `ended` |
| `players[]` | `seat_index`, `alive`, `display_name` |
| `day` | debug / UI |

| HTTP | Meaning |
|------|---------|
| **200** + `schema_version":"v1"` | Use payload |
| **404** | Session not started / wrong id — keep polling or ask Richard |
| **502** | Traefik/backend — retry |

**Static regression (no live game):** `game_20260706_215618` (ended, 10p, 8 banished).  
**Alternate:** `game_20260706_210532` (6p ended).

---

## Tasks (order)

1. **Preflight (Mac terminal)**  
   `curl -sS "https://traitorsim.rbnk.uk/api/sessions/game_20260706_215618/projection/world" | head -c 400`  
   Confirm JSON + `schema_version`.

2. **Director** — On placed `BP_CeremonyDirector`:  
   - `BaseUrl` = `https://traitorsim.rbnk.uk`  
   - `SessionId` = Richard’s live id **or** static id above  
   - Poll interval ~3s (existing if fine)

3. **macOS PIE** — Focus Unreal Editor before PIE (`osascript` or click window). Confirm poll timer fires (log/print).

4. **Live run** — Richard starts game (UI or API); paste `game_id` into `SessionId`. PIE through `round_table` + ≥1 banish.

5. **Regression** — Phase debounce, seat hide, MH seats 0–1, host banish wide shot, sting/ambient.

6. **Deliverables** — `BUILD-STATUS.md` update; `Saved/live_pie_banish.png` or `highresshot` if possible.

---

## Out of scope

Backend sim changes, new API fields, packaging, full 12× MetaHuman, Fab wardrobe (next session).

---

## Tooling

- Blueprint: `create_node` / `connect_nodes` — not transient pin nodes from `get_node_type_pins`.
- One asset per `run_python_script` when using ProgrammaticToolset.
- MCP serial; no modal dialogs during PIE.

## End task

Report: `SessionId`, phases seen, banish count, blockers. Next: Fab wardrobe session, sculpt session.

## COPY TO HERE ↑