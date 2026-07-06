# Deploy — World projection API shim (v1)

Deploys `GET /api/sessions/{session_id}/projection/world` to **traitorsim.rbnk.uk**.

## What ships

- `src/traitorsim/events/` (schemas, bus, projection builders)
- `game_engine_async.py` event hooks (outcome-safe)
- `traitorsim-ui/backend/app/routers/projection.py`
- `API-CONTRACT.md`, `tests/test_world_projection.py`

## Preconditions

- Changes committed on Dockerhost: `/home/rkb/projects/TraitorSim`
- `pytest tests/ -q` green (125+ tests)

## 1. Rebuild image

The production container runs **uvicorn from the image** (`traitorsim-ui:latest`), not live-mounted `app/`. Rebuild after backend/router changes:

```bash
cd /home/rkb/projects/TraitorSim/traitorsim-ui
docker build -f backend/Dockerfile -t traitorsim-ui-backend:shim backend/   # if split build
# OR your existing prod build that produces traitorsim-ui:latest — e.g.:
docker compose -f docker-compose.prod.yml build
docker tag <built-image-id> traitorsim-ui:latest
```

Use whatever command you normally use to refresh `traitorsim-ui:latest` (confirm with `docker images traitorsim-ui`).

## 2. Production compose (`/srv/dockerdata/traitorsim/docker-compose.yml`)

Ensure the **traitorsim** service has:

```yaml
environment:
  - REPORTS_DIR=/app/reports
  - PYTHONPATH=/app/traitorsim:/app
  - SESSIONS_DIR=/app/traitorsim/data/sessions
volumes:
  - /home/rkb/projects/TraitorSim/data/reports:/app/reports
  - /home/rkb/projects/TraitorSim:/app/traitorsim:ro
  - /home/rkb/projects/TraitorSim/data/sessions:/app/traitorsim/data/sessions
```

- **Reports** → projection from completed games (required).
- **Sessions** → live `world_snapshot.json` from `GameEngineAsync` runs (optional but recommended).

Apply the patch file `deploy/srv-traitorsim-compose-shim.patch` or edit by hand, then:

```bash
cd /srv/dockerdata/traitorsim
docker compose up -d --force-recreate traitorsim
```

## 3. Smoke tests

```bash
# Replace with a real report stem under data/reports/
curl -sS "https://traitorsim.rbnk.uk/api/sessions/game_20260104_012251/projection/world" | jq .
curl -sS -o /dev/null -w "%{http_code}\n" "https://traitorsim.rbnk.uk/api/sessions/nonexistent_session/projection/world"  # expect 404
```

## 4. Not in this deploy

- **Containerized engine** EventBus wiring (`game_engine_containerized.py`) — follow-up; reports path still works.
- **Arena** router — separate commit if not included in image build.

## Rollback

```bash
cd /srv/dockerdata/traitorsim
docker compose pull   # if previous image tagged remotely
# or retag previous local image
docker compose up -d --force-recreate traitorsim
```