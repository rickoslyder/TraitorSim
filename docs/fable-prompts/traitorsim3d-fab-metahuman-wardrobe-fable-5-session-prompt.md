# TraitorSim3D — Fab MetaHuman wardrobe (Fable 5)

**CWD:** `~/Documents/Unreal Projects/TraitorSim3D` · `claude-fable-5` · effort `high`  
**Style:** Goal-oriented — you choose the steps.

---

## COPY FROM HERE ↓

# End goal

TraitorSim’s **castle dinner** cast (modern UK, ages 21–54, not fantasy armor) looks intentional on **MetaHuman seats 0–1** using Richard’s **Fab library** plus what’s already in the project — without breaking banish/hide/camera.

**Done when:**

1. `Content/TraitorSim/FAB-WARDROBE-MAP.md` exists: what you imported, what you skipped, seat assignments, applied Y/N.
2. Viewport or `Saved/fab_wardrobe_seats01.png` shows **visible** wardrobe/groom improvement on seats **0–1**.
3. You state top **5** Fab items worth keeping for this show and which of the **37** library MetaHuman listings are waste for TraitorSim.

**Why:** 37 MetaHuman Fab listings are in **Launcher library** (2026-07-06); only grooms + `MH_Host` / `MH_Faithful1` are in-project today. Outfits live in `Content/` only after **Add to project** (Launcher Fab or **Window → Fab**).

---

## Ground truth (mandatory read)

`docs/fable-prompts/traitorsim3d-fab-mac-verified.md` — verified paths. **Do not** scan nonexistent `Common/Fab` / `FabCache`.  
Already on disk: `Content/Grooms/` (~733 MB), `Content/TraitorSim/MetaHumans/`.  
Apply via same family as `Content/Python/mh_build.py`. Generic SK meshes ≠ MetaHuman bodies (prop-only).  
Cast brief: seat 0 host male ~40s formal dark; seat 1 female ~30s smart/analytical; 2–3 palette families for wider cast; no traitor/faithful costume coding in v1.

---

## Boundaries

- No sculpt API session work, no C++ plugin, no full castle relight, no backend.
- PIE: document MH banish if death anim still skips.

---

## Close-out

TLDR: imports added, seats touched, blockers (add-to-project, rig, auth). What the sculpt session should reuse from your map.

## COPY TO HERE ↑