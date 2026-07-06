# TraitorSim — Live PIE coordination (Hermes ↔ Mac)

Hermes on CT105 can start a prod game and give Richard the **exact** `SessionId` for `BP_CeremonyDirector`.

## Start game (Dockerhost / public)

```bash
curl -sS -X POST https://traitorsim.rbnk.uk/api/games/run \
  -H 'Content-Type: application/json' \
  -d '{"num_players":6,"num_traitors":1}'
# → game_id in JSON — use as SessionId in UE
```

## Poll status

```bash
curl -sS https://traitorsim.rbnk.uk/api/games/run/status
```

## Projection (UE poll URL)

```bash
curl -sS "https://traitorsim.rbnk.uk/api/sessions/<game_id>/projection/world" | jq .
```

## Static regression session (ended, no live sim)

| SessionId | Notes |
|-----------|--------|
| `game_20260706_210532` | 6 players, 1 banished, `phase=ended` |
| `game_20260706_215618` | 10 players, 8 banished, full run |

## Session id fix (2026-07-06)

Runner pre-assigns `game_YYYYMMDD_HHMMSS` and passes `TRAITORSIM_SESSION_ID` into the sim subprocess so API id matches `data/sessions/{id}/`.

## Fable prompt order (next)

1. **Live wire** — `traitorsim3d-live-projection-fable-5-session-prompt.md`
2. **Fab wardrobe** — `traitorsim3d-fab-metahuman-wardrobe-fable-5-session-prompt.md`
3. **Sculpt + scale** — `traitorsim3d-metahuman-sculpt-scale-fable-5-session-prompt.md`

Fresh Claude Code chat each. CWD: `~/Documents/Unreal Projects/TraitorSim3D`.