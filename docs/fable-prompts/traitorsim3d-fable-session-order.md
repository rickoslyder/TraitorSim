# TraitorSim3D — Fable session order (2026-07-07)

**Each slice = new Claude Code chat.**  
`cd ~/Documents/Unreal\ Projects/TraitorSim3D` · `claude-fable-5` · effort `high`

## 1. Paste harness (every session)

From `claude-fable-5-cheatsheet.md` — at minimum:

```
When you have enough information to act, act. Do not re-derive facts already established in the conversation, re-litigate a decision the user has already made, or narrate options you will not pursue in user-facing messages. If you are weighing a choice, give a recommendation, not an exhaustive survey. This does not apply to thinking blocks.
```

```
Don't add features, refactor, or introduce abstractions beyond what the task requires. A bug fix doesn't need surrounding cleanup. Don't design for hypothetical future requirements. Only validate at system boundaries (user input, external APIs).
```

```
You are operating autonomously. The user cannot answer questions mid-task. For reversible actions that follow from the original request, proceed without asking. Before ending your turn, if your last paragraph is a plan or promise you have not executed, do that work now with tool calls.
```

## 2. Session prompts (copy body between markers)

| Order | File |
|-------|------|
| **1 Live PIE** | `docs/fable-prompts/traitorsim3d-live-projection-fable-5-session-prompt.md` → **COPY FROM HERE ↓** … **↑** |
| **2 Fab wardrobe** | `docs/fable-prompts/traitorsim3d-fab-metahuman-wardrobe-fable-5-session-prompt.md` |
| **3 Sculpt + scale** | `docs/fable-prompts/traitorsim3d-metahuman-sculpt-scale-fable-5-session-prompt.md` |

**Fab facts:** `docs/fable-prompts/traitorsim3d-fab-mac-verified.md`

**Live game id:** Ask Hermes on Telegram → paste into `BP_CeremonyDirector` `SessionId`.

## 3. Pull on Mac (if repo cloned)

```bash
cd ~/path/to/TraitorSim && git pull
# or copy from Hermes CT105: ~/.hermes/references/traitorsim3d-*.md
```

Hermes syncs copies to `dockerhost:~/projects/TraitorSim/docs/fable-prompts/` on request.