"""Game configuration dataclass."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GameConfig:
    """Configuration for game rules and setup."""

    # Player setup
    total_players: int = 10
    num_traitors: int = 3

    # Rule variants
    enable_recruitment: bool = True  # Traitor recruitment when traitor banished
    recruitment_type: str = "standard"  # "standard" or "ultimatum" (blackmail)
    enable_shields: bool = True  # Shield/Dagger mechanics
    shield_visibility: str = "secret"  # "secret" or "public"
    enable_dramatic_entry: bool = True  # Breakfast order tells

    # Mission settings
    mission_base_reward: float = 5000.0
    mission_difficulty: float = 0.5

    # Voting
    tie_break_method: str = "random"  # "random", "revote", "countback"

    # End game (MVP: simplified)
    end_game_type: str = "vote_to_end"  # "vote_to_end", "traitors_dilemma"
    final_player_count: int = 4

    # AI configuration
    gemini_model: str = "gemini-3-flash-preview"  # Latest Gemini model
    claude_model: str = "claude-sonnet-4-5-20250929"

    # Persona generation (World Bible system)
    personality_generation: str = "archetype"  # "archetype" (only mode, no random fallback)
    persona_library_path: str = "data/personas/library"
    world_bible_path: str = "WORLD_BIBLE.md"

    # Logging
    verbose: bool = True
    save_transcripts: bool = True

    # API settings (loaded from environment)
    gemini_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Safety limits
    max_days: int = 30  # Prevent infinite loops
