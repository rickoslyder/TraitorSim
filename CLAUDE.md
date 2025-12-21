# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TraitorSim is a high-fidelity AI simulator for the reality TV show "The Traitors" - a social deduction game combining elements of Werewolf/Mafia with economic strategy and psychological manipulation. The system uses advanced multi-agent AI to simulate an entire season with distinct AI personalities exhibiting genuine social dynamics including deception, paranoia, alliance-building, and betrayal.

## Architecture

### Core Components

**Game Master Agent (Gemini 3.0 Flash ADK)**
- Orchestrates the game loop using Coordinator/Dispatcher pattern
- Manages state transitions between game phases
- Leverages 1M+ token context window to maintain entire season transcript
- Delegates to specialized sub-agents:
  - VotingAgent: Vote tallying and tie-breaking logic
  - NarrativeAgent: Dramatic descriptions and event generation
  - PsychAgent: Updates hidden stress/trust levels across all agents

**Player Agents (Claude Agents SDK)**
- Individual AI contestants with distinct personalities
- File-system-based memory architecture for progressive disclosure
- Custom SKILL.md files defining strategic behaviors
- Trust Matrix tracking (Bayesian belief updates about other players)
- Big Five personality traits (OCEAN) modulating all decisions

**Game Engine (Python)**
- Strict rule enforcement layer
- State machine managing day/night cycles
- Economic modeling for Prize Pot
- Mission execution and performance tracking
- Win condition evaluation

### Game State Machine

The simulation cycles through five phases per "day":

1. **STATE_BREAKFAST** - Murder victim reveal; agents update trust matrices based on "breakfast order tell"
2. **STATE_MISSION** - Cooperative/competitive challenges testing different agent stats (Intellect, Dexterity, Composure)
3. **STATE_SOCIAL** - Pre-voting alliance building and information warfare
4. **STATE_ROUNDTABLE** - Public accusations and banishment voting
5. **STATE_TURRET** - Traitors secretly murder a Faithful (or recruit new Traitors)

### Agent Memory System

Each agent maintains a private directory structure:
```
/memories/player_{id}/
  ├── profile.md              # Self-concept and role
  ├── suspects.csv            # Trust Matrix (suspicion scores)
  ├── diary/                  # Daily logs
  │   ├── day_01_morning.md
  │   └── day_01_roundtable.md
  └── skills/                 # Behavioral modules
      ├── skill-traitor-defense.md
      ├── skill-faithful-hunting.md
      └── skill-shield-logic.md
```

### Personality System

Agents are initialized with Big Five (OCEAN) traits that weight decision-making:

- **Openness**: Receptiveness to new theories vs. rigid thinking
- **Conscientiousness**: Mission reliability and voting consistency
- **Extraversion**: Round Table dominance vs. passive following
- **Agreeableness**: Alliance loyalty vs. confrontational "truth-telling"
- **Neuroticism**: Paranoia/defensiveness vs. stoic composure

Each trait (0.0-1.0) modulates agent behavior across all game phases.

## Key Simulation Mechanics

### Trust Matrix Updates

Agents maintain an M_ij matrix where M_ij = Agent i's suspicion of Agent j (0.0 = absolute trust, 1.0 = certain traitor).

Updates triggered by:
- **Voting records**: Voting for/defending revealed Traitors
- **Mission sabotage**: Unexplained failures (vs. baseline clumsiness)
- **Social cues**: "Too quiet" or "too knowledgeable" behavior
- **Breakfast tells**: Consistently entering last but never murdered (indicates Traitor or recruitment)

### Regional Rule Variants

The simulator must support multiple franchise rule sets:

**Recruitment Mechanics**
- Standard: Triggered when Traitor banished; Faithful can decline
- Ultimatum (Blackmail): Last Traitor forces "Join or Die"

**End Game Variants**
- Vote to End (UK/US): Final 4 vote to continue or end; unanimous required
- Traitor's Dilemma (Australia): Final 2 Traitors play Prisoner's Dilemma (Share/Steal)

**Tie-Breaking**
- Revote with tied players immune
- Countback (cumulative season votes)
- Random draw/coin toss

### Strategic Heuristics

**Traitor Strategies:**
- "Traitor Angel": Perfect Faithful performance with loyal "useful idiots"
- "Bus Throwing": Sacrificing fellow Traitor when suspicion > threshold
- "Silent Murder": Killing trusted/non-suspicious players to create chaos

