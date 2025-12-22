# TraitorSim Web UI

Interactive dashboard for analyzing TraitorSim game sessions.

## Features

- **Trust Network Graph**: Force-directed visualization of player suspicion relationships
- **Player Cards**: OCEAN personality traits, archetypes, and status tracking
- **Timeline Scrubber**: Navigate through game days and phases
- **Voting Heatmap**: Matrix visualization of voting patterns
- **Event Feed**: Chronological event stream with filtering

## Quick Start

### Development (without Docker)

1. **Backend** (Python 3.11+):
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

2. **Frontend** (Node 18+):
```bash
cd frontend
npm install
npm run dev
```

3. Open http://localhost:5173

### Development (with Docker)

```bash
docker-compose up --build
```

Open http://localhost:5173

## Usage

1. Click "Upload Game" to load a TraitorSim game JSON file
2. Use the timeline to navigate through days/phases
3. Switch between views: Trust Network, Players, Voting, Events
4. Toggle "Show Roles" to reveal true player roles
5. Click players to highlight their connections

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/games` | GET | List all games |
| `/api/games/{id}` | GET | Get full game data |
| `/api/games/upload` | POST | Upload game JSON |
| `/api/games/{id}/trust-matrix` | GET | Get trust matrix |
| `/api/games/{id}/events` | GET | Get filtered events |

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, D3.js, Zustand
- **Backend**: FastAPI, SQLite, Pydantic
- **Visualization**: react-force-graph-2d, Recharts, Framer Motion

## Project Structure

```
traitorsim-ui/
├── frontend/
│   └── src/
│       ├── components/     # React components
│       ├── stores/         # Zustand state
│       ├── types/          # TypeScript types
│       └── api/            # API client
├── backend/
│   └── app/
│       ├── routers/        # API endpoints
│       ├── services/       # Business logic
│       └── db/             # Database
└── docker-compose.yml
```
