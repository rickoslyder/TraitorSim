"""Main entry point for containerized TraitorSim.

This version uses Docker containers for player agents, communicating via HTTP.
Each agent runs in isolated environment with dedicated resources.
"""

import logging
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

from .core.config import GameConfig
from .core.game_engine_containerized import GameEngineContainerized
from .utils.logger import setup_logger


def validate_persona_library(config: GameConfig) -> bool:
    """Validate that persona library exists and is populated.

    Args:
        config: Game configuration

    Returns:
        True if valid, False otherwise
    """
    persona_dir = Path(config.persona_library_path)

    if not persona_dir.exists():
        return False

    # Check for JSON persona files
    persona_files = list(persona_dir.glob("*.json"))

    if len(persona_files) == 0:
        return False

    # Try to load one file to validate format
    import json
    try:
        with open(persona_files[0]) as f:
            data = json.load(f)
            # Basic validation - check for required fields
            if isinstance(data, list):
                sample = data[0] if data else {}
            else:
                sample = data

            required_fields = ["name", "archetype", "personality", "backstory"]
            if not all(field in sample for field in required_fields):
                return False
    except Exception:
        return False

    return True


def main():
    """Main entry point for containerized TraitorSim."""

    # Load environment variables
    load_dotenv()

    # Setup logging
    setup_logger(verbose=True, save_to_file=True)
    logger = logging.getLogger(__name__)

    logger.info("\n" + "="*60)
    logger.info("TRAITORS SIMULATION - CONTAINERIZED")
    logger.info("="*60 + "\n")

    # Create config (full 24-player game per architectural spec)
    config = GameConfig(
        total_players=24,
        num_traitors=3,  # Standard starting traitor count
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_days=20,  # Full season
    )

    # Validate API keys
    if not config.gemini_api_key:
        logger.warning("⚠️  GEMINI_API_KEY not set. Using fallback narratives.")

    # Check for Claude auth (API key OR OAuth token)
    has_claude_auth = config.anthropic_api_key or os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
    if not has_claude_auth:
        logger.warning("⚠️  ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN not set.")
    elif os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        logger.info("✅ Using Claude subscription via CLAUDE_CODE_OAUTH_TOKEN in containers")

    if not config.gemini_api_key and not has_claude_auth:
        logger.error("❌ No API keys set. The simulation will run but use fallback logic.")
        logger.error("   Set GEMINI_API_KEY and ANTHROPIC_API_KEY in .env file")
        logger.error("   See .env.example for template\n")

    # Validate persona library
    logger.info("🔍 Validating persona library...")
    if not validate_persona_library(config):
        logger.error("❌ Persona library missing or invalid!")
        logger.error(f"   Expected location: {config.persona_library_path}")
        logger.error("   Generate personas first:")
        logger.error("   ./scripts/generate_persona_library.sh --count 15\n")
        sys.exit(1)
    else:
        persona_count = len(list(Path(config.persona_library_path).glob("*.json")))
        logger.info(f"✅ Persona library validated ({persona_count} files)\n")

    # Agent base URL (localhost for docker-compose)
    agent_base_url = os.getenv("AGENT_BASE_URL", "http://localhost")

    logger.info("📦 Containerized Architecture:")
    logger.info(f"   - Game Engine: Host process")
    logger.info(f"   - Player Agents: {config.total_players} Docker containers")
    logger.info(f"   - Agent URLs: {agent_base_url}:18000-18009")
    logger.info(f"   - Memory: 1GB per container ({config.total_players}GB total)")
    logger.info(f"   - CPU: 1.0 core per container ({config.total_players} cores total)\n")

    # Create and run game (containerized engine with HTTP communication)
    engine = GameEngineContainerized(config, agent_base_url=agent_base_url)

    try:
        winner = engine.run_game()  # Synchronous wrapper for async engine
        logger.info(f"\n🏆 WINNERS: {winner}S")
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Game interrupted by user")
    except Exception as e:
        logger.error(f"\n\n❌ Game error: {e}", exc_info=True)
        sys.exit(1)

    logger.info("\nSimulation complete!")


if __name__ == "__main__":
    main()
