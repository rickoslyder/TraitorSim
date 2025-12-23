-- TraitorSim UI Database Schema
-- Normalized tables for efficient game data queries

-- Drop existing tables if migrating
DROP TABLE IF EXISTS trust_snapshots;
DROP TABLE IF EXISTS events;
DROP TABLE IF EXISTS players;
DROP TABLE IF EXISTS games;

-- games table (metadata only)
CREATE TABLE games (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_days INTEGER NOT NULL,
    prize_pot INTEGER DEFAULT 0,
    winner TEXT DEFAULT 'UNKNOWN' CHECK(winner IN ('FAITHFUL', 'TRAITORS', 'UNKNOWN', '')),
    rule_variant TEXT DEFAULT 'uk',
    source_file TEXT,  -- Original JSON path for reference
    -- Config fields
    config_total_players INTEGER,
    config_num_traitors INTEGER,
    config_max_days INTEGER,
    config_enable_recruitment BOOLEAN DEFAULT TRUE,
    config_enable_shields BOOLEAN DEFAULT TRUE,
    config_enable_death_list BOOLEAN DEFAULT FALSE,
    config_tie_break_method TEXT DEFAULT 'revote',
    -- Current holders
    shield_holder TEXT,
    dagger_holder TEXT,
    seer_holder TEXT,
    -- Raw JSON for backward compatibility
    raw_json TEXT
);

-- players table (denormalized per-game)
CREATE TABLE players (
    id TEXT NOT NULL,
    game_id TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    role TEXT CHECK(role IN ('FAITHFUL', 'TRAITOR')),
    archetype_id TEXT,
    archetype_name TEXT,
    alive BOOLEAN DEFAULT TRUE,
    eliminated_day INTEGER,
    elimination_type TEXT CHECK(elimination_type IN ('BANISHED', 'MURDERED', NULL)),
    was_recruited BOOLEAN DEFAULT FALSE,
    backstory TEXT,
    strategic_profile TEXT,
    -- Demographics
    demographics_age INTEGER,
    demographics_location TEXT,
    demographics_occupation TEXT,
    -- Personality (OCEAN)
    openness REAL,
    conscientiousness REAL,
    extraversion REAL,
    agreeableness REAL,
    neuroticism REAL,
    -- Stats
    intellect REAL,
    dexterity REAL,
    composure REAL,
    social_influence REAL,
    -- Status flags
    has_shield BOOLEAN DEFAULT FALSE,
    has_dagger BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (id, game_id)
);

-- events table
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    day INTEGER NOT NULL,
    phase TEXT,
    actor_id TEXT,
    target_id TEXT,
    data JSON,
    narrative TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- trust_snapshots table (efficient per-cell storage)
CREATE TABLE trust_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    day INTEGER NOT NULL,
    phase TEXT NOT NULL,
    alive_count INTEGER,
    observer_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    suspicion REAL NOT NULL,
    UNIQUE(game_id, day, phase, observer_id, target_id)
);

-- vote_history table (per-day voting records)
CREATE TABLE vote_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    day INTEGER NOT NULL,
    voter_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    UNIQUE(game_id, day, voter_id)
);

-- breakfast_order table (entry order per day)
CREATE TABLE breakfast_order (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    day INTEGER NOT NULL,
    position INTEGER NOT NULL,
    player_id TEXT NOT NULL,
    UNIQUE(game_id, day, position)
);

-- Indices for common queries
CREATE INDEX idx_games_created ON games(created_at DESC);
CREATE INDEX idx_games_winner ON games(winner);

CREATE INDEX idx_players_game ON players(game_id);
CREATE INDEX idx_players_role ON players(game_id, role);
CREATE INDEX idx_players_alive ON players(game_id, alive);

CREATE INDEX idx_events_game_day ON events(game_id, day);
CREATE INDEX idx_events_type ON events(game_id, type);
CREATE INDEX idx_events_actor ON events(game_id, actor_id);
CREATE INDEX idx_events_target ON events(game_id, target_id);

CREATE INDEX idx_trust_game_day ON trust_snapshots(game_id, day, phase);
CREATE INDEX idx_trust_observer ON trust_snapshots(game_id, observer_id);
CREATE INDEX idx_trust_target ON trust_snapshots(game_id, target_id);

CREATE INDEX idx_vote_history_game ON vote_history(game_id, day);
CREATE INDEX idx_breakfast_game ON breakfast_order(game_id, day);
