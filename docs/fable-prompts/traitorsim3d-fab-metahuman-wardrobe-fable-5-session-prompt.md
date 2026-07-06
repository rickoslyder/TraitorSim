# TraitorSim3D — Fab MetaHuman wardrobe audit (Fable 5, standalone)

**Use with:** Claude Code on **rkb-mac**, CWD `~/Documents/Unreal Projects/TraitorSim3D`, **`claude-fable-5`**, effort **`high`**.

**Context:** Richard downloaded **30+ MetaHuman outfits / Fab items** via Epic Games Launcher. Inventory them and assign the best fits to the **12-seat social-deduction cast** (castle dinner, UK ages 21–54, mix of class vibes per sim personas).

**Prerequisite:** `mh_build.py` already placed default MetaHumans on seats 0–1. Manny/mannequin on other seats unless this pass also retargets.

---

## COPY FROM HERE ↓

# Fab vault inventory → TraitorSim cast wardrobe

## Why

Default MetaHuman archetypes read generic. Fab downloads may include period-appropriate, formal, or “castle dinner” clothing, grooms, hair, accessories. Map assets to seats **without** breaking banish/hide/camera logic.

**Success:** Written `docs/FAB-WARDROBE-MAP.md` (or `Content/TraitorSim/FAB-WARDROBE-MAP.md`) listing every relevant Fab asset, recommended seat assignment, and what was **actually applied** in the project. At least **seats 0–1** visibly updated in editor viewport + one screenshot.

---

## Step 1 — Discover Fab content (run first)

Execute `Tools/inventory_fab_metahuman.py` (create if missing) or shell:

```bash
# Common Epic / Fab locations on Mac — search all
FAB_ROOTS=(
  "$HOME/Library/Application Support/Epic/UnrealEngine/Common/Fab"
  "$HOME/Library/Application Support/Epic/FabCache"
  "$HOME/Documents/Unreal Projects/TraitorSim3D/Content"
  "$HOME/Documents/Unreal Projects/TraitorSim3D/Plugins"
)
for r in "${FAB_ROOTS[@]}"; do
  [ -d "$r" ] && find "$r" -maxdepth 6 \( -iname '*metahuman*' -o -iname '*MH*' -o -iname '*Outfit*' -o -iname '*Groom*' -o -iname '*.uasset' \) 2>/dev/null | head -200
done
```

Also: **Content Browser → Fab / Vault** in editor; list imports already in `/Game/` tree.

Produce a table:

| Asset path | Type (outfit/groom/acc) | Style notes | Suggested seats |
|------------|-------------------------|-------------|-----------------|

---

## Step 2 — Cast brief (TraitorSim tone)

- Setting: Ardross-style castle, **modern UK contestants** (not fantasy armor).
- Seat 0: host / authority (male ~40s) — formal, dark, commanding.
- Seat 1: key faithful (female ~30s) — smart casual / evening.
- Seats 2–11: diverse ages/occupations from sim — avoid 12 identical suits; **2–3 palette families** max (stone, burgundy, navy, tweed).

Traitor vs faithful: **no** obvious red/black coding in v1 (omniscient `role_visible` is debug only).

---

## Step 3 — Apply via MetaHuman API

Use plugin Python examples (same family as `mh_build.py`):

- Swap **outfit** / **groom** on existing MetaHuman actors for seats 0–1 first.
- If Fab assets are **MetaHuman DNA compatible** — bind through Creator/Assembly pipeline.
- If assets are **generic skeletal meshes** — do **not** force onto MetaHuman body; note as “prop-only” in map.

**Verify:** PIE banish still works (collapse anim may skip on MH skeleton — document).

---

## Step 4 — Optional quick wins

- Torch-adjacent **material** tweaks from Fab environment packs.
- **Hair/groom** variety for seats 2–3 if cheap.

---

## Deliverables

| Artifact | Purpose |
|----------|---------|
| `Tools/inventory_fab_metahuman.py` | Repeatable Fab scan |
| `Content/TraitorSim/FAB-WARDROBE-MAP.md` | Human-readable map |
| Updated `mh_build.py` or `Content/Python/apply_fab_wardrobe.py` | Idempotent apply |
| Viewport capture | `Saved/fab_wardrobe_seats01.png` |

---

## Out of scope

- Sculpt API (next session), C++ plugin code, rebaking lighting for full castle.

## End task

Top 5 Fab assets Richard should keep; which downloads are useless for this project; seats updated; blockers (wrong skeleton, missing plugin).

## COPY TO HERE ↑