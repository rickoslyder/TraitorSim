# Castle broadcast — 2D ↔ UE integration

The **web dashboard** and **TraitorSim3D** share one contract: `GET /api/sessions/{session_id}/projection/world` ([API-CONTRACT.md](../../API-CONTRACT.md)).

## Operator flow

1. Open **traitorsim.rbnk.uk** → **Game Runner** → Start game (or use historical `game_YYYYMMDD_HHMMSS`).
2. Copy **session id** from the **Castle broadcast** panel.
3. On Mac UE: set `SessionId` on `BP_CeremonyDirector`, `BaseUrl` = `https://traitorsim.rbnk.uk`, PIE.
4. Web panel polls the same projection every 3s while a run is active (phase, pot, alive names + roles v1 omniscient).

## UI code

- `traitorsim-ui/frontend/src/components/broadcast/CastleBroadcastPanel.tsx`
- `traitorsim-ui/frontend/src/types/projection.ts`
- `useWorldProjection` in `api/hooks.ts`

## UE backlog (session 5 Fable)

Nameplates, HUD, audio, banish reveal, turret staging — `docs/fable-prompts/traitorsim3d-broadcast-presentation-fable-5-session-prompt.md` on Mac.