**Faithful Strategies:**
- "Shield Bluff": False Shield claims to detect information leaks
- Voting bloc analysis: Identifying coordinated voting patterns
- "Poisoned Chalice": Tracking recruitment via sudden survival shifts

## Mission Types

Missions test different agent attributes and provide observables for trust updates:

- **The Funeral (Social/Memory)**: Question-answering reveals agent attentiveness
- **Laser Heist (Dexterity/Risk)**: Probabilistic skill checks; sabotage vs. clumsiness detection
- **Cabin Creepies (Fear/Willpower)**: Neuroticism trait tests; agents may fake fear to blend
- **Crossbow Challenge (Accuracy/Vindictiveness)**: Revealed preference game showing target priorities

## Implementation Notes

### When Writing Game Engine Code

1. **State transitions must be atomic** - Never leave the game in an intermediate state
2. **All randomness must be seeded** - For reproducible season replays
3. **Trust Matrix updates are append-only** - Maintain full history for agent "memory recall"
4. **Mission performance uses formula**: `Success = (Base_Stat * Personality_Modifier) - Stress_Level`

### When Writing Agent Logic

1. **Agents cannot access ground truth** - Only their knowledge base (role, observations, Trust Matrix)
2. **Traitors must maintain "Faithful mask"** - Their public statements cannot leak privileged information
3. **Bayesian updates required** - Don't hard-code suspicions; calculate from evidence
4. **Personality traits are weights, not absolutes** - High Agreeableness increases probability of cooperation, doesn't guarantee it

### When Implementing Memory System

1. **Progressive disclosure pattern** - Agents should query specific memory files, not load everything
2. **Skills are executable prompts** - SKILL.md files define contextual behavior (e.g., "how to defend when accused")
3. **Diary entries must be timestamped** - Format: `day_{N}_{phase}.md`
4. **Trust Matrix persists as CSV** - Format: `target_id,suspicion_score,last_updated,evidence_summary`

### API Integration

**Claude Agents SDK Usage:**
- Memory: File-system-based retrieval from `/memories/{agent_id}/`
- Skills: Load SKILL.md files for context-specific behavior modules
- Decision generation: Construct prompts with personality traits + recent memory + current context

**Gemini 3.0 Flash Usage:**
- Game Master orchestration with full season context
- Narrative generation for dramatic event descriptions
- Dispatcher pattern for coordinating sub-agents

## Configuration Vectors

When initializing a simulation, the following parameters must be configurable:

```python
{
  "rule_set": "UK" | "US" | "Australia",
  "recruitment_type": "standard" | "ultimatum",
  "end_game_mode": "vote_to_end" | "traitors_dilemma",
  "tie_break_method": "revote" | "countback" | "random",
  "enable_dramatic_entry": true | false,  # Breakfast order manipulation
  "shield_visibility": "public" | "secret",
  "num_players": 20,  # Typically 20-22
  "num_traitors": 3,  # Typically 3-4
  "starting_pot": 0,
  "personality_generation": "random" | "archetype" | "custom"
}
```

## Testing Considerations

When writing tests:
- **End-to-end season tests** should verify win condition logic across all rule variants
- **Trust Matrix tests** should validate Bayesian update formulas with known evidence sequences
- **Personality tests** should confirm trait weights properly modulate decision probabilities
- **Mission tests** should check both cooperative and sabotage scenarios
- **Recruitment tests** must handle acceptance, refusal, and ultimatum edge cases
- **Tie-break tests** should cover all resolution paths including countback edge cases

## Critical Edge Cases

1. **All Traitors Banished Early**: Faithful win immediately
2. **Traitor Majority**: Traitors can force "Vote to End" and auto-win
3. **Shield on Murder Target**: Murder fails; Traitors must select alternate
4. **Recruitment Declined**: Game continues with reduced Traitor count
5. **Final Two (Both Traitors)**: Triggers Dilemma or Share depending on rule set
6. **Perfect Tie in Countback**: Falls back to random if cumulative votes equal

## Code Style Expectations

- Use type hints for all function signatures
- Agent decision logic should be pure functions (no side effects except API calls)
- State mutations only in GameEngine methods
- Trust Matrix updates should emit event logs for debugging
- All personality trait access via getter methods (not direct dict access)
