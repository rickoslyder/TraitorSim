# Agent Workflow

Summary: canonical loop for agents in this repo. Inspect before editing. Keep a worksheet for resumability. Run targeted checks as you go and fresh full validation before handoff. Update docs when you learn durable repo facts. Stop on ambiguity, destructive actions, missing credentials, or validation failure.

## Loop

1. Orient — read `AGENTS.md`, `docs/commands.md`, relevant docs/source/tests.
2. Claim or create a task — use `.agent-operability/task-queue.json` or the configured tracker.
3. Open a worksheet — every multi-step task gets `.agent-operability/worksheets/<task-id>.md`.
4. Plan a tracer bullet — one behavior slice, not a horizontal rewrite.
5. Implement with evidence — run focused tests after each meaningful change.
6. Review — use `docs/review.md`; cross-agent review if configured.
7. Validate fresh — run `aok_eos.py . --apply` or the project equivalent.
8. Handoff — summarize files touched, evidence, risks, and next tasks.

## Stop conditions

- Requirements conflict with existing code/docs and no precedent exists.
- A command would destroy data, rewrite history, deploy, send, or spend money.
- Required credentials are missing.
- Full validation fails and root cause is unknown.
- You cannot produce fresh evidence for a claim.
