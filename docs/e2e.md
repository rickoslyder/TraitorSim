# End-to-End Testing

Summary: user-facing changes need an executable path through the UI/backend. Agents must actually run the app or a faithful harness, capture failures, fix them, and record evidence. Do not substitute static review for runtime verification.

## Web UI E2E shape

Preferred local dev path:

```bash
cd traitorsim-ui
docker compose up --build
```

Then verify:

- backend `/health`
- games list loads from `reports/`
- timeline scrubber moves between days/phases
- POV selector hides traitor-only data in Faithful mode
- Game Runner flow works only when API keys/environment are present

## Evidence

For UI changes, capture at least one screenshot or browser-console check. Store local artifacts under `.agent-operability/reports/` unless a task specifies another location.

## Stop conditions

- Missing `.env`/API keys for Game Runner behavior.
- Docker service would conflict with live production deployment.
- Any command would deploy or restart production without explicit approval.
