"""Flask API service for containerized player agents.

Each agent runs in its own Docker container and exposes HTTP endpoints
for game actions (voting, murder, reflection).
"""

import os
import asyncio
import logging
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
import json

from ..core.game_state import GameState, Player, Role, TrustMatrix
from ..core.config import GameConfig
from ..core.enums import GamePhase
from ..memory.memory_manager import MemoryManager
from .player_agent_sdk import PlayerAgentSDK

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global agent instance (initialized on startup)
agent: Optional[PlayerAgentSDK] = None


def deserialize_game_state(data: Dict[str, Any]) -> GameState:
    """Deserialize GameState from JSON."""
    game_state = GameState()
    game_state.day = data['day']
    game_state.phase = GamePhase(data['phase'])
    game_state.prize_pot = data['prize_pot']

    # Deserialize players
    game_state.players = []
    for p_data in data['players']:
        player = Player(
            id=p_data['id'],
            name=p_data['name'],
            role=Role(p_data['role']),
            alive=p_data['alive'],
            personality=p_data['personality'],
            stats=p_data['stats']
        )
        game_state.players.append(player)

    # Deserialize trust matrix
    if data.get('trust_matrix'):
        player_ids = [p.id for p in game_state.players]
        game_state.trust_matrix = TrustMatrix(player_ids)
        # Note: matrix values updated by agents themselves

    game_state.murdered_players = data.get('murdered_players', [])
    game_state.banished_players = data.get('banished_players', [])
    game_state.last_murder_victim = data.get('last_murder_victim')

    return game_state


def serialize_player(player: Player) -> Dict[str, Any]:
    """Serialize Player to JSON."""
    return {
        'id': player.id,
        'name': player.name,
        'role': player.role.value,
        'alive': player.alive,
        'personality': player.personality,
        'stats': player.stats
    }


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    if agent:
        return jsonify({
            'status': 'ok',
            'player_id': agent.player.id,
            'player_name': agent.player.name,
            'role': agent.player.role.value
        })
    return jsonify({'status': 'not_initialized'}), 503


@app.route('/initialize', methods=['POST'])
def initialize():
    """Initialize the agent with player data."""
    global agent

    try:
        data = request.json
        player_data = data['player']

        # Create Player instance
        player = Player(
            id=player_data['id'],
            name=player_data['name'],
            role=Role(player_data['role']),
            alive=player_data['alive'],
            personality=player_data['personality'],
            stats=player_data['stats']
        )

        # Create minimal game state
        game_state = GameState()
        game_state.players = [player]  # Will be updated on each request

        # Create memory manager
        config = GameConfig()
        memory_manager = MemoryManager(player, config)
        memory_manager.initialize()

        # Create agent
        agent = PlayerAgentSDK(player, game_state, memory_manager)

        logger.info(f"Initialized agent for {player.name} ({player.role.value})")

        return jsonify({
            'status': 'initialized',
            'player_id': player.id,
            'player_name': player.name
        })

    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/vote', methods=['POST'])
