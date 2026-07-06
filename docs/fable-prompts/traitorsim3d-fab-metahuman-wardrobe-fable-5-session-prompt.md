# TraitorSim3D — Fab MetaHuman wardrobe (Fable 5, standalone)

**Machine:** `rkb-mac` · **CWD:** `~/Documents/Unreal Projects/TraitorSim3D`  
**CLI:** `claude-fable-5` · **effort:** `high`  
**Harness:** Paste blocks from `~/.hermes/references/claude-fable-5-cheatsheet.md` at session start.

**Read first (verified 2026-07-07):** `docs/fable-prompts/traitorsim3d-fab-mac-verified.md` (or Hermes `~/.hermes/references/traitorsim3d-fab-mac-verified.md`).

**Prerequisite:** `mh_build.py` placed MetaHumans on seats **0–1**. Other seats may be Manny/mannequin until this pass.

---

## COPY FROM HERE ↓

# Fab library → TraitorSim cast wardrobe

## Why

Richard acquired **37 MetaHuman Fab listings** in Epic Launcher (2026-07-06). They are in **Fab library**, not all in the project yet. Castle-dinner cast needs modern UK wardrobe (21–54), not fantasy armor.

**Success:**  
- `Content/TraitorSim/FAB-WARDROBE-MAP.md` — every **relevant** asset (name, type, seats, applied Y/N).  
- **Add to project** for top picks into `Content/TraitorSim/Wardrobe/` (or documented paths).  
- **Seats 0–1** visibly updated in viewport + `Saved/fab_wardrobe_seats01.png`.  
- **Grooms** from existing `Content/Grooms/` applied where cheap.

---

## Verified machine state (do not re-guess paths)

| Fact | Detail |
|------|--------|
| Library downloads | **37** `listing/metahuman` in `~/Library/Application Support/Epic/EpicGamesLauncher/Saved/Config/MacEditor/GameUserSettings.ini` |
| **Not** valid scan roots | `…/UnrealEngine/Common/Fab`, `…/FabCache` — **missing on this Mac** |
| Already in project | `Content/Grooms/` (~733 MB), `Content/TraitorSim/MetaHumans/MH_Host`, `MH_Faithful1` |
| Fab UE plugin | `FabPlugin_5.8` installed |
| Permanent UE assets | Only under **`Content/`** after **Add to project** (Launcher Fab tab or **Window → Fab** in editor) |

---

## Step 1 — Inventory (authoritative sources)

**A. Launcher / editor (primary)**  
1. Epic Launcher → **Fab** → **My Library** → filter MetaHuman; note titles.  
2. Unreal → **Window → Fab** (or Content Drawer **Fab**); list items **not yet** in project.  
3. For each useful listing: **Add to project** → **TraitorSim3D** → folder `Content/TraitorSim/Wardrobe/<ShortName>`.

**B. On-disk project (secondary)**  
```bash
cd "$HOME/Documents/Unreal Projects/TraitorSim3D"
find Content -maxdepth 5 \( -iname '*Outfit*' -o -iname '*Groom*' -o -iname '*MetaHuman*' -o -iname '*.uasset' \) 2>/dev/null | head -300
ls -la Content/Grooms Content/TraitorSim/MetaHumans
```

**C. Library count (sanity)**  
```bash
grep -c 'listing/metahuman' "$HOME/Library/Application Support/Epic/EpicGamesLauncher/Saved/Config/MacEditor/GameUserSettings.ini"
# expect 37
```

Build table in `FAB-WARDROBE-MAP.md`:

| Display name | Source (Fab uuid if known) | Type | Style | Seats | Imported path | Applied |

---

## Step 2 — Cast brief

- **Setting:** Ardross-style castle; **modern UK** contestants.  
- **Seat 0:** Host male ~40s — formal, dark, commanding.  
- **Seat 1:** Female ~30s — smart evening / analytical, not runway glam.  
- **Seats 2–11:** Diverse; **2–3 palette families** (stone, burgundy, navy, tweed).  
- **Traitor/faithful:** no obvious red/black costume coding in v1.

---

## Step 3 — Apply

1. **Outfits** — MetaHuman-compatible only; swap on seats **0–1** first via same patterns as `Content/Python/mh_build.py` (plugin examples / assembly API).  
2. **Grooms** — Pull from `Content/Grooms/Hair_MyAdvancedGroom`, `FacialHair_Grooms` for variety on 0–1 (and 2–3 if fast).  
3. **FBX library items (3)** — prop-only unless proven retarget; document in map.  
4. **Reject** — generic SK meshes forced onto MH bodies; fantasy armor; duplicate near-identical suits for all 12.

**Verify:** PIE banish on MH seat — collapse may skip Manny death anim; document behavior.

---

## Step 4 — Automation (light)

| Artifact | Purpose |
|----------|---------|
| `Tools/inventory_fab_metahuman.py` | Re-run disk + ini count |
| `Content/Python/apply_fab_wardrobe.py` | Idempotent apply for mapped seats |
| Optional extend `mh_build.py` | `--outfit` / groom paths from map |

---

## Out of scope

Sculpt API (next session), C++ plugin, full castle relight, seats 4–11 full MH assembly unless time remains.

## End task

- Top **5** Fab items to keep for TraitorSim  
- Which library downloads are **skip** for this show  
- Seats updated + screenshot path  
- Blockers (auth, add-to-project failed, wrong rig)

## COPY TO HERE ↑