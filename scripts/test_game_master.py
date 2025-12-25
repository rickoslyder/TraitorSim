#!/usr/bin/env python3
"""Minimal test script for GameMasterInteractions with World Bible grounding.

Tests:
1. World Bible file upload to Gemini
2. Document reference passing on first interaction
3. Interaction chaining via previous_interaction_id
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traitorsim.core.game_state import GameState, GamePhase
from traitorsim.core.enums import Role
from traitorsim.agents.game_master_interactions import GameMasterInteractions


async def test_game_master():
    """Test GameMaster with World Bible grounding."""
    print("=" * 60)
    print("Testing GameMasterInteractions with World Bible")
    print("=" * 60)

    # Check API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not set")
        sys.exit(1)
    print(f"✓ API key set (length: {len(api_key)})")

    # Create minimal game state
    game_state = GameState()
    game_state.day = 1
    game_state.current_phase = GamePhase.BREAKFAST

    # Initialize Game Master
    print("\nInitializing GameMaster...")
    gm = GameMasterInteractions(
        game_state=game_state,
        api_key=api_key,
        model_name="gemini-2.5-flash",  # Use stable model
        world_bible_path="WORLD_BIBLE.md"
    )

    if gm.world_bible_file:
        print(f"✓ World Bible uploaded: {gm.world_bible_file.name}")
        print(f"  URI: {gm.world_bible_file.uri}")
    else:
        print("⚠️ World Bible not uploaded (using fallback)")

    # Test 1: Game start announcement (first turn - includes World Bible doc)
    print("\n" + "-" * 60)
    print("Test 1: Game Start Announcement (with World Bible context)")
    print("-" * 60)

    players = ["Alice", "Bob", "Charlie", "Diana", "Eve"]
    traitors = ["Charlie"]
    faithful = ["Alice", "Bob", "Diana", "Eve"]

    announcement = await gm.announce_game_start_async(players, traitors, faithful)
    print(f"\n{announcement}\n")

    if gm.current_interaction_id:
        print(f"✓ Interaction ID: {gm.current_interaction_id[:20]}...")

    # Test 2: Murder announcement (chained turn - uses previous_interaction_id)
    print("\n" + "-" * 60)
    print("Test 2: Murder Announcement (chained interaction)")
    print("-" * 60)

    murder_announcement = await gm.announce_murder_async("Alice", 1)
    print(f"\n{murder_announcement}\n")

    # Test 3: Check for World Bible brand consistency
    print("\n" + "-" * 60)
    print("Test 3: Lore Consistency Check")
    print("-" * 60)

    # Prompt that should elicit World Bible brands
    prompt = """Generate a mission briefing for Day 1.

**Mission Details**:
- Type: Castle Kitchen Challenge
- Difficulty: moderate
- Description: Contestants must prepare breakfast using ingredients from the castle larder.

Reference the breakfast provisions and setting. Use in-universe brands only.
Create a dramatic announcement (3-4 sentences)."""

    response = await gm._send_message_async(prompt)
    print(f"\n{response}\n")

    # Check for forbidden brands
    forbidden_terms = ["Starbucks", "Costa", "Tesco", "Sainsbury", "Facebook", "Instagram", "Google"]
    found_forbidden = [term for term in forbidden_terms if term.lower() in response.lower()]

    if found_forbidden:
        print(f"⚠️ Forbidden brand(s) found: {found_forbidden}")
    else:
        print("✓ No forbidden brands detected")

    # Check for in-universe brands
    in_universe = ["Highland Spring", "Cairngorm Coffee", "Loch Provisions", "Ardross", "Castle"]
    found_inuniverse = [term for term in in_universe if term.lower() in response.lower()]

    if found_inuniverse:
        print(f"✓ In-universe references found: {found_inuniverse}")
    else:
        print("⚠️ No explicit in-universe brands detected (may still be lore-consistent)")

    print("\n" + "=" * 60)
    print("✓ All tests completed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_game_master())
