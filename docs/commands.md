# Commands

Summary: source of truth for local development commands. Run from repo root unless a command says otherwise. Do not start the full simulation unless explicitly asked; use safe tests/checks for routine validation.

## Setup

Python package/dev tools:

```bash
python -m pip install -e ".[dev]"
```

Web UI frontend:

```bash
npm --prefix traitorsim-ui/frontend ci
```

Web UI backend:

```bash
python -m pip install -r traitorsim-ui/backend/requirements.txt
```

## Safe checks

These are safe on Hermes and do not start the 24-agent simulation.

| Purpose | Command | Configured in `agent-operability.toml` |
|---|---|---|
| Agent kit validation | `python /home/hermes/repos/agent-operability-kit/bin/aok_validate.py .` | n/a |
| Python tests | `python -m pytest tests -q` | `commands.unit` |
| False-confidence audit | `python /home/hermes/repos/agent-operability-kit/bin/aok_test_audit.py .` | manual |

## Optional checks after dependencies are installed

Keep these documented but do not assume the environment already has the dependencies.

```bash
python -m black --check src tests
python -m ruff check src tests
python -m mypy src
npm --prefix traitorsim-ui/frontend run typecheck
npm --prefix traitorsim-ui/frontend run lint
npm --prefix traitorsim-ui/frontend run build
npm --prefix traitorsim-ui/frontend run test -- --run
```

## Web UI development

Docker dev mode:

```bash
cd traitorsim-ui
docker compose up --build
```

No-Docker split mode:

```bash
# Backend
cd traitorsim-ui/backend
REPORTS_DIR=../../reports uvicorn app.main:app --reload

# Frontend
cd traitorsim-ui/frontend
npm run dev
```

## Production deployment — approval required

Do not run these without explicit approval:

```bash
cd traitorsim-ui
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

## Full game simulation — approval required

Do **not** run `python -m src.traitorsim` directly. It can exhaust resources by spawning many agents in one process.

Approved execution modes, when explicitly requested:

```bash
./run.sh
# or
docker compose -f docker-compose.yml build
docker compose -f docker-compose.yml up --abort-on-container-exit
docker compose -f docker-compose.yml down -v
```
