# Testing

Summary: tests should prove behavior, not mocks. Use Python tests for simulation/game-rule behavior and frontend tests/typechecks for UI behavior. Do not start full multi-agent simulation as part of routine validation.

## Python tests

Safe default:

```bash
python -m pytest tests -q
```

Focused examples:

```bash
python -m pytest tests/test_game_state.py -q
python -m pytest tests/test_voting.py -q
python -m pytest tests/test_missions.py -q
```

## Frontend checks

After `npm --prefix traitorsim-ui/frontend ci`:

```bash
npm --prefix traitorsim-ui/frontend run typecheck
npm --prefix traitorsim-ui/frontend run lint
npm --prefix traitorsim-ui/frontend run build
npm --prefix traitorsim-ui/frontend run test -- --run
```

## False-confidence red flags

- Tests with no assertions.
- Tests that only check HTTP 200 or component existence.
- Heavy mocks of game state or model output with no behavioral assertion.
- Skipped/xfailed tests near changed code.
- Production code changed without relevant test or explicit reason.
- Snapshot or visual updates without a semantic assertion.

Run:

```bash
python /home/hermes/repos/agent-operability-kit/bin/aok_test_audit.py .
```
