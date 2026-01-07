"""Main entry point for TraitorSim.

This simulation uses a dual-SDK architecture:
- Claude Agent SDK: Player agents with MCP tools for structured decisions
- Gemini Interactions API: Game Master with server-side conversation state (55-day retention)

Async execution enables parallel voting/reflection for 5-10x performance improvement.

Model Provider Support:
    Player agents can use Anthropic Claude or Z.AI GLM-4.7 (Claude-compatible API).
    Use --agent-provider flag to select:
    - auto: Try Anthropic first, fallback to Z.AI on failure (default, most resilient)
    - anthropic: Claude models via Anthropic API only
    - zai: GLM-4.7 via Z.AI API only (cheaper alternative)

    Example:
        python -m traitorsim                           # Auto mode (default)
        python -m traitorsim --agent-provider zai      # Use GLM-4.7 only
        python -m traitorsim --agent-provider anthropic  # Use Claude only
"""

import argparse
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

from .core.config import GameConfig
from .core.game_engine_async import GameEngineAsync
from .utils.logger import setup_logger


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="TraitorSim - AI Reality TV Social Deduction Simulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m traitorsim                              # Auto mode (Claude → GLM fallback)
    python -m traitorsim --agent-provider anthropic   # Claude only (no fallback)
    python -m traitorsim --agent-provider zai         # GLM-4.7 only (cheaper)
        """
    )

    # Model provider options
    parser.add_argument(
        "--agent-provider",
        choices=["anthropic", "zai", "auto"],
        default=os.environ.get("TRAITORSIM_AGENT_PROVIDER", "auto"),
        help="Model provider for player agents (default: auto)"
    )
    parser.add_argument(
        "--agent-model",
        default=os.environ.get("TRAITORSIM_AGENT_MODEL", "claude-sonnet-4-5-20250929"),
        help="Model name for player agents (default: claude-sonnet-4-5-20250929)"
    )
    parser.add_argument(
        "--agent-fallback",
        action="store_true",
        default=os.environ.get("TRAITORSIM_AGENT_FALLBACK", "").lower() == "true",
        help="Enable fallback to Z.AI GLM if primary provider fails"
    )
    parser.add_argument(
        "--zai-api-key",
        default=os.environ.get("ZAI_API_KEY"),
        help="Z.AI API key (can also set ZAI_API_KEY env var)"
    )

    # Game configuration
    parser.add_argument(
        "--players",
        type=int,
        default=10,
        help="Total number of players (default: 10)"
    )
    parser.add_argument(
        "--traitors",
        type=int,
        default=3,
        help="Number of traitors (default: 3)"
    )

    return parser.parse_args()


def main():
    """Main entry point for TraitorSim."""

    # Load environment variables
    load_dotenv()

    # Parse command line args
    args = parse_args()

    # Setup logging
    setup_logger(verbose=True, save_to_file=True)
    logger = logging.getLogger(__name__)

    logger.info("\n" + "="*60)
    logger.info("TRAITORS SIMULATION - MVP")
    logger.info("="*60 + "\n")

    # Create config with model provider settings
    config = GameConfig(
        total_players=args.players,
        num_traitors=args.traitors,
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        personality_generation="archetype",
        persona_library_path="data/personas/library",
        # Model provider settings
        agent_model_provider=args.agent_provider,
        agent_model=args.agent_model,
        agent_fallback_enabled=args.agent_fallback,
        zai_api_key=args.zai_api_key,
    )

    # Log model provider configuration
    provider_name = {
        "anthropic": "Anthropic Claude",
        "zai": "Z.AI GLM-4.7",
        "auto": "Auto (Claude → GLM fallback)"
    }.get(config.agent_model_provider, config.agent_model_provider)

    logger.info(f"🤖 Agent Model Provider: {provider_name}")
    logger.info(f"   Model: {config.agent_model}")
    if config.agent_fallback_enabled:
        logger.info("   Fallback: Enabled (will try Z.AI GLM if primary fails)")

    # Validate API keys
    if not config.gemini_api_key:
        logger.warning("⚠️  GEMINI_API_KEY not set. Using fallback narratives.")

    # Check for agent model auth based on provider
    has_agent_auth = False
    if config.agent_model_provider == "zai":
        has_agent_auth = bool(config.zai_api_key)
        if has_agent_auth:
            logger.info("✅ Using Z.AI GLM-4.7 via ZAI_API_KEY")
        else:
            logger.warning("⚠️  ZAI_API_KEY not set. Required for --agent-provider zai")
    elif config.agent_model_provider == "anthropic":
        has_agent_auth = bool(os.getenv("CLAUDE_CODE_OAUTH_TOKEN"))
        if has_agent_auth:
            logger.info("✅ Using Anthropic Claude via CLAUDE_CODE_OAUTH_TOKEN")
        else:
            logger.warning("⚠️  CLAUDE_CODE_OAUTH_TOKEN not set. Using fallback decisions.")
    else:  # auto
        has_claude = bool(os.getenv("CLAUDE_CODE_OAUTH_TOKEN"))
        has_zai = bool(config.zai_api_key)
        has_agent_auth = has_claude or has_zai
        if has_claude:
            logger.info("✅ Auto mode: Will try Claude first (CLAUDE_CODE_OAUTH_TOKEN set)")
        if has_zai:
            logger.info("✅ Auto mode: Z.AI fallback available (ZAI_API_KEY set)")
        if not has_agent_auth:
            logger.warning("⚠️  No agent auth configured for auto mode")

    if not config.gemini_api_key and not has_agent_auth:
        logger.error("❌ No API keys set. The simulation will run but use fallback logic.")
        logger.error("   Set GEMINI_API_KEY and CLAUDE_CODE_OAUTH_TOKEN in .env file")
        logger.error("   Or use --agent-provider zai with ZAI_API_KEY\n")

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
