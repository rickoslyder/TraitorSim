# TraitorSim3D — Sculpt & likeness (Fable session 2)

**Prereq:** Session 1 done (`BUILD-STATUS.md` § Production ceremony). **Do not** redo prod polling, wardrobe import, or MH death skeleton hack.

**Mac:** `cd ~/Documents/Unreal\ Projects/TraitorSim3D` · `claude-fable-5` · effort **`high`**

---

## Paste 1 — harness

```
When you have enough information to act, act. Do not re-derive facts already established in the conversation, re-litigate a decision the user has already made, or narrate options you will not pursue in user-facing messages. If you are weighing a choice, give a recommendation, not an exhaustive survey. This does not apply to thinking blocks.

Don't add features, refactor, or introduce abstractions beyond what the task requires. A bug fix doesn't need surrounding cleanup. Don't design for hypothetical future requirements. Only validate at system boundaries (user input, external APIs).

You are operating autonomously. The user cannot answer questions mid-task. For reversible actions that follow from the original request, proceed without asking. Before ending your turn, if your last paragraph is a plan or promise you have not executed, do that work now with tool calls.
```

---

## Paste 2 — task (COPY FROM HERE ↓)

# TraitorSim3D — hero likeness + cast polish (session 2)

## End goal

The **presenter host** (`HostActor` / `MH_Host`, standing) and **seat-1 contestant** (`MH_Faithful1`) look like **specific UK adults** on camera—not default MetaHuman archetypes—with **believable skin** (no red-hand artifact), **readable hair** at banish distance, and **intentional garment color** (charcoal host, faithful palette from `FAB-WARDROBE-MAP.md`). Richard gets a honest plan for **seats 2–3** (stretch: one more MH or mannequin+dressed) without boiling the ocean on 4–11.

**Priority (stop when quota tight; finish higher tiers first):**

| Tier | Outcome |
|------|---------|
| **S1 (must)** | Host ~40s authoritative male likeness + faithful ~30s sharp female likeness on **face/body**; fix or document **red hands** / bad skin textures; replace or improve **host hair** so he doesn’t read bald on banish shots. |
| **S2 (should)** | Apply **garment tints** (host sweater/jeans → charcoal/dark; faithful jumpsuit coherent with map)—via MetaHuman params, materials, or re-import if needed. |
| **S3 (nice)** | One additional table seat (2 or 3) with distinct silhouette from remaining Fab keepers; table in `BUILD-STATUS.md` for seats 4–11 (MH vs mannequin + outfit). |

**Done when:** `BUILD-STATUS.md` has **§ Sculpt & likeness** with before/after notes, cloud rig minutes (if any), `Saved/` hero screenshots (host standing + seat-1 seated), and explicit **deferrals**. Banish collapse still works on seat 1 (do not break Mannequin-compatible skeleton registration from session 1).

**Why:** Session 1 proved prod ceremony + `apply_fab_wardrobe.py` plumbing; remaining uncanny valley is **likeness, skin, hair distance-read, and tint params that came back empty**.

---

## Ground truth (read first)

- `BUILD-STATUS.md` § Production ceremony + § Host rework — host is **not** `SeatActors[0]`; seat 0 stays Manny contestant.
- `Content/TraitorSim/FAB-WARDROBE-MAP.md` — top 5 keepers, skips, current assignments (jumpsuit, sweater, jeans, chelsea boots, ponytail, buzzcut).
- `Content/Python/apply_fab_wardrobe.py` + `mh_build.py` — extend only if automation beats manual Creator; keep boot idempotent.
- **Already working:** `SK_Mannequin` compatible skeleton → `MM_Death_Front_01` on MH banish; `r.RayTracing=False` in `DefaultEngine.ini`; kill **CrashReportClient** after any crash before relying on MCP (port 8000).
- MetaHuman Creator plugin Python examples under project `Content/`; VaultCache `.mhpkg` pathing documented in wardrobe map.
- **No formal suit** in Fab library—host stays smart-casual (sweater/jeans), not black-tie.

---

## Boundaries

- No API/backend/Docker, no ceremony Blueprint redesign, no lip sync/mocap, no re-proving live `POST /api/games/run` P0.
- Do not seat host at the table or bind host to seat 0.
- Cloud rig: batch requests; note cost in close-out.

---

## Close-out

TLDR: S1/S2/S3 status, screenshot paths, cloud minutes, what Richard sees in one PIE banish on seat 1, and whether a **third** session is needed (only for seats 4–11 mass variety or castle lighting).

## COPY TO HERE ↑