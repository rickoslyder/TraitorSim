# TraitorSim3D — Production ceremony (ONE Fable session)

**Quota:** Use this file only until P0+P1 done. Do **not** open legacy stepped prompts.

**Mac:** `cd ~/Documents/Unreal\ Projects/TraitorSim3D` · `claude-fable-5` · effort **`high`** (not `xhigh`).

---

## Paste 1 — harness (top of chat)

```
When you have enough information to act, act. Do not re-derive facts already established in the conversation, re-litigate a decision the user has already made, or narrate options you will not pursue in user-facing messages. If you are weighing a choice, give a recommendation, not an exhaustive survey. This does not apply to thinking blocks.

Don't add features, refactor, or introduce abstractions beyond what the task requires. A bug fix doesn't need surrounding cleanup. Don't design for hypothetical future requirements. Only validate at system boundaries (user input, external APIs).

You are operating autonomously. The user cannot answer questions mid-task. For reversible actions that follow from the original request, proceed without asking. Before ending your turn, if your last paragraph is a plan or promise you have not executed, do that work now with tool calls.
```

---

## Paste 2 — task (COPY FROM HERE ↓)

# TraitorSim3D — production ceremony + hero cast (single session)

## End goal

Richard can run **PIE** and see TraitorSim’s **production** sim drive the castle ceremony (phase + banish beats), with **contestant MetaHuman seat 1** and **presenter host** (`HostActor`, off-table) reading as a deliberate modern-UK dinner show—not greybox mannequins—**without** breaking what mock/static sessions already proved.

**Priority order (stop when quota/time is tight; do not expand scope upward until the prior tier is done):**

| Tier | Outcome |
|------|---------|
| **P0 (must)** | `BP_CeremonyDirector` polls `https://traitorsim.rbnk.uk/api/sessions/{SessionId}/projection/world`; PIE shows correct phase progression and at least one banish beat (hide/seat/camera/sting) using a **real** session id. If live sim timing is impossible in one sitting, prove the **same graph** on static ended session `game_20260706_215618` and document exactly how Richard triggers a **live** run with Hermes (`SessionId` on director + PIE while sim runs). |
| **P1 (should)** | **Seat 1** contestant (`MH_Faithful1`) gets visible Fab wardrobe/groom; **presenter** `HostActor` / `MH_Host` looks correct **standing** (not seated)—see `BUILD-STATUS.md` § Host rework. `Content/TraitorSim/FAB-WARDROBE-MAP.md` lists imports vs skipped (top 5 keepers). |
| **P2 (nice)** | MetaHuman banish uses a **visible** death/fall—not silent skip—on at least one MH seat, without redesigning ceremony logic. |

**Done when:** `BUILD-STATUS.md` has a dated **Production ceremony** section with: session id(s) used, P0 evidence (log path or `Saved/` screenshot), P1 status, P2 status or explicit deferral. Richard knows one sentence: “Press Play with SessionId = ___” and whether to Telegram Hermes for a fresh live game.

**Why:** Backend + projection API are live; UE already proved mock/static banish. Remaining risk is **prod wire + macOS PIE focus + cast read** on the two hero MetaHumans.

---

## Ground truth (read first; do not invent)

- `BUILD-STATUS.md`, `implementation-notes.md` — debounced phases, `SeatActors`, **seat 0 = contestant (Manny)**, **seat 1 = MH_Faithful1**, **`HostActor` presenter off-table** (phase show/hide on banish), host wide shot **removed** from seat-0 path.
- Projection v1 only: `phase`, `players[].seat_index|alive|display_name`, `day`. URL shape: `/api/sessions/{id}/projection/world`.
- Static ids: `game_20260706_215618` (10p ended), `game_20260706_210532` (6p ended). Live example: `game_20260706_233625` (may be ended—Hermes can start another on request).
- **Fab (verified Mac):** `docs/fable-prompts/traitorsim3d-fab-mac-verified.md` — **37** MetaHuman listings in Launcher library; project has `Content/Grooms/` + `MH_Host` (presenter, **not** `SeatActors[0]`) + `MH_Faithful1` (seat 1). Assets enter `Content/` only via **Add to project** (Launcher Fab or **Window → Fab**). No `Common/Fab` / `FabCache` paths.
- **Cast (UE, matches sim):** All `players[]` are **contestants** at seats 0–N. **Seat 0** = first contestant at the table (Manny). **Seat 1** = key faithful MH. **Host** = separate `HostActor` / standing `MH_Host` — never in `players[]`, never banished. No traitor/faithful costume coding in v1.
- `Content/Python/mh_build.py` for MH automation patterns.
- UE pitfalls: `docs/fable-prompts/` LEGACY files + skill `fable-ue-harness-lessons` in Hermes repo—**read only if blocked** (EditorToolset, Blueprint `create_node`, ghost assets, macOS timer throttle when editor unfocused).

---

## Boundaries

- **No** TraitorSim Python/API/Docker changes, no new projection fields, no packaging, no lip sync/mocap, no full castle relight, no seats 2–11 sculpt pass, no “import all 37 Fab items.”
- **No** numbered runbook in your head—pick tools (MCP, Editor, Fab UI, Python) that satisfy the tier table.
- Blueprint: durable nodes; no modal dialogs during PIE.

---

## Close-out (TLDR first)

Outcome per P0/P1/P2, screenshot paths, blockers, exact `SessionId` for Richard’s next Play, and whether a **second** Fable session is justified (only for sculpt scale 2–11 or full live timing rehearsal—not for redoing P0).

## COPY TO HERE ↑