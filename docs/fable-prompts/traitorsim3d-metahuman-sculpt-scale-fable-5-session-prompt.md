# TraitorSim3D — MetaHuman sculpt + seats 2–11 (Fable 5, standalone)

**Machine:** `rkb-mac` · **CWD:** `~/Documents/Unreal Projects/TraitorSim3D`  
**CLI:** `claude-fable-5` · **effort:** `high`  
**Harness:** Paste blocks from `~/.hermes/references/claude-fable-5-cheatsheet.md` at session start.

**Prerequisite:** Live PIE optional. **Fab wardrobe** done or skipped — use `Content/TraitorSim/FAB-WARDROBE-MAP.md` if it exists. Seats 0–1 MH via `mh_build.py`.

---

## COPY FROM HERE ↓

# Sculpt hero faces + scale cast (phased)

## Why

Default archetypes + Manny on seats 2+ break immersion. **Hero sculpt** host + lead faithful; scale MH count with wardrobe from Fab pass; keep banish/camera graph stable.

**Success:** Documented sculpt targets for seats 0–1; **visible** banish motion on MH (not silent skip); plan + **≥2** additional MH seats (2–3) if cloud rig budget allows; updated `BUILD-STATUS.md` + `implementation-notes.md`.

---

## Phase A — Sculpt API (seats 0–1)

1. Use MetaHuman Creator plugin Python patterns (same family as `Content/Python/mh_build.py`).  
2. Brief:  
   - **Seat 0:** Male ~40s, authoritative UK host (Northern/Welsh-lean OK, not caricature).  
   - **Seat 1:** Female ~30s, sharp, analytical — not glam runway.  
3. Headless cloud rig + texture synthesis (launcher session auth).  
4. Re-assemble into existing `SeatActors[0]` / `[1]` — **do not** rewire banish Blueprint graph.

---

## Phase B — Banish on MetaHuman skeleton

- `MM_Death_Front_01` **silently skips** on MH — fix with one of:  
  - Retargeted slump/death compatible with MH skeleton, **or**  
  - ~1.5s **AB** layered slump while seated.  
- Keep timing: collapse → poll hides ~3s later.

---

## Phase C — Scale seats 2–11

| Tier | Target |
|------|--------|
| **Minimum** | MH 0–3 + mannequins 4–11 with Fab outfits from map |
| **Stretch** | MH 0–5 with `Content/Grooms/` + wardrobe variance |
| **Perf** | LOD; limit heavy grooms; note PIE FPS |

Extend `mh_build.py` CLI: e.g. `--seats 0,1,2,3` with archetype rotation; reuse outfits from `FAB-WARDROBE-MAP.md`.

**Already on disk:** `Content/Grooms/` for hair; `MH_Host` / `MH_Faithful1` trees — extend, don’t duplicate from scratch.

---

## Verification

- [ ] Viewport screenshot seats 0–1 post-sculpt  
- [ ] PIE: MH banish shows motion  
- [ ] PIE: mannequin seats still use death anim  
- [ ] Seat coverage table in `BUILD-STATUS.md`

---

## Out of scope

Lip sync, voice face, full mocap, backend/API.

## End task

Seat table, cloud rig time, anim asset paths, recommendation for seats 4–11.

## COPY TO HERE ↑