"""Game configuration dataclass.

Based on comprehensive research of The Traitors Wiki (Dec 2025).
Supports UK, US, Australia, Canada, and other international rule variants.
"""

from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class GameConfig:
    """Configuration for game rules and setup.

    Rule variants based on actual show mechanics:
    - UK: 22-25 players, 3 Traitors, Vote to End, Seer power (S3+), no Dagger
    - US: 20-23 players, 3-4 Traitors, Vote to End, Seer power (S3+), no Dagger
    - Australia: 20-24 players, 3-4 Traitors, enhanced Shield (also blocks banishment)
    - Canada: 20 players, 3 Traitors, Dagger available, Ultimatum recruitment
    """

    # ===========================================
    # PLAYER SETUP
    # ===========================================
    total_players: int = 22  # UK standard: 22-25, US: 20-23
    num_traitors: int = 3  # UK always 3, US 3-4 (we default to UK standard)

    # ===========================================
    # RULE SET PRESETS
    # ===========================================
    # "uk" = UK rules (no Dagger, Seer available, standard Shield)
    # "us" = US rules (similar to UK)
    # "australia" = Enhanced Shield (blocks murder AND banishment)
    # "canada" = Dagger available, standard rules
    # "custom" = Use individual settings below
    rule_set: str = "uk"

    # ===========================================
    # RECRUITMENT MECHANICS
    # ===========================================
    enable_recruitment: bool = True  # Traitor recruitment when traitor banished
    # "standard" = Faithful can decline (night wasted if declined)
    # "ultimatum" = Join or be murdered immediately (UK Series 1+)
    # "blackmail" = Forced recruitment, no choice (Norway)
    recruitment_type: str = "standard"

    # ===========================================
    # SHIELD MECHANICS
    # ===========================================
    enable_shields: bool = True  # Shield protects from murder
    shield_visibility: str = "secret"  # "secret" or "public"
    # Shield power scope:
    # "murder_only" = Standard (UK/US/most versions) - only blocks murder
    # "murder_and_banishment" = Australia variant - blocks both
    shield_power: str = "murder_only"

    # ===========================================
    # DAGGER MECHANICS (based on actual show research)
    # ===========================================
    # IMPORTANT: UK and US versions do NOT use the Dagger!
    # Dagger is used in: Canada, France, Netherlands, Norway, etc.
    # "never" = No dagger (UK/US accurate - they use Seer instead)
    # "rare" = Offered on specific days as Shield OR Dagger choice (Canada style)
    # "every_mission" = Unrealistic legacy behavior
    dagger_mode: str = "never"  # Changed to "never" for UK/US accuracy
    dagger_mission_days: Tuple[int, ...] = (4, 8)  # Only if dagger_mode="rare"

    # ===========================================
    # SEER POWER (UK Series 3+, US Season 3+)
    # ===========================================
    # Allows one player to confirm another's true role (Traitor/Faithful)
    # Won through mission performance, typically late-game
    enable_seer: bool = True  # UK/US use Seer instead of Dagger
    seer_available_day: int = 8  # Day when Seer power becomes available
    # "mission_winner" = Top mission performer wins Seer
    # "auction" = Players bid prize money for Seer
    seer_acquisition: str = "mission_winner"

    # ===========================================
    # DEATH LIST / ON TRIAL MECHANIC
    # ===========================================
    # Traitors pre-select 3-4 murder candidates, restricting their choices
    # Used when "Traitors have been too efficient at murdering"
    enable_death_list: bool = False  # Optional mechanic

    # ===========================================
    # MISSION SETTINGS
    # ===========================================
    mission_base_reward: float = 10000.0  # UK: £2,000-10,000, US: $5,000-30,000
    mission_difficulty: float = 0.5
    enable_dramatic_entry: bool = True  # Breakfast order tells

    # ===========================================
    # VOTING / BANISHMENT
    # ===========================================
    # "revote" = Standard - revote with only tied players eligible (UK/US)
    # "random" = Random selection if tie persists
    # "countback" = Cumulative season votes determine winner
    tie_break_method: str = "revote"

    # ===========================================
    # ENDGAME MECHANICS
    # ===========================================
    # "vote_to_end" = UK/US standard - unanimous vote required to end
    # "traitors_dilemma" = Australia S2 - Share/Steal between Traitors
    # "prisoners_dilemma" = Netherlands original - all finalists Share/Steal
    end_game_type: str = "vote_to_end"
    final_player_count: int = 4  # Game can end when this many remain

    # 2025 Rule Change: Eliminated endgame players don't reveal their role
    # Forces remaining players to rely on intuition
    endgame_reveal_roles: bool = False  # False = 2025 rules, True = classic

    # ===========================================
    # AI CONFIGURATION
    # ===========================================
    gemini_model: str = "gemini-3-flash-preview"
    claude_model: str = "claude-sonnet-4-5-20250929"

    # ===========================================
    # PERSONA GENERATION
    # ===========================================
    personality_generation: str = "archetype"
    persona_library_path: str = "data/personas/library"
    world_bible_path: str = "WORLD_BIBLE.md"

    # ===========================================
    # LOGGING
    # ===========================================
    verbose: bool = True
    save_transcripts: bool = True

    # ===========================================
    # API SETTINGS
    # ===========================================
    gemini_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # ===========================================
    # SAFETY LIMITS
    # ===========================================
    max_days: int = 20  # Typical season is 10-12 days