def vote():
    """Cast a vote to banish a player."""
    global agent

    if not agent:
        return jsonify({'error': 'Agent not initialized'}), 503

    try:
        data = request.json

        # Update agent's game state with current state
        agent.game_state = deserialize_game_state(data['game_state'])

        # Update agent's player reference
        agent.player = agent.game_state.get_player(agent.player.id)

        # Cast vote asynchronously
        target = asyncio.run(agent.cast_vote_async())

        # Get reasoning from tool context
        vote_result = agent.tool_context.get('vote_result', {})
        reasoning = vote_result.get('reasoning', 'No reasoning provided')

        logger.info(f"{agent.player.name} voted for {target}: {reasoning}")

        return jsonify({
            'target_player_id': target,
            'reasoning': reasoning,
            'voter_id': agent.player.id
        })

    except Exception as e:
        logger.error(f"Error in vote endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/choose_murder_victim', methods=['POST'])
def choose_murder_victim():
    """Choose a murder victim (Traitors only)."""
    global agent

    if not agent:
        return jsonify({'error': 'Agent not initialized'}), 503

    if agent.player.role != Role.TRAITOR:
        return jsonify({'error': 'Only traitors can murder'}), 403

    try:
        data = request.json

        # Update agent's game state
        agent.game_state = deserialize_game_state(data['game_state'])
        agent.player = agent.game_state.get_player(agent.player.id)

        # Choose victim asynchronously
        target = asyncio.run(agent.choose_murder_victim_async())

        # Get reasoning from tool context
        murder_result = agent.tool_context.get('murder_result', {})
        reasoning = murder_result.get('reasoning', 'Strategic elimination')

        logger.info(f"{agent.player.name} chose to murder {target}: {reasoning}")

        return jsonify({
            'target_player_id': target,
            'reasoning': reasoning,
            'traitor_id': agent.player.id
        })

    except Exception as e:
        logger.error(f"Error in choose_murder_victim endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/reflect', methods=['POST'])
def reflect():
    """Reflect on events and update suspicions."""
    global agent

    if not agent:
        return jsonify({'error': 'Agent not initialized'}), 503

    try:
        data = request.json

        # Update agent's game state
        agent.game_state = deserialize_game_state(data['game_state'])
        agent.player = agent.game_state.get_player(agent.player.id)

        # Get events
        events = data.get('events', [])

        # Reflect asynchronously
        asyncio.run(agent.reflect_on_day_async(events))

        logger.info(f"{agent.player.name} reflected on {len(events)} events")

        return jsonify({
            'status': 'completed',
            'player_id': agent.player.id
        })

    except Exception as e:
        logger.error(f"Error in reflect endpoint: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/get_suspicions', methods=['GET'])
def get_suspicions():
    """Get current suspicion scores."""
    global agent

    if not agent:
        return jsonify({'error': 'Agent not initialized'}), 503

    try:
        suspicions = agent.memory_manager.get_suspicions()

        return jsonify({
            'player_id': agent.player.id,
            'suspicions': suspicions
        })

    except Exception as e:
        logger.error(f"Error getting suspicions: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/choose_recruit_target', methods=['POST'])
def choose_recruit_target():
    """Choose who to recruit as a Traitor (Traitors only)."""
    global agent

    if not agent:
        return jsonify({'error': 'Agent not initialized'}), 503

    if agent.player.role != Role.TRAITOR:
        return jsonify({'error': 'Only traitors can recruit'}), 403

    try:
        data = request.json

        # Update agent's game state
        agent.game_state = deserialize_game_state(data['game_state'])
        agent.player = agent.game_state.get_player(agent.player.id)

        # Choose recruit target (pick strongest Faithful for alliance)
        faithful_players = [p for p in agent.game_state.alive_players if p.role == Role.FAITHFUL]

        if not faithful_players:
            return jsonify({'error': 'No faithful to recruit'}), 400

        # Simple strategy: recruit player with highest social influence
        target = max(faithful_players, key=lambda p: p.stats.get('social_influence', 0.5))

        logger.info(f"{agent.player.name} chose to recruit {target.name}")

        return jsonify({
            'target_player_id': target.id,
            'reasoning': 'Strategic recruitment'
        })

    except Exception as e:
        logger.error(f"Error choosing recruit target: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/decide_recruitment', methods=['POST'])
def decide_recruitment():
    """Decide whether to accept recruitment offer (Faithful only)."""
    global agent

    if not agent:
        return jsonify({'error': 'Agent not initialized'}), 503

    try:
        data = request.json

        # Update agent's game state
        agent.game_state = deserialize_game_state(data['game_state'])
        agent.player = agent.game_state.get_player(agent.player.id)

        is_ultimatum = data.get('is_ultimatum', False)

        # Decision logic based on personality and situation
        if is_ultimatum:
            # Ultimatum = join or die, rational choice is to accept
            accepts = True
            reasoning = "Survival instinct - accepting ultimatum"
        else:
            # Standard recruitment: personality-based decision
            # High agreeableness = more likely to betray principles
            # High neuroticism = fear of being caught as faithful
            agreeableness = agent.player.personality.get('agreeableness', 0.5)
            neuroticism = agent.player.personality.get('neuroticism', 0.5)

            # Check game state - if Traitors are winning, might join
            traitor_count = len([p for p in agent.game_state.alive_players if p.role == Role.TRAITOR])
            faithful_count = len([p for p in agent.game_state.alive_players if p.role == Role.FAITHFUL])

            # Calculate acceptance probability
            base_prob = (agreeableness + neuroticism) / 2
            if traitor_count >= faithful_count * 0.7:  # Traitors dominating
                base_prob += 0.2

            accepts = base_prob > 0.6
            reasoning = f"Personality-based decision (agreeableness={agreeableness:.2f})"

        logger.info(f"{agent.player.name} {'ACCEPTED' if accepts else 'REFUSED'} recruitment: {reasoning}")

        return jsonify({
            'accepts': accepts,
            'reasoning': reasoning
        })

    except Exception as e:
        logger.error(f"Error deciding recruitment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/vote_to_end', methods=['POST'])
def vote_to_end():
    """Decide whether to END the game or BANISH again (Final 4 mechanic)."""
    global agent

    if not agent:
        return jsonify({'error': 'Agent not initialized'}), 503

    try:
        data = request.json

        # Update agent's game state
        agent.game_state = deserialize_game_state(data['game_state'])
        agent.player = agent.game_state.get_player(agent.player.id)

        # Get suspicion scores from memory
        suspicions = agent.memory_manager.get_suspicions() if agent.memory_manager else {}

        if agent.player.role == Role.TRAITOR:
            # Traitor logic: Vote END if safe, otherwise BANISH
            alive_traitors = len([p for p in agent.game_state.alive_players if p.role == Role.TRAITOR])
            alive_faithful = len([p for p in agent.game_state.alive_players if p.role == Role.FAITHFUL])

            if alive_traitors >= alive_faithful:
                # Traitors have majority - vote END to win
                vote = "END"
                reasoning = "Traitor majority - safe to end game"
            else:
                # Need to eliminate more Faithful
                vote = "BANISH"
                reasoning = "Need to eliminate more Faithful first"
        else:
            # Faithful logic: Vote END only if 100% certain no Traitors remain
            # Check if any suspicion > 0.05
            max_suspicion = max(suspicions.values()) if suspicions else 0.0

            # Personality affects threshold
            neuroticism = agent.player.personality.get('neuroticism', 0.5)
            threshold = 0.05 + (neuroticism * 0.15)  # More paranoid = higher threshold

            if max_suspicion > threshold:
                vote = "BANISH"
                reasoning = f"Still suspicious (max={max_suspicion:.2f}, threshold={threshold:.2f})"
            else:
                vote = "END"
                reasoning = "Confident all Traitors eliminated"

        logger.info(f"{agent.player.name} votes {vote}: {reasoning}")

        return jsonify({
            'vote': vote,
            'reasoning': reasoning
        })

    except Exception as e:
        logger.error(f"Error in vote_to_end: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/share_or_steal', methods=['POST'])
def share_or_steal():
    """Decide whether to SHARE or STEAL in Traitor's Dilemma (2 Traitors remaining)."""
    global agent

    if not agent:
        return jsonify({'error': 'Agent not initialized'}), 503

    if agent.player.role != Role.TRAITOR:
        return jsonify({'error': 'Only Traitors play the dilemma'}), 403

    try:
        data = request.json

        # Update agent's game state
        agent.game_state = deserialize_game_state(data['game_state'])
        agent.player = agent.game_state.get_player(agent.player.id)

        # Personality-based decision (Nash Equilibrium weighted by traits)
        agreeableness = agent.player.personality.get('agreeableness', 0.5)
        neuroticism = agent.player.personality.get('neuroticism', 0.5)

        # Base probability of sharing
        share_prob = agreeableness * 0.6 - neuroticism * 0.4 + 0.2

        # Clamp to [0, 1]
        share_prob = max(0.0, min(1.0, share_prob))

        import random
        decision = "SHARE" if random.random() < share_prob else "STEAL"

        reasoning = f"Personality-driven (agreeableness={agreeableness:.2f}, neuroticism={neuroticism:.2f})"

        logger.info(f"{agent.player.name} chooses to {decision}: {reasoning}")

        return jsonify({
            'decision': decision,
            'reasoning': reasoning
        })

    except Exception as e:
        logger.error(f"Error in share_or_steal: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/choose_seer_target', methods=['POST'])
def choose_seer_target():
    """Choose who to investigate with Seer power (UK S3+ mechanic).

    The Seer power is awarded to the top mission performer on Day 8+.
    The holder can investigate one player to learn their TRUE role.
    """
    global agent

    if not agent:
        return jsonify({'error': 'Agent not initialized'}), 503

    try:
        data = request.json

        # Update agent's game state
        agent.game_state = deserialize_game_state(data['game_state'])
        agent.player = agent.game_state.get_player(agent.player.id)

        # Get valid targets (cannot investigate self)
        valid_targets = [p for p in agent.game_state.alive_players if p.id != agent.player.id]

        if not valid_targets:
            return jsonify({'error': 'No valid targets'}), 400

        # Strategy: Investigate the player we're MOST suspicious of
        # This confirms our suspicion OR clears an innocent
        suspicions = agent.memory_manager.get_suspicions() if agent.memory_manager else {}

        if suspicions:
            # Filter to valid targets and find most suspicious
            target_suspicions = {pid: score for pid, score in suspicions.items()
                                  if any(p.id == pid for p in valid_targets)}
            if target_suspicions:
                target_id = max(target_suspicions.keys(), key=lambda k: target_suspicions[k])
                reasoning = f"Highest suspicion ({target_suspicions[target_id]:.2f})"
            else:
                # No suspicion data for targets, pick random
                import random
                target = random.choice(valid_targets)
                target_id = target.id
                reasoning = "Random selection (no suspicion data)"
        else:
            # No suspicion data, pick player with highest social influence
            # (they're most dangerous if Traitor)
            target = max(valid_targets, key=lambda p: p.stats.get('social_influence', 0.5))
            target_id = target.id
            reasoning = "Highest social influence (most dangerous if Traitor)"

        target_player = agent.game_state.get_player(target_id)
        logger.info(f"👁️  {agent.player.name} uses SEER power on {target_player.name}: {reasoning}")

        return jsonify({
            'target_player_id': target_id,
            'reasoning': reasoning
        })

    except Exception as e:
        logger.error(f"Error in choose_seer_target: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/seer_result', methods=['POST'])
def seer_result():
    """Receive the result of Seer investigation.

    This endpoint is called AFTER the Seer uses their power.
    The true role is revealed privately to the Seer.
    """
    global agent

    if not agent:
        return jsonify({'error': 'Agent not initialized'}), 503

    try:
        data = request.json
        target_player_id = data['target_player_id']
        true_role = data['true_role']  # "TRAITOR" or "FAITHFUL"

        # Get target name for logging
        target_player = agent.game_state.get_player(target_player_id) if agent.game_state else None
        target_name = target_player.name if target_player else target_player_id

        logger.info(f"👁️  {agent.player.name} LEARNS: {target_name} is a {true_role}")

        # Update suspicions based on TRUTH
        if agent.memory_manager:
            if true_role == "TRAITOR":
                # Confirmed Traitor - max suspicion
                agent.memory_manager.update_suspicion(
                    target_player_id,
                    target_name,
                    1.0,  # Absolute certainty
                    "Seer power revealed: TRAITOR"
                )
                logger.info(f"   Suspicion of {target_name} set to 1.0 (CONFIRMED TRAITOR)")
            else:
                # Confirmed Faithful - clear suspicion
                agent.memory_manager.update_suspicion(
                    target_player_id,
                    target_name,
                    0.0,  # Complete trust
                    "Seer power revealed: FAITHFUL"
                )
                logger.info(f"   Suspicion of {target_name} set to 0.0 (CONFIRMED FAITHFUL)")

        return jsonify({
            'status': 'acknowledged',
            'player_id': agent.player.id
        })

    except Exception as e:
        logger.error(f"Error in seer_result: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/create_death_list', methods=['POST'])
def create_death_list():
    """Create Death List - pre-select 3-4 murder candidates (Traitors only).

    This mechanic restricts Traitor murder options. The Death List is created
    during the turret phase when Traitors have been "too efficient".

    Strategic considerations:
    - Include players who are suspicious of us (eliminate threats)
    - Include players who could expose our identity
    - Can include self for strategic misdirection
    """
    global agent

    if not agent:
        return jsonify({'error': 'Agent not initialized'}), 503

    if agent.player.role != Role.TRAITOR:
        return jsonify({'error': 'Only Traitors create Death List'}), 403

    try:
        data = request.json
        num_candidates = data.get('num_candidates', 3)

        # Update agent's game state
        agent.game_state = deserialize_game_state(data['game_state'])
        agent.player = agent.game_state.get_player(agent.player.id)

        # Get alive Faithful (valid death list targets)
        faithful_players = [p for p in agent.game_state.alive_players if p.role == Role.FAITHFUL]

        if len(faithful_players) == 0:
            return jsonify({'death_list': []})

        if len(faithful_players) <= num_candidates:
            # All Faithful go on the list
            death_list = [p.id for p in faithful_players]
            reasoning = "All remaining Faithful included"
        else:
            # Strategic selection: prioritize threats
            # 1. Players with high social influence (dangerous accusers)
            # 2. Players who might be suspicious of us

            # Score each Faithful by threat level
            threat_scores = {}
            for p in faithful_players:
                score = 0.0
                # High social influence = dangerous accuser
                score += p.stats.get('social_influence', 0.5) * 2.0
                # High conscientiousness = methodical, dangerous
                score += p.personality.get('conscientiousness', 0.5) * 1.0
                # Low agreeableness = more likely to accuse
                score += (1.0 - p.personality.get('agreeableness', 0.5)) * 1.0
                threat_scores[p.id] = score

            # Sort by threat score (highest first)
            sorted_faithful = sorted(faithful_players, key=lambda p: threat_scores[p.id], reverse=True)
            death_list = [p.id for p in sorted_faithful[:num_candidates]]

            # Log the names
            death_list_names = [agent.game_state.get_player(pid).name for pid in death_list]
            reasoning = f"Highest threat scores: {', '.join(death_list_names)}"

        logger.info(f"📜 {agent.player.name} creates DEATH LIST with {len(death_list)} candidates: {reasoning}")

        return jsonify({
            'death_list': death_list,
            'reasoning': reasoning
        })

    except Exception as e:
        logger.error(f"Error creating death list: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Get port from environment
    port = int(os.environ.get('PORT', 5000))

    # Get player ID from environment (for logging)
    player_id = os.environ.get('PLAYER_ID', 'unknown')

    logger.info(f"Starting agent service for {player_id} on port {port}")

    # Run Flask app
    app.run(host='0.0.0.0', port=port, debug=False)
