# TraitorSim3D — dressing + banish camera (Fable 5, standalone)

**Use with:** Claude Code on **rkb-mac**, CWD `~/Documents/Unreal Projects/TraitorSim3D`, **`claude-fable-5`**, effort **`high`**.

**Prerequisites:** Greybox + `BP_CeremonyDirector` HTTP polling verified (`BUILD-STATUS.md`). Prod API: `https://traitorsim.rbnk.uk/api/sessions/{id}/projection/world`.

**Load:** `unreal-engine-mcp` (EditorToolset, MCP serial, Blueprint graph DSL if needed).

---

## COPY FROM HERE ↓

# Art pass — castle dressing + banish camera beat

## Why

Round-table **polling and seat hide/show work**. Next: make the court **read as a castle** (materials, torches, fog, audio stubs) and add a **banish moment** when `OnPhaseChanged` fires during `round_table` after a banish (use `players[].alive` delta or `PLAYER_BANISHED` is API-only — **detect alive→false between polls** in Blueprint).

**Success:** `L_CastleCourt` looks intentional (not greybox); one **Sequence** or **camera cut** plays when a seat is eliminated during round table; `BUILD-STATUS.md` updated; PIE demo with mock or prod session.

---

## Scope (this session only)

### 1) Environment dressing (greybox → mood)

- **Materials:** stone floor/walls (engine or Quixel placeholders), dark wood on table props if any.
- **Lighting:** warm key on table, cool fill, **volumetric fog** light volume (subtle).
- **Torches / point lights** around ring — 4–8, no perf meltdown.
- **Post:** slight vignette via Post Process Volume (optional).
- **Audio:** placeholder **Ambient** cue (loop) + **One-shot** sting for banish (can be silent cue with log).

**Out of scope:** MetaHuman faces, full castle exterior, multiplayer.

### 2) Banish camera beat

- Extend **`BP_CeremonyDirector`** (or child **`BP_BanishCameraController`**):
  - Track **previous alive mask** per `seat_index` (bool array length 12).
  - On poll, if `round_table` phase and seat *i* transitions alive→dead → fire **`OnPlayerBanished(seat_index, display_name)`** (new event).
- **`LS_Banish_Close`** (new Level Sequence, 3–8 s):
  - Cut or blend from `CineCam_RoundTableWide` to a **closer** camera on that seat’s mannequin.
  - Optional: hide actor 0.5 s after cut (already hidden by polling — sequence is **drama**, not logic).
- Wire `OnPlayerBanished` → play sequence (use existing `LS_RoundTable_Wide` binding pattern).

### 3) Phase hooks (light)

| `phase` | UE action |
|---------|-----------|
| `round_table` | Ensure wide cam / sequence default |
| `turret` | Log + optional cool grade (blue tint post) |
| `breakfast` | Optional: dim table lights |

No new HTTP fields.

---

## MCP / editor rules

- Save level + blueprint after changes; quit editor cleanly before claiming done.
- Verify with **PIE** + mock server or prod `SessionId`.
- If Blueprint DSL: custom events must exist before `write_graph_dsl`; document in `implementation-notes.md`.

---

## Deliverables

| Artifact | Purpose |
|----------|---------|
| Updated `L_CastleCourt` | Dressing |
| `LS_Banish_Close` | Banish beat |
| `BP_CeremonyDirector` or helper BP | Alive delta + `OnPlayerBanished` |
| `BUILD-STATUS.md` | Test steps |
| `implementation-notes.md` | Banish detection + seq quirks |

---

## Verification checklist

- [ ] PIE: court reads as lit castle, not flat grey.
- [ ] Mock: flip one player `alive` false in `mock_projection.json` during `round_table` → banish seq plays once per seat (debounce).
- [ ] No regression: phase debounce + seat visibility still work.
- [ ] MCP screenshot or `highresshot` of dressed court.

## End task

Report what changed, how to trigger banish in PIE, and follow-up chips (MetaHuman, other locations).

## COPY TO HERE ↑