# TraitorSim3D — Fable 5 session prompt (standalone)

**Use with:** Claude Code / Claude on **rkb-mac**, model **`claude-fable-5`**, effort **`high`** ( **`xhigh`** only if stuck on architecture).

**Companion Hermes assets (load or attach — do not duplicate their full text here):**

| Asset | Path on Hermes CT105 | Role |
|-------|----------------------|------|
| Fable harness blocks | `~/.hermes/references/claude-fable-5-cheatsheet.md` | Routing, paste blocks, effort |
| Unknowns / map vs territory | Skill **`unknowns-pass`** | Optional **Mode A** blind-spot or **Known unknowns** pass before building |
| UE + TraitorSim split | Skill **`unreal-engine-mcp`** + `references/traitorsim-ue-split.md` | Host placement, MCP serial rules, architecture A |
| Lore / mechanics (read if reachable) | Dockerhost `/home/rkb/projects/TraitorSim/WORLD_BIBLE.md` | Castle, phases, show format |

**How to start a session**

1. Paste **everything below the line** as the user message (or save this file into the Claude project).
2. Ensure **Unreal Editor** is open on **TraitorSim3D**, **Unreal MCP** auto-started at `http://127.0.0.1:8000/mcp`.
3. If Hermes on CT105 drives via tunnel: reverse SSH `-R 127.0.0.1:8000:127.0.0.1:8000` to `hermes@100.90.163.20` must be up **before** remote MCP tests.

---

## COPY FROM HERE ↓

# TraitorSim3D — Unreal Engine 5.8 build (Fable 5 session)

## Why this exists (read this first)

I'm building a **3D visualization / playable slice** for **TraitorSim** — a high-fidelity AI simulation of the TV social-deduction game *The Traitors* (not a shooter, not a generic action game). The **source of truth** for game logic stays a **Python dual-SDK sim** (Gemini game master + Claude player agents) deployed on my homelab; **Unreal is the client layer** (spaces, ceremony beats, character presence, cameras). Success means a **credible Scottish-castle social space** with a **round-table focal point** and hooks for later API-driven state — not a full rewrite of the sim in Blueprint.

**Effort:** use **`high`** by default; **`xhigh`** only for hard layout/lighting/Blueprint architecture decisions. Do **not** burn effort re-deriving facts already stated here.

---

## Fable harness rules (non-negotiable)

When you have enough information to act, **act**. Do not re-litigate decisions, narrate options you won't pursue, or end turns on plans you haven't executed.

**Do not** ask "Shall I…?" mid-task for reversible steps that follow from this brief. Pause only for: destructive/irreversible edits, real scope changes, or input only I can provide.

**Lead with outcomes** in messages to me: first sentence = what happened / what you found; detail after. No essay status reports — ground claims in **tool/editor evidence**.

**Boundaries:** assess and build what's asked; **no** mass refactors, bonus features, or "while I'm here" cleanup. Bug-level fixes only when they block the stated deliverables.

**Do not** ask me to "show your reasoning" or echo chain-of-thought in chat (classifier risk). Use tools; report results.

**Parallel work:** if your environment supports subagents, delegate research/asset lists in parallel; **Unreal MCP calls must be serial** (one at a time — Epic runs on the game thread).

**Memory:** append durable lessons to `TraitorSim3D/implementation-notes.md` when you discover engine/MCP quirks; one lesson per entry.

**Unknowns (first 10 minutes):** run a short **known-unknowns** pass (see Hermes skill `unknowns-pass`): list gaps, pick sensible *Traitors*-show defaults, log assumptions in `implementation-notes.md`. Do **not** block the whole session on my replies unless scope would change irreversibly.

---

## Environment (territory — do not guess)

| Item | Value |
|------|--------|
| Machine | MacBook Pro **M4 Max**, **128 GB** RAM |
| Project path | `/Users/rkb/Documents/Unreal Projects/TraitorSim3D` |
| Template | **Games → Third Person**, **Blueprint**, Desktop, **Maximum** quality |
| UE version | **5.8+** |
| Unreal MCP | Plugin enabled; **Auto Start Server**; default **`http://127.0.0.1:8000/mcp`** |
| MCP constraint | **Experimental**; **serial** tool execution; editor must stay open |
| Live sim (reference) | `https://traitorsim.rbnk.uk` — Python sim + web dashboard on Dockerhost |
| Sim repo (lore/mechanics) | Dockerhost: `/home/rkb/projects/TraitorSim/` — `WORLD_BIBLE.md`, `ARCHITECTURE.md`, `README.md` |
| Architecture | **A — UE viewer**: Python sim authoritative; UE displays state (poll/subscribe later) |

