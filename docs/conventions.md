# Coding Conventions

Summary: project-specific coding rules for TraitorSim. Follow existing patterns first; avoid new abstractions unless they remove real duplication. Keep runtime simulation logic deterministic where possible and UI changes visually verified.

## Python / simulation core

- Keep game-rule enforcement in `src/traitorsim/core/`; do not bury rules in agents or UI.
- Treat agent/model output as untrusted input; validate before mutating game state.
- Preserve regional rule variants and document new variants in existing architecture docs.
- Prefer typed dataclasses/Pydantic-style boundary models over ad-hoc dictionaries for new interfaces.
- Add regression tests for bug fixes in `tests/`.
- Do not start direct multi-agent execution from tests or validation commands.

## Web UI

- Frontend code lives in `traitorsim-ui/frontend` and uses React + TypeScript + Vite.
- API calls should use relative `/api/*` URLs so nginx can proxy in production.
- For new user-facing states, include loading/error/empty behavior.
- Verify UI changes with a build or typecheck when dependencies are installed; use screenshots for visual/layout changes.

## Docs and operations

- `CLAUDE.md` remains the detailed project constitution.
- `AGENTS.md` is only the router.
- Update the most specific doc when discovering a durable repo fact.
- Deployment and full game simulations require explicit approval.
- Never commit or print `.env` secrets.
