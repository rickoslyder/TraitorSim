"""SQLite database for storing normalized game data.

This module provides:
- Normalized schema for efficient queries
- Migration functions to import JSON game files
- Query helpers for games, players, events, and trust matrices
"""

import aiosqlite
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

DATABASE_PATH = Path(__file__).parent.parent.parent / "data" / "games.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def get_db() -> aiosqlite.Connection:
    """Get database connection with row factory enabled."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db(force_recreate: bool = False):
    """Initialize database with normalized schema.

    Args:
        force_recreate: If True, drops and recreates all tables
    """
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Check if tables exist
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='games'"
        )
        table_exists = await cursor.fetchone() is not None

        if force_recreate or not table_exists:
            logger.info("Initializing database schema...")

            # Read and execute schema
            if SCHEMA_PATH.exists():
                schema_sql = SCHEMA_PATH.read_text()
                await db.executescript(schema_sql)
            else:
                # Inline schema if file not found
                await _create_schema_inline(db)

            await db.commit()
            logger.info("Database schema initialized")
        else:
            logger.info("Database already initialized")


async def _create_schema_inline(db: aiosqlite.Connection):
    """Create schema inline if schema.sql not found."""
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS games (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_days INTEGER NOT NULL,
            prize_pot INTEGER DEFAULT 0,
            winner TEXT,
            rule_variant TEXT DEFAULT 'uk',
            source_file TEXT,
            raw_json TEXT
        );

        CREATE TABLE IF NOT EXISTS players (
            id TEXT NOT NULL,
            game_id TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            role TEXT,
            archetype_id TEXT,
            archetype_name TEXT,
            alive BOOLEAN DEFAULT TRUE,
            openness REAL,
            conscientiousness REAL,
            extraversion REAL,
            agreeableness REAL,
            neuroticism REAL,
            intellect REAL,
            dexterity REAL,
            composure REAL,
            social_influence REAL,
            PRIMARY KEY (id, game_id)
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
            type TEXT NOT NULL,
            day INTEGER NOT NULL,
            phase TEXT,
            actor_id TEXT,
            target_id TEXT,
            data JSON,
            narrative TEXT
        );

        CREATE TABLE IF NOT EXISTS trust_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            game_id TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
            day INTEGER NOT NULL,
            phase TEXT NOT NULL,
            observer_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            suspicion REAL NOT NULL,
            UNIQUE(game_id, day, phase, observer_id, target_id)
        );

        CREATE INDEX IF NOT EXISTS idx_games_created ON games(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_players_game ON players(game_id);
        CREATE INDEX IF NOT EXISTS idx_events_game_day ON events(game_id, day);
        CREATE INDEX IF NOT EXISTS idx_trust_game_day ON trust_snapshots(game_id, day, phase);
    """)


# =============================================================================
# Migration Functions
# =============================================================================

