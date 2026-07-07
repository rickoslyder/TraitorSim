# TraitorSim3D — Live prod projection (Fable 5)

**CWD:** `~/Documents/Unreal Projects/TraitorSim3D` · `claude-fable-5` · effort `high`  
**Style:** Goal-oriented — you choose the steps. Do not wait for a recipe.

---

## COPY FROM HERE ↓

# End goal

`BP_CeremonyDirector` drives ceremony from **production** TraitorSim, not mock JSON: poll `https://traitorsim.rbnk.uk/api/sessions/{SessionId}/projection/world` and keep existing banish/camera/audio behavior working in **PIE**.

**Done when:** You have evidence (log, screenshot, or `BUILD-STATUS.md` § Live PIE) that at least one **real** `alive→false` during `round_table` triggered the same beats we already proved on mock/static sessions — or you document precisely what blocked live timing and what *did* work on a static ended session.

**Why it matters:** Mock/static proved the graph; prod proves the show can follow a running Dockerhost sim (and Richard can paste a live `SessionId` from Hermes when he wants true live flips).

---

## Ground truth (read, don’t reinvent)

- `BUILD-STATUS.md`, `implementation-notes.md` — what already works (phase debounce, seat hide, MH 0–1, host wide shot, sting).
- API contract only: `phase`, `players[].seat_index|alive|display_name`, `day`; `schema_version` v1. No new backend fields.
- **Static sessions** if live timing is awkward: `game_20260706_215618` (10p ended), `game_20260706_210532` (6p ended). Example live id from Hermes: `game_20260706_233625`.
- **macOS:** Editor must stay focused during PIE or poll timers throttle — you fix that however fits.
- **Runner alignment:** `game_id` on server matches session files (`TRAITORSIM_SESSION_ID`); use the id Richard gives you.

---

## Boundaries

- No sim/API/backend changes, no packaging, no Fab wardrobe, no sculpt pass, no new ceremony features.
- UE/MCP: serial tool use; no modal dialogs in PIE; Blueprint edits via durable nodes (`create_node`), not transient pin scaffolding.

---

## Close-out

TLDR: session id(s) tried, what phases/banishes you saw, regression gaps, one screenshot path if any. Say what Richard should do for the *next* live attempt (e.g. “message Hermes for fresh `game_id` then PIE immediately”).

## COPY TO HERE ↑