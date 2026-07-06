# TraitorSim3D — MetaHuman sculpt + seats 2–11 scale (Fable 5, standalone)

**Use with:** Claude Code on **rkb-mac**, CWD `~/Documents/Unreal Projects/TraitorSim3D`, **`claude-fable-5`**, effort **`high`**.

**Prerequisite:** Fab wardrobe pass done (or skipped if no usable outfits). Seats 0–1 MetaHumans exist via `mh_build.py`.

---

## COPY FROM HERE ↓

# Sculpt key faces + scale cast to 12 MetaHumans (phased)

## Why

Default archetypes and Manny mannequins break immersion. Target: **recognizable host + 1–2 leads** sculpted; remaining seats either MetaHuman clones with wardrobe variance or **hybrid** (MH heroes + mannequins) if cloud rig budget/time tight.

**Success:** Documented sculpt params for host (male ~40s) + seat 1 (female ~30s); banish-compatible behavior on MH skeleton (new anim or AB pose); plan for seats 2–11 with **at least 2 more** MH swaps if feasible.

---

## Phase A — Sculpt API (seats 0–1)

1. Read MetaHuman Creator plugin Python tests in engine tree (same sources used in `mh_build.py`).
2. Apply sculpt deltas toward brief:
   - Seat 0: authoritative male, 40s, Northern/Welsh-adjacent acceptable generic UK.
   - Seat 1: female 30s, analytical, sharp features — not glam runway.
3. Re-run cloud rig + texture synthesis headless (launcher session auth).
4. Re-assemble into existing `SeatActors[0]` / `[1]` without rewiring banish graph.

---

## Phase B — Banish animation on MetaHuman skeleton

- Manny `MM_Death_Front_01` **silently skips** on MH — find or retarget:
  - MetaHuman-compatible death / slump / sit-to-floor from Marketplace/Manny pack retarget, **or**
  - 1.5s **Animation Blueprint** layered blend (upper body slump, mesh stays seated).
- Keep existing timing: collapse → poll hides ~3s later.

---

## Phase C — Scale (seats 2–11)

| Tier | Approach |
|------|----------|
| **Minimum** | 4 MH (0,1,2,3) + mannequins 4–11 with Fab outfits if possible |
| **Target** | 12 MH with shared body types + wardrobe from `FAB-WARDROBE-MAP.md` |
| **Perf guard** | LOD + limit simultaneous groom complexity; document FPS in PIE |

Automate via extended `mh_build.py` CLI: `--seats 0,1,2,3` with archetype rotation.

---

## Verification

- [ ] Viewport: seats 0–1 match sculpt brief (screenshot).
- [ ] PIE: banish on MH seat shows visible motion (not T-pose pop).
- [ ] PIE: mannequin seats still banish with death anim.
- [ ] `BUILD-STATUS.md` + `implementation-notes.md` updated.

---

## Out of scope

- Lip sync, voice-driven face, full body mocap.

## End task

Seat coverage table, cloud rig minutes used, anim asset paths, recommendation for remaining seats.

## COPY TO HERE ↑