async def migrate_json_to_db(json_path: Path) -> str:
    """Import a game JSON file into normalized database tables.

    Args:
        json_path: Path to the JSON game file

    Returns:
        The game ID
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    game_id = json_path.stem

    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Check if game already exists
        cursor = await db.execute("SELECT id FROM games WHERE id = ?", (game_id,))
        if await cursor.fetchone():
            logger.info(f"Game {game_id} already exists, skipping")
            return game_id

        # Extract config
        config = data.get('config', {})

        # Insert game metadata
        await db.execute("""
            INSERT INTO games (
                id, name, created_at, total_days, prize_pot, winner, rule_variant,
                source_file, config_total_players, config_num_traitors, config_max_days,
                config_enable_recruitment, config_enable_shields, config_enable_death_list,
                config_tie_break_method, shield_holder, dagger_holder, seer_holder, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            game_id,
            data.get('name', game_id),
            datetime.now().isoformat(),
            data.get('total_days', data.get('day', 0)),
            data.get('prize_pot', 0),
            data.get('winner', 'UNKNOWN'),
            data.get('rule_variant', 'uk'),
            str(json_path),
            config.get('total_players'),
            config.get('num_traitors'),
            config.get('max_days'),
            config.get('enable_recruitment', True),
            config.get('enable_shields', True),
            config.get('enable_death_list', False),
            config.get('tie_break_method', 'revote'),
            data.get('shield_holder'),
            data.get('dagger_holder'),
            data.get('seer_holder'),
            json.dumps(data),  # Store raw JSON for backward compatibility
        ))

        # Insert players
        players = data.get('players', {})
        for pid, player in players.items():
            personality = player.get('personality', {})
            stats = player.get('stats', {})
            demographics = player.get('demographics', {})

            await db.execute("""
                INSERT INTO players (
                    id, game_id, name, role, archetype_id, archetype_name,
                    alive, eliminated_day, elimination_type, was_recruited,
                    backstory, strategic_profile,
                    demographics_age, demographics_location, demographics_occupation,
                    openness, conscientiousness, extraversion, agreeableness, neuroticism,
                    intellect, dexterity, composure, social_influence,
                    has_shield, has_dagger
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pid,
                game_id,
                player.get('name', pid),
                player.get('role'),
                player.get('archetype_id'),
                player.get('archetype_name'),
                player.get('alive', True),
                player.get('eliminated_day'),
                player.get('elimination_type'),
                player.get('was_recruited', False),
                player.get('backstory'),
                player.get('strategic_profile'),
                demographics.get('age'),
                demographics.get('location'),
                demographics.get('occupation'),
                personality.get('openness', 0.5),
                personality.get('conscientiousness', 0.5),
                personality.get('extraversion', 0.5),
                personality.get('agreeableness', 0.5),
                personality.get('neuroticism', 0.5),
                stats.get('intellect', 0.5),
                stats.get('dexterity', 0.5),
                stats.get('composure', 0.5),
                stats.get('social_influence', 0.5),
                player.get('has_shield', False),
                player.get('has_dagger', False),
            ))

        # Insert events
        events = data.get('events', [])
        for event in events:
            await db.execute("""
                INSERT INTO events (game_id, type, day, phase, actor_id, target_id, data, narrative)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                game_id,
                event.get('type'),
                event.get('day', 0),
                event.get('phase'),
                event.get('actor'),
                event.get('target'),
                json.dumps(event.get('data', {})),
                event.get('narrative'),
            ))

        # Insert trust snapshots (flattened)
        snapshots = data.get('trust_snapshots', [])
        for snapshot in snapshots:
            day = snapshot.get('day', 0)
            phase = snapshot.get('phase', '')
            alive_count = snapshot.get('alive_count')
            matrix = snapshot.get('matrix', {})

            for observer_id, targets in matrix.items():
                for target_id, suspicion in targets.items():
                    try:
                        await db.execute("""
                            INSERT OR REPLACE INTO trust_snapshots
                            (game_id, day, phase, alive_count, observer_id, target_id, suspicion)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (game_id, day, phase, alive_count, observer_id, target_id, suspicion))
                    except Exception as e:
                        logger.warning(f"Failed to insert trust snapshot: {e}")

        # Insert vote history
        vote_history = data.get('vote_history', [])
        for day_idx, votes in enumerate(vote_history, start=1):
            if isinstance(votes, dict):
                for voter_id, target_id in votes.items():
                    await db.execute("""
                        INSERT OR REPLACE INTO vote_history (game_id, day, voter_id, target_id)
                        VALUES (?, ?, ?, ?)
                    """, (game_id, day_idx, voter_id, target_id))

        # Insert breakfast order
        breakfast_history = data.get('breakfast_order_history', [])
        for day_idx, order in enumerate(breakfast_history, start=1):
            if isinstance(order, list):
                for position, player_id in enumerate(order):
                    await db.execute("""
                        INSERT OR REPLACE INTO breakfast_order (game_id, day, position, player_id)
                        VALUES (?, ?, ?, ?)
                    """, (game_id, day_idx, position, player_id))

        await db.commit()
        logger.info(f"Successfully imported game {game_id}")

    return game_id


async def sync_from_filesystem(reports_dir: Path) -> List[str]:
    """Scan reports directory and import any new games.

    Args:
        reports_dir: Path to the reports directory

    Returns:
        List of newly imported game IDs
    """
    imported = []

    if not reports_dir.exists():
        logger.warning(f"Reports directory does not exist: {reports_dir}")
        return imported

    for json_file in reports_dir.glob("*.json"):
        game_id = json_file.stem

        # Check if already imported
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT id FROM games WHERE id = ?", (game_id,))
            if await cursor.fetchone():
                continue

        try:
            await migrate_json_to_db(json_file)
            imported.append(game_id)
        except Exception as e:
            logger.error(f"Failed to import {json_file}: {e}")

    return imported


# =============================================================================
# Query Functions
# =============================================================================

async def list_games(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """List all games with pagination."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT id, name, created_at, total_days, prize_pot, winner, rule_variant,
                   config_total_players, config_num_traitors
            FROM games
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def count_games() -> int:
    """Get total count of games."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM games")
        row = await cursor.fetchone()
        return row[0] if row else 0


async def get_game(game_id: str) -> Optional[Dict[str, Any]]:
    """Get full game data by ID, reconstructed from normalized tables."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Get game metadata
        cursor = await db.execute("SELECT * FROM games WHERE id = ?", (game_id,))
        game_row = await cursor.fetchone()
        if not game_row:
            return None

        game = dict(game_row)

        # Get players
        cursor = await db.execute("SELECT * FROM players WHERE game_id = ?", (game_id,))
        player_rows = await cursor.fetchall()

        players = {}
        for row in player_rows:
            player = dict(row)
            pid = player.pop('id')
            player.pop('game_id')

            # Reconstruct nested structures
            players[pid] = {
                'id': pid,
                'name': player['name'],
                'role': player['role'],
                'archetype_id': player['archetype_id'],
                'archetype_name': player['archetype_name'],
                'alive': bool(player['alive']),
                'eliminated_day': player['eliminated_day'],
                'elimination_type': player['elimination_type'],
                'was_recruited': bool(player['was_recruited']),
                'backstory': player['backstory'],
                'strategic_profile': player['strategic_profile'],
                'has_shield': bool(player['has_shield']),
                'has_dagger': bool(player['has_dagger']),
                'personality': {
                    'openness': player['openness'],
                    'conscientiousness': player['conscientiousness'],
                    'extraversion': player['extraversion'],
                    'agreeableness': player['agreeableness'],
                    'neuroticism': player['neuroticism'],
                },
                'stats': {
                    'intellect': player['intellect'],
                    'dexterity': player['dexterity'],
                    'composure': player['composure'],
                    'social_influence': player['social_influence'],
                },
                'demographics': {
                    'age': player['demographics_age'],
                    'location': player['demographics_location'],
                    'occupation': player['demographics_occupation'],
                },
            }

        game['players'] = players

        # Get events
        cursor = await db.execute(
            "SELECT type, day, phase, actor_id as actor, target_id as target, data, narrative FROM events WHERE game_id = ? ORDER BY id",
            (game_id,)
        )
        event_rows = await cursor.fetchall()

        events = []
        for row in event_rows:
            event = dict(row)
            if event['data']:
                event['data'] = json.loads(event['data'])
            else:
                event['data'] = {}
            events.append(event)

        game['events'] = events

        # Get trust snapshots (reconstruct nested matrix structure)
        cursor = await db.execute("""
            SELECT DISTINCT day, phase, alive_count FROM trust_snapshots
            WHERE game_id = ? ORDER BY day, phase
        """, (game_id,))
        snapshot_keys = await cursor.fetchall()

        trust_snapshots = []
        for key in snapshot_keys:
            day, phase, alive_count = key

            cursor = await db.execute("""
                SELECT observer_id, target_id, suspicion FROM trust_snapshots
                WHERE game_id = ? AND day = ? AND phase = ?
            """, (game_id, day, phase))
            cells = await cursor.fetchall()

            matrix = {}
            for cell in cells:
                observer_id, target_id, suspicion = cell
                if observer_id not in matrix:
                    matrix[observer_id] = {}
                matrix[observer_id][target_id] = suspicion

            trust_snapshots.append({
                'day': day,
                'phase': phase,
                'alive_count': alive_count,
                'matrix': matrix,
            })

        game['trust_snapshots'] = trust_snapshots

        # Build config object
        game['config'] = {
            'total_players': game.pop('config_total_players', None),
            'num_traitors': game.pop('config_num_traitors', None),
            'max_days': game.pop('config_max_days', None),
            'enable_recruitment': game.pop('config_enable_recruitment', True),
            'enable_shields': game.pop('config_enable_shields', True),
            'enable_death_list': game.pop('config_enable_death_list', False),
            'tie_break_method': game.pop('config_tie_break_method', 'revote'),
        }

        # Remove raw_json from response (it's redundant now)
        game.pop('raw_json', None)
        game.pop('source_file', None)

        return game


async def get_trust_matrix(
    game_id: str,
    day: Optional[int] = None,
    phase: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Get trust matrix for a specific day/phase.

    Args:
        game_id: The game ID
        day: Day number (defaults to latest)
        phase: Phase name (defaults to 'roundtable')

    Returns:
        Dict with day, phase, and matrix, or None if not found
    """
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Find the closest snapshot
        if day is None:
            # Get latest day
            cursor = await db.execute(
                "SELECT MAX(day) FROM trust_snapshots WHERE game_id = ?",
                (game_id,)
            )
            row = await cursor.fetchone()
            day = row[0] if row and row[0] else 1

        if phase is None:
            phase = 'roundtable'

        # Get matrix cells
        cursor = await db.execute("""
            SELECT observer_id, target_id, suspicion, alive_count
            FROM trust_snapshots
            WHERE game_id = ? AND day = ? AND phase = ?
        """, (game_id, day, phase))

        rows = await cursor.fetchall()
        if not rows:
            # Try to find any snapshot for this day
            cursor = await db.execute("""
                SELECT observer_id, target_id, suspicion, alive_count, phase
                FROM trust_snapshots
                WHERE game_id = ? AND day = ?
                LIMIT 1
            """, (game_id, day))
            rows = await cursor.fetchall()
            if rows:
                phase = rows[0]['phase']
                cursor = await db.execute("""
                    SELECT observer_id, target_id, suspicion, alive_count
                    FROM trust_snapshots
                    WHERE game_id = ? AND day = ? AND phase = ?
                """, (game_id, day, phase))
                rows = await cursor.fetchall()

        if not rows:
            return None

        # Reconstruct matrix
        matrix = {}
        alive_count = None
        for row in rows:
            if row['observer_id'] not in matrix:
                matrix[row['observer_id']] = {}
            matrix[row['observer_id']][row['target_id']] = row['suspicion']
            alive_count = row['alive_count']

        return {
            'day': day,
            'phase': phase,
            'alive_count': alive_count,
            'matrix': matrix,
        }


async def get_events_by_type(
    game_id: str,
    event_type: str,
    day: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Get events of a specific type, optionally filtered by day."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        if day is not None:
            cursor = await db.execute("""
                SELECT type, day, phase, actor_id as actor, target_id as target, data, narrative
                FROM events
                WHERE game_id = ? AND type = ? AND day = ?
                ORDER BY id
            """, (game_id, event_type, day))
        else:
            cursor = await db.execute("""
                SELECT type, day, phase, actor_id as actor, target_id as target, data, narrative
                FROM events
                WHERE game_id = ? AND type = ?
                ORDER BY id
            """, (game_id, event_type))

        rows = await cursor.fetchall()

        events = []
        for row in rows:
            event = dict(row)
            if event['data']:
                event['data'] = json.loads(event['data'])
            else:
                event['data'] = {}
            events.append(event)

        return events


async def get_player(game_id: str, player_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific player from a game."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT * FROM players WHERE game_id = ? AND id = ?",
            (game_id, player_id)
        )
        row = await cursor.fetchone()

        if not row:
            return None

        player = dict(row)
        return {
            'id': player['id'],
            'name': player['name'],
            'role': player['role'],
            'archetype_id': player['archetype_id'],
            'archetype_name': player['archetype_name'],
            'alive': bool(player['alive']),
            'personality': {
                'openness': player['openness'],
                'conscientiousness': player['conscientiousness'],
                'extraversion': player['extraversion'],
                'agreeableness': player['agreeableness'],
                'neuroticism': player['neuroticism'],
            },
            'stats': {
                'intellect': player['intellect'],
                'dexterity': player['dexterity'],
                'composure': player['composure'],
                'social_influence': player['social_influence'],
            },
        }


async def delete_game(game_id: str) -> bool:
    """Delete a game and all related data (cascading)."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Enable foreign keys for cascade
        await db.execute("PRAGMA foreign_keys = ON")

        cursor = await db.execute("DELETE FROM games WHERE id = ?", (game_id,))
        await db.commit()

        return cursor.rowcount > 0
