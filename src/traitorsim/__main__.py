"""Main entry point for TraitorSim.

This simulation uses a dual-SDK architecture:
- Claude Agent SDK: Player agents with MCP tools for structured decisions
- Gemini Interactions API: Game Master with server-side conversation state (55-day retention)

Async execution enables parallel voting/reflection for 5-10x performance improvement.
"""

import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

from .core.config import GameConfig
from .core.game_engine_async import GameEngineAsync
from .utils.logger import setup_logger


def main():
    """Main entry point for TraitorSim."""

    # Load environment variables
    load_dotenv()

    # Setup logging
    setup_logger(verbose=True, save_to_file=True)
    logger = logging.getLogger(__name__)

    logger.info("\n" + "="*60)
    logger.info("TRAITORS SIMULATION - MVP")
    logger.info("="*60 + "\n")

    # Create config
    config = GameConfig(
        total_players=10,
        num_traitors=3,
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )

    # Validate API keys
    if not config.gemini_api_key:
        logger.warning("⚠️  GEMINI_API_KEY not set. Using fallback narratives.")

    # Check for Claude auth (API key OR OAuth token)
    has_claude_auth = config.anthropic_api_key or os.getenv("CLAUDE_CODE_OAUTH_TOKEN")
    if not has_claude_auth:
        logger.warning("⚠️  ANTHROPIC_API_KEY or CLAUDE_CODE_OAUTH_TOKEN not set. Using fallback decisions.")
    elif os.getenv("CLAUDE_CODE_OAUTH_TOKEN"):
        logger.info("✅ Using Claude subscription via CLAUDE_CODE_OAUTH_TOKEN")

    if not config.gemini_api_key and not has_claude_auth:
        logger.error("❌ No API keys set. The simulation will run but use fallback logic.")
        logger.error("   Set GEMINI_API_KEY and ANTHROPIC_API_KEY in .env file")
        logger.error("   See .env.example for template\n")

    # Create and run game (async engine with dual-SDK architecture)
    engine = GameEngineAsync(config)

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
