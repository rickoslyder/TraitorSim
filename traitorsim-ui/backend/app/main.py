"""TraitorSim UI Backend - FastAPI Application

Serves game data from normalized SQLite database with auto-sync from
filesystem reports directory.
"""

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import games, analysis, runner, lobby, websocket as ws_router
from .db.database import init_db, sync_from_filesystem
from .cache import cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TraitorSim UI API",
    description="Backend API for the TraitorSim game analysis dashboard and live gameplay",
    version="0.3.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "https://traitorsim.rbnk.uk",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(games.router, prefix="/api/games", tags=["games"])
app.include_router(analysis.router, prefix="/api/games", tags=["analysis"])
app.include_router(runner.router, prefix="/api/games", tags=["runner"])
app.include_router(lobby.router, prefix="/api/lobby", tags=["lobby"])
app.include_router(ws_router.router, prefix="/ws", tags=["websocket"])


@app.on_event("startup")
async def startup():
    """Initialize database and sync from filesystem on startup."""
    logger.info("Starting TraitorSim UI API...")

    # Initialize database schema
    await init_db()

    # Auto-sync from reports directory
    reports_dir = Path(os.environ.get("REPORTS_DIR", "/app/reports"))
    if reports_dir.exists():
        logger.info(f"Auto-syncing from reports directory: {reports_dir}")
        imported = await sync_from_filesystem(reports_dir)
        if imported:
            logger.info(f"Imported {len(imported)} new games: {imported}")
        else:
            logger.info("No new games to import")
    else:
        logger.warning(f"Reports directory not found: {reports_dir}")

    logger.info("Startup complete")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Shutting down TraitorSim UI API...")
    cache.invalidate()


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "traitorsim-ui-api", "version": "0.2.0"}


@app.get("/health")
async def health():
    """Health check for container orchestration."""
    return {"status": "healthy"}


@app.get("/api/cache/stats")
async def cache_stats():
    """Get cache statistics for debugging."""
    return cache.stats()
