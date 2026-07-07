# TraitorSim3D — Fable session order

**One new chat per slice.** `cd ~/Documents/Unreal\ Projects/TraitorSim3D` · `claude-fable-5` · effort `high`

## How to prompt Fable (not micro-steps)

Per [Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5):

| Do | Don’t |
|----|--------|
| **End state** + why + how we’ll know it’s done | Numbered runbooks (“step 1 curl, step 2…”) |
| **Constraints** (API contract, verified Fab facts, out of scope) | Prescriptive skill dumps in the first message |
| **Pointers** to repo truth (`BUILD-STATUS.md`, `traitorsim3d-fab-mac-verified.md`) | Re-derive architecture Fable can read |
| Short **harness** (autonomous, YAGNI, anti-overplanning) | Ask mid-task unless destructive |

Older slice files (greybox, BP polling, dressing) were written when we were **de-risking** unknown MCP/UE pitfalls — keep them as **archives** if a regression needs a checklist. **Next slices** use goal prompts below.

## Harness (paste once per chat)

```
When you have enough information to act, act. Do not re-derive facts already established in the conversation, re-litigate a decision the user has already made, or narrate options you will not pursue in user-facing messages. If you are weighing a choice, give a recommendation, not an exhaustive survey. This does not apply to thinking blocks.

Don't add features, refactor, or introduce abstractions beyond what the task requires. A bug fix doesn't need surrounding cleanup. Don't design for hypothetical future requirements. Only validate at system boundaries (user input, external APIs).

You are operating autonomously. The user cannot answer questions mid-task. For reversible actions that follow from the original request, proceed without asking. Before ending your turn, if your last paragraph is a plan or promise you have not executed, do that work now with tool calls.
```

## Goal prompts (copy `COPY FROM HERE` block only)

| Order | File |
|-------|------|
| 1 Live prod wire | `traitorsim3d-live-projection-fable-5-session-prompt.md` |
| 2 Fab wardrobe | `traitorsim3d-fab-metahuman-wardrobe-fable-5-session-prompt.md` |
| 3 Sculpt + scale | `traitorsim3d-metahuman-sculpt-scale-fable-5-session-prompt.md` |

**Fab facts:** `traitorsim3d-fab-mac-verified.md`  
**Live `SessionId`:** Telegram Hermes → `BP_CeremonyDirector`

**Paths:** `~/Documents/Unreal Projects/TraitorSim3D/docs/fable-prompts/` · Git `TraitorSim/docs/fable-prompts/`