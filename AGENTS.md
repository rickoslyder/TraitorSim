# Agent Router — TraitorSim

This file routes coding agents to the right context. Keep this short; durable detail lives in linked docs.

## Start here

1. Read `CLAUDE.md` for the project constitution, architecture, and deployment caveats.
2. Read `docs/agent-workflow.md` for the agent loop.
3. Read `docs/commands.md` before running checks or starting services.
4. Read `docs/conventions.md` before editing code.
5. Read `docs/testing.md` before changing behavior.
6. Read `docs/review.md` before marking code complete.
7. For user-facing UI changes, read `docs/e2e.md` and `docs/visual-regression.md`.
8. Use `.agent-operability/task-queue.json` and `.agent-operability/worksheets/` for resumable multi-step work.
9. Before handoff, run fresh validation and record evidence with:

```bash
python /home/hermes/repos/agent-operability-kit/bin/aok_validate.py .
python /home/hermes/repos/agent-operability-kit/bin/aok_eos.py . --apply
```

## Project-specific hard boundaries

- **Do not run `python -m src.traitorsim` directly.** It can spawn 22+ Claude Agent SDK instances in one process and exhaust resources. Use documented Docker-in-Docker / containerized paths only when explicitly asked.
- Do not deploy to `traitorsim.rbnk.uk` without explicit approval.
- Do not touch `.env` or print secrets.
- Do not overwrite existing docs/files with `--force` unless explicitly approved.
- Existing uncommitted work may be present; check `git status` before editing and do not clobber unrelated changes.

## Useful kit commands

```bash
python /home/hermes/repos/agent-operability-kit/bin/aok_queue.py --root . list
python /home/hermes/repos/agent-operability-kit/bin/aok_worksheet.py --root . validate
python /home/hermes/repos/agent-operability-kit/bin/aok_test_audit.py .
python /home/hermes/repos/agent-operability-kit/bin/aok_review.py . --diff
```