**What TraitorSim is *not*:** FPS combat loop, live-service MMO, or replacing Python agent orchestration in v1.

**What it *is* for this sprint:** spatial staging for **Breakfast → Mission → Social → Round Table → Turret** phases (minimum deliverable: **Round Table + castle-adjacent social space** greybox).

---

## Negative prompts (do NOT)

- Do **not** pivot to First Person or combat-heavy template gameplay as the core loop.
- Do **not** implement full AI/agent logic in UE (no Gemini/Claude SDK in C++/Blueprint for this pass).
- Do **not** issue **overlapping** Unreal MCP requests.
- Do **not** delete or rename the `.uproject` / migrate project location without explicit approval.
- Do **not** enable experimental rendering that breaks Mac SM6 without checking **macOS 15+** and project SM6 settings.
- Do **not** commit secrets, API keys, or Epic credentials anywhere.
- Do **not** over-build Nanite hero environments before **round-table scale** reads correctly (~10–12 figures).
- Do **not** stop after a plan — ship **visible editor state** per deliverables below.

---

## Mission objectives (outcomes)

### Phase 0 — Prove the harness
- Confirm editor opens **TraitorSim3D** and MCP responds at `http://127.0.0.1:8000/mcp`.
- Document MCP URL/port if different from default.

### Phase 1 — Greybox "Castle Court"
- Level **`L_CastleCourt`**: stone hall at human scale; central **round table** zone (~10–12 seats); sightlines from third-person spawn to table center; simple **Lumen-friendly** lighting (fallback if unstable on Mac).
- Placeholder characters/mannequins for crowd scale.

### Phase 2 — Ceremony beat
- **PlayerStart** + navigable path to table.
- **`LS_RoundTable_Wide`** framing table + seats.
- Optional **`BP_CeremonyDirector`** with stub `OnPhaseChanged(PhaseName)` — no backend yet.

### Phase 3 — Integration stub
- `Content/TraitorSim/README-integration.md`: proposed JSON session shape, placeholder API `https://traitorsim.rbnk.uk/api/...`, how `BP_CeremonyDirector` would consume it later.

### Phase 4 — Handoff
- **`BUILD-STATUS.md`** at project root: what exists, stubbed items, how to open demo view, known issues, next 3 tasks.
- Project opens without critical errors on this machine.

---

## Quality bar

- PIE: spawn → table without stuck geometry.
- Table fits **10+** placeholders without clipping.
- Interior readability at table (no final art required).
- Docs terse, technical, plain English.

---

## Verification (run; report pass/fail)

1. MCP initialize succeeds locally.
2. PIE path spawn → table works.
3. `LS_RoundTable_Wide` plays and frames the table.
4. No critical errors on cold open (Output Log).
5. `BUILD-STATUS.md` matches actual level/asset names.

---

## If blocked

| Blocker | Action |
|---------|--------|
| MCP connection reset | Fix local MCP (`Auto Start Server`, plugin restart, `ModelContextProtocol.StartServer`); one serial retry. |
| Mac rendering crash | Reduce quality; try Lumen off; log in `implementation-notes.md`. |
| Cannot read `WORLD_BIBLE.md` | Mark lore **assumed** in notes; do not invent contradictory rules. |
| No Unreal MCP tools | Stop; report client/harness — do not fake editor actions. |

---

## Start

Begin **Phase 0** → through **Phase 4** or a hard blocker. When done or blocked: **TL;DR ≤8 sentences** + paste **`BUILD-STATUS.md`**.

## COPY UNTIL HERE ↑

---

## File metadata

- **Created:** 2026-07-06 (Hermes CT105)
- **Skill owner:** `unreal-engine-mcp` (devops)
- **Cheatsheet:** `claude-fable-5-cheatsheet.md`