"""Prompt templates for Player Agents.

Enhanced with training data integration for realistic behavior patterns.
"""

from typing import List, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ...core.game_state import Player, GameState
    from ...training.training_data_loader import OCEANTraits

# Lazy import to avoid circular dependencies
_training_loaded = False
_training_loader = None
_strategy_advisor = None
_behavior_modulator = None


def _get_training_components():
    """Lazy load training components."""
    global _training_loaded, _training_loader, _strategy_advisor, _behavior_modulator

    if not _training_loaded:
        try:
            from ...training import (
                TrainingDataLoader,
                StrategyAdvisor,
                BehaviorModulator,
            )
            _training_loader = TrainingDataLoader().load()
            _strategy_advisor = StrategyAdvisor(_training_loader)
            _behavior_modulator = BehaviorModulator(_training_loader)
            _training_loaded = True
        except Exception as e:
            print(f"Warning: Could not load training data: {e}")
            _training_loaded = True  # Don't retry

    return _training_loader, _strategy_advisor, _behavior_modulator


class PlayerPrompts:
    """Prompt templates for Player Agents using Claude.

    Enhanced with training data from The Traitors UK Season 1 for:
    - Role-appropriate strategy suggestions
    - Phase-specific behavioral guidance
    - Personality-modulated decision making
    """

    @staticmethod
    def system_prompt(player: "Player") -> str:
        """Generate system prompt for player agent."""
        loader, advisor, modulator = _get_training_components()

        # Base personality description
        personality_lines = [
            f"- Openness: {player.personality['openness']:.1f} (higher = more receptive to new theories, lower = more rigid)",
            f"- Conscientiousness: {player.personality['conscientiousness']:.1f} (higher = more methodical, lower = more chaotic)",
            f"- Extraversion: {player.personality['extraversion']:.1f} (higher = more dominant/vocal, lower = more quiet)",
            f"- Agreeableness: {player.personality['agreeableness']:.1f} (higher = more cooperative, lower = more confrontational)",
            f"- Neuroticism: {player.personality['neuroticism']:.1f} (higher = more anxious/paranoid, lower = more calm)",
        ]

        # Add personality interpretation
        personality_summary = PlayerPrompts._interpret_personality(player.personality)

        role_guidance = ""
        if player.role.value == "traitor":
            role_guidance = """You are a TRAITOR. Your goal is to survive and eliminate Faithfuls while remaining undetected.
Never reveal you are a Traitor. Act like a Faithful at all times.

**Key Traitor Behaviors** (from successful players like Wilfred and Amanda):
- "Lie by telling the truth 90% of the time" - build genuine relationships
- Mirror Faithful behavior - be helpful, caring, and engaged
- Deflect suspicion through positivity, not defensiveness
- When voting, blend with the majority unless protecting a fellow Traitor"""
        else:
            role_guidance = """You are FAITHFUL. Your goal is to find and banish the Traitors.

**Key Faithful Behaviors** (from successful players like Fay and Claire):
- Look for inconsistencies in voting patterns
- Note who defends whom - Traitors protect each other
- Trust your gut but verify with evidence
- Don't be afraid to voice suspicions, but be strategic about timing"""

        return f"""You are {player.name}, a contestant on "The Traitors".

Your role: {player.role.value.upper()}

Your personality (Big Five traits):
{chr(10).join(personality_lines)}

**What This Means For You**:
{personality_summary}

{role_guidance}

Stay in character. Make decisions based on your personality traits and role.
Your personality affects how you react, but you should still be strategic."""

    @staticmethod
    def _interpret_personality(personality: Dict[str, float]) -> str:
        """Generate personality interpretation from OCEAN traits."""
        interpretations = []

        # Openness
        if personality.get('openness', 0.5) >= 0.7:
            interpretations.append("You're intellectually curious and open to new theories about who the Traitors might be")
        elif personality.get('openness', 0.5) <= 0.3:
            interpretations.append("You prefer sticking with established facts and proven evidence")

        # Conscientiousness
        if personality.get('conscientiousness', 0.5) >= 0.7:
            interpretations.append("You're methodical and organized in your approach to the game")
        elif personality.get('conscientiousness', 0.5) <= 0.3:
            interpretations.append("You're spontaneous and may act on instinct")

        # Extraversion
        if personality.get('extraversion', 0.5) >= 0.7:
            interpretations.append("You're vocal and likely to lead discussions at the Round Table")
        elif personality.get('extraversion', 0.5) <= 0.3:
            interpretations.append("You're quiet and observant, preferring to listen before speaking")

        # Agreeableness
        if personality.get('agreeableness', 0.5) >= 0.7:
            interpretations.append("You're cooperative and tend to build alliances")
        elif personality.get('agreeableness', 0.5) <= 0.3:
            interpretations.append("You're direct and not afraid of confrontation")

        # Neuroticism
        if personality.get('neuroticism', 0.5) >= 0.7:
            interpretations.append("You're anxious and may read too much into small details")
        elif personality.get('neuroticism', 0.5) <= 0.3:
            interpretations.append("You stay calm under pressure and don't get rattled easily")

        if not interpretations:
            interpretations.append("You have a balanced personality and adapt to situations")

        return "\n".join(f"- {i}" for i in interpretations)

    @staticmethod
    def daily_reflection(
        player: "Player", observations: str, state: "GameState"
    ) -> str:
        """Generate prompt for daily reflection."""
        alive_players = [p.name for p in state.alive_players if p.id != player.id]

        return f"""It's the end of Day {state.day}. Reflect on what you've observed today.

Recent events:
{observations if observations else "Nothing notable yet."}

Current alive players (besides you):
{', '.join(alive_players)}

Based on today's events and your personality, write a brief reflection (2-3 sentences):
- What are your current suspicions?
- Who do you trust or distrust?
- What patterns have you noticed?

Write naturally as {player.name} would think."""

    @staticmethod
    def voting_decision(
        player: "Player",
        candidates: List[str],
        suspicions: Dict[str, float],
        state: "GameState",
    ) -> str:
        """Generate prompt for voting decision with strategic guidance."""
        loader, advisor, modulator = _get_training_components()

        # Build suspicion list
        suspicion_list = []
        for candidate_id in candidates:
            candidate = state.get_player(candidate_id)
            if candidate:
                score = suspicions.get(candidate_id, 0.5)
                suspicion_list.append(f"- {candidate.name} ({candidate_id}): {score:.2f}")

        # Get strategic guidance based on role and personality
        strategic_guidance = ""
        if advisor and modulator:
            try:
                from ...training.training_data_loader import OCEANTraits
                ocean = OCEANTraits.from_dict(player.personality)

                game_context = {
                    "day": state.day,
                    "alive_count": len(list(state.alive_players)),
                    "suspicion_on_me": 0.3,  # Could be calculated from others' matrices
                }

                # Get voting-specific guidance
                guidance = advisor.get_voting_guidance(
                    role=player.role.value,
                    personality=ocean,
                    candidates=[{"id": c, "suspicion_score": suspicions.get(c, 0.5)} for c in candidates],
                    game_context=game_context,
                )

                if guidance:
                    strategic_guidance = f"\n**Strategic Guidance for Your Role and Personality**:\n{guidance}\n"
            except Exception:
                pass  # Fallback to basic prompt if training data unavailable

        role_hint = ""
        if player.role.value == "traitor":
            role_hint = """**As a TRAITOR**:
- Avoid voting for fellow Traitors unless absolutely necessary for cover
- Vote with the majority to blend in
- If someone suspects you, consider whether voting against them helps or hurts
- "Bus throwing" (sacrificing a fellow Traitor) is a valid but costly strategy"""
        else:
            role_hint = """**As FAITHFUL**:
- Vote for who you genuinely suspect is a Traitor
- Look for voting patterns - who consistently votes together?
- Consider who has defended whom (Traitors protect Traitors)
- Don't just follow the crowd - independent thinking catches Traitors"""

        return f"""It's time to vote at the Round Table on Day {state.day}.

Your current suspicions (0.0 = trust, 1.0 = certain traitor):
{chr(10).join(suspicion_list) if suspicion_list else "No suspicions recorded yet."}

{role_hint}
{strategic_guidance}
**Your Personality Affects Your Vote**:
- Extraversion {player.personality.get('extraversion', 0.5):.1f}: {"Lead the vote" if player.personality.get('extraversion', 0.5) >= 0.7 else "Follow strong arguments" if player.personality.get('extraversion', 0.5) <= 0.3 else "Contribute to discussion"}
- Agreeableness {player.personality.get('agreeableness', 0.5):.1f}: {"May vote with allies" if player.personality.get('agreeableness', 0.5) >= 0.7 else "Independent judgment" if player.personality.get('agreeableness', 0.5) <= 0.3 else "Balanced approach"}
- Neuroticism {player.personality.get('neuroticism', 0.5):.1f}: {"May over-suspect" if player.personality.get('neuroticism', 0.5) >= 0.7 else "Calm analysis" if player.personality.get('neuroticism', 0.5) <= 0.3 else "Reasonable caution"}

You must vote to BANISH one player.

Provide brief reasoning (1-2 sentences) then respond with:
VOTE: [player_id]

Example: "I suspect player_03 because they've been too quiet and always votes with the majority. VOTE: player_03" """

    @staticmethod
    def murder_decision(player: "Player", faithful: List[str], state: "GameState") -> str:
        """Generate prompt for traitor murder decision with strategic guidance."""
        loader, advisor, modulator = _get_training_components()

        # Build target list with threat assessment
        target_list = []
        for faithful_id in faithful:
            target = state.get_player(faithful_id)
            if target:
                target_list.append(f"- {target.name} ({faithful_id})")

        # Get murder-specific strategic guidance
        strategic_guidance = ""
        if advisor:
            try:
                from ...training.training_data_loader import OCEANTraits
                ocean = OCEANTraits.from_dict(player.personality)

                game_context = {
                    "day": state.day,
                    "alive_count": len(list(state.alive_players)),
                }

                guidance = advisor.get_murder_guidance(
                    personality=ocean,
                    potential_victims=[{"id": f, "name": state.get_player(f).name if state.get_player(f) else f} for f in faithful],
                    game_context=game_context,
                )

                if guidance:
                    strategic_guidance = f"\n{guidance}\n"
            except Exception:
                pass

        return f"""You are a Traitor. It's time to choose who to murder tonight on Day {state.day}.

Available Faithful targets:
{chr(10).join(target_list)}

**Murder Strategy** (from successful Traitors like Wilfred, Amanda, Alyssa):

*Target Selection Principles*:
1. **Threat Elimination**: Kill those who suspect you or are close to figuring it out
2. **Chaos Creation**: Kill popular/trusted players to create grief and confusion
3. **Strategic Preservation**: Keep "useful idiots" alive - Faithfuls who defend you
4. **Shield Awareness**: Check if anyone might have Shield protection (murder fails if shielded)
5. **Recruitment Consideration**: Sometimes sparing someone makes them a recruitment target later
{strategic_guidance}
**Your Personality Affects Your Choice**:
- {"Aggressive approach - eliminate threats quickly" if player.personality.get('extraversion', 0.5) >= 0.7 else "Cautious approach - consider long-term strategy" if player.personality.get('extraversion', 0.5) <= 0.3 else "Balanced approach"}
- {"Analytical target selection" if player.personality.get('conscientiousness', 0.5) >= 0.7 else "Trust your instincts" if player.personality.get('conscientiousness', 0.5) <= 0.3 else "Mix of logic and intuition"}
- {"May struggle emotionally with the kill" if player.personality.get('agreeableness', 0.5) >= 0.7 else "Decisive and detached" if player.personality.get('agreeableness', 0.5) <= 0.3 else "Accept it as part of the game"}

Provide brief reasoning (1-2 sentences) then respond with:
VOTE: [player_id]

Example: "Player_02 is too observant and mentioned my inconsistent voting pattern. They're a threat. VOTE: player_02" """
