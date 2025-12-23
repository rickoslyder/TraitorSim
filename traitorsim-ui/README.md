# TraitorSim Web UI

Interactive dashboard for analyzing TraitorSim game sessions.

**Live at:** https://traitorsim.rbnk.uk

## Features

- **Trust Network Graph**: Force-directed D3.js visualization of player suspicion relationships
- **Player Cards**: OCEAN personality traits, archetypes, behavioral stats, and status tracking
- **Timeline Scrubber**: Navigate through game days and phases with animated trust transitions
- **Voting Heatmap**: Matrix visualization of voting patterns and traitor-voter detection
- **Event Feed**: Chronological event stream with POV-aware filtering
- **Analysis Tab**: Breakfast order suspicion analysis, mission performance breakdown
- **Story Mode**: Scrollytelling narrative recap of entire game

### POV System

Toggle between viewing modes to experience the game from different perspectives:

| Mode | Description |
|------|-------------|
| **Omniscient** | See all roles, all events, full trust matrix |
| **Faithful** | No role reveals, traitor-only events hidden (spoiler-free) |
| **Traitor** | See traitor identities only, useful for traitor strategy analysis |

## Quick Start

### Production Deployment

```bash
# Build and deploy
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Check status
docker ps --filter "name=traitorsim-ui"

# View logs
docker logs traitorsim-ui-frontend-1 --tail 50
docker logs traitorsim-ui-backend-1 --tail 50
```

Production serves on **port 8085** via nginx, which proxies `/api/*` to the backend.

### Development (with Docker)

```bash
docker compose up --build
```

Open http://localhost:5173 (hot reload enabled)

### Development (without Docker)

1. **Backend** (Python 3.11+):
```bash
cd backend
pip install -r requirements.txt
REPORTS_DIR=../../reports uvicorn app.main:app --reload
```

2. **Frontend** (Node 20+):
```bash
cd frontend
npm install
npm run dev
```

3. Open http://localhost:5173

## Usage

1. Games auto-load from the `reports/` directory on startup
2. Select a game from the sidebar dropdown
3. Use the timeline scrubber to navigate through days/phases
4. Switch views: Trust Network, Players, Voting, Events, Analysis, Story
5. Use the POV selector to toggle role visibility
6. Click players to highlight their connections across all views

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/games` | GET | List all games |
| `/api/games/{id}` | GET | Get full game data with trust matrices |
| `/api/games/sync` | POST | Re-import games from reports directory |
| `/api/games/refresh` | POST | Force re-sync and clear cache |
| `/api/games/{id}/trust-matrix` | GET | Get trust matrix at specific day/phase |
| `/api/games/{id}/events` | GET | Get filtered events |
| `/api/games/{id}/voting-patterns` | GET | Get voting analysis |
| `/health` | GET | Backend health check |

## Tech Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Zustand
- **Visualization**: react-force-graph-2d (D3.js), Recharts, Framer Motion
- **Backend**: FastAPI, SQLite, Pydantic
- **Deployment**: Docker, nginx (production reverse proxy)

## Project Structure

```
traitorsim-ui/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/          # Sidebar, POVSelector
│   │   │   ├── players/         # PlayerCard, PlayerGrid
│   │   │   ├── trust-network/   # TrustGraph (D3 force-directed)
│   │   │   ├── timeline/        # TimelineScrubber, PlaybackControls
│   │   │   ├── voting/          # VoteFlow, voting heatmap
│   │   │   ├── events/          # EventFeed with POV filtering
│   │   │   ├── analysis/        # BreakfastOrderChart, MissionBreakdown
│   │   │   └── recap/           # DayRecap, ScrollytellingView
│   │   ├── stores/
│   │   │   └── gameStore.ts     # Zustand state (game, timeline, POV)
│   │   ├── hooks/
│   │   │   ├── usePOVVisibility.ts  # POV-aware content filtering
│   │   │   ├── useContainerSize.ts  # Responsive sizing
│   │   │   └── useTrustAnimation.ts # Smooth trust transitions
│   │   ├── types/
│   │   │   └── game.ts          # TypeScript interfaces
│   │   └── api/
│   │       └── client.ts        # API client (relative URLs)
│   ├── Dockerfile               # Development (npm run dev)
│   ├── Dockerfile.prod          # Production (Node build → nginx)
│   └── nginx.conf               # Production reverse proxy config
├── backend/
│   └── app/
│       ├── main.py              # FastAPI app, CORS, startup sync
│       ├── routers/
│       │   ├── games.py         # Game CRUD endpoints
│       │   ├── analysis.py      # Trust evolution, voting patterns
│       │   └── runner.py        # Game execution (WIP)
│       ├── db/
│       │   ├── database.py      # SQLite + filesystem sync
│       │   └── schema.sql       # Normalized database schema
│       └── cache.py             # Response caching
├── docker-compose.yml           # Development environment
└── docker-compose.prod.yml      # Production environment (port 8085)
```

## Key Components

### State Management (gameStore.ts)

```typescript
interface GameStore {
  // Current game
  currentGame: GameSession | null;
  games: GameSummary[];

  // Timeline navigation
  currentDay: number;
  currentPhase: Phase;

  // POV system
  viewingMode: 'omniscient' | 'faithful' | 'traitor';
  povPlayerId: string | null;

  // UI state
  selectedPlayerId: string | null;
  hoveredPlayerId: string | null;
  showRoles: boolean;
  showEliminatedPlayers: boolean;
  trustThreshold: number;
}
```

### POV Visibility Hook (usePOVVisibility.ts)

```typescript
const {
  shouldShowRole,      // (player) => boolean
  shouldRevealTraitor, // (player) => boolean
  filterVisibleEvents, // (events) => filtered events
  getVisibleTrust,     // (matrix) => filtered matrix
  isSpoilerFree,       // true in faithful mode
} = usePOVVisibility(players);
```

## Troubleshooting

### Games not appearing
```bash
# Check reports are mounted
docker exec traitorsim-ui-backend-1 ls /app/reports

# Force re-sync
curl -X POST http://localhost:8085/api/games/refresh
```

### Port already in use
```bash
sudo lsof -ti:8085 | xargs -r kill -9
docker compose -f docker-compose.prod.yml up -d
```

### CORS errors
Add your domain to `backend/app/main.py` origins list:
```python
origins = [
    "http://localhost:5173",
    "https://traitorsim.rbnk.uk",
    # Add new origins here
]
```
