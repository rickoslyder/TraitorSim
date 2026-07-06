#!/usr/bin/env python3
"""TraitorSim Reference Agent - minimal implementation of the Agent Protocol v1.

This is a simple rule-based agent that demonstrates the HTTP API contract
required to participate in TraitorSim Arena games. It uses heuristic
strategies rather than LLM reasoning.

Usage:
    # Start the agent server
    python agent.py --port 8080

    # Register with the arena
    curl -X POST https://traitorsim.rbnk.uk/api/arena/register \\
        -H "Content-Type: application/json" \\
        -d '{"name": "ReferenceBot", "callback_url": "https://your-agent.example.com:8080"}'

Requirements:
    pip install flask
"""

import argparse
import logging
import os
import random
from typing import Any, Dict, List, Optional

from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Agent state (persisted in memory for simplicity)
# ---------------------------------------------------------------------------

class AgentState:
    """In-memory state for the reference agent."""

    def __init__(self):
        self.player: Optional[Dict[str, Any]] = None
        self.game_id: str = ""
        self.role: str = ""
        self.fellow_traitors: List[Dict[str, str]] = []
        self.suspicions: Dict[str, float] = {}
        self.vote_history: List[Dict[str, str]] = []
        self.day: int = 0

    @property
    def is_traitor(self) -> bool:
        return self.role == "traitor"

    @property
    def player_id(self) -> str:
        return self.player["id"] if self.player else ""

    @property
    def player_name(self) -> str:
        return self.player["name"] if self.player else ""

    @property
    def personality(self) -> Dict[str, float]:
        return self.player.get("personality", {}) if self.player else {}


state = AgentState()


# ---------------------------------------------------------------------------
# Strategy helpers
# ---------------------------------------------------------------------------

def get_alive_others(game_state: Dict) -> List[Dict]:
    """Get alive players excluding self."""
    return [
        p for p in game_state.get("players", [])
        if p["alive"] and p["id"] != state.player_id
    ]


def get_alive_faithful_targets(game_state: Dict) -> List[Dict]:
    """Get alive players who are known Faithful (for Traitor murder targeting)."""
    fellow_ids = {t["id"] for t in state.fellow_traitors}
    return [
        p for p in game_state.get("players", [])
        if p["alive"] and p["id"] != state.player_id and p["id"] not in fellow_ids
    ]


def most_suspicious(players: List[Dict]) -> Dict:
    """Pick the player we're most suspicious of."""
    if not players:
        return {}

    def suspicion_score(p: Dict) -> float:
        return state.suspicions.get(p["id"], 0.5)

    return max(players, key=suspicion_score)


def highest_social_influence(players: List[Dict]) -> Dict:
    """Pick the player with highest social influence."""
    if not players:
        return {}
    return max(players, key=lambda p: p.get("stats", {}).get("social_influence", 0.5))


# ---------------------------------------------------------------------------
# Required endpoints
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    """Health check - required by protocol."""
    return jsonify({
        "status": "ok",
        "agent_name": state.player_name or "ReferenceBot",
        "protocol_version": "1.0",
    })


@app.route("/initialize", methods=["POST"])
def initialize():
    """Initialize agent with player configuration."""
    data = request.json

    state.player = data["player"]
    state.role = data["player"]["role"]
    state.game_id = data.get("game_id", "")
    state.fellow_traitors = data.get("fellow_traitors", [])
    state.suspicions = {}
    state.vote_history = []
    state.day = 0

    logger.info(
        f"Initialized as {state.player_name} "
        f"(role: {state.role}, game: {state.game_id})"
    )

    if state.is_traitor:
        fellow_names = [t["name"] for t in state.fellow_traitors]
        logger.info(f"Fellow traitors: {fellow_names}")

    return jsonify({
        "status": "initialized",
        "player_id": state.player_id,
        "player_name": state.player_name,
    })


@app.route("/vote", methods=["POST"])
def vote():
    """Cast a banishment vote.

    Strategy:
    - As Faithful: vote for most suspicious player
    - As Traitor: vote for highest-threat Faithful (high social influence)
    """
    data = request.json
    game_state = data["game_state"]
    eligible = data.get("eligible_targets", [])
    others = get_alive_others(game_state)

    # Filter to eligible if provided
    if eligible:
        others = [p for p in others if p["id"] in eligible]

    if not others:
        return jsonify({"target_player_id": state.player_id, "reasoning": "No valid targets"})

    if state.is_traitor:
        # Traitor strategy: vote for high-influence Faithful (bus-throw if needed)
        faithful_targets = get_alive_faithful_targets(game_state)
        targets = [p for p in faithful_targets if p["id"] in [o["id"] for o in others]]

        if targets:
            target = highest_social_influence(targets)
            reasoning = f"Targeting high-influence Faithful ({target['name']})"
        else:
            target = random.choice(others)
            reasoning = "Random vote (no clear Faithful target)"
    else:
        # Faithful strategy: vote for most suspicious
        target = most_suspicious(others)
        sus = state.suspicions.get(target["id"], 0.5)
        reasoning = f"Most suspicious player (suspicion: {sus:.2f})"

    logger.info(f"Voting for {target['name']}: {reasoning}")

    return jsonify({
        "target_player_id": target["id"],
        "reasoning": reasoning,
        "voter_id": state.player_id,
    })


@app.route("/reflect", methods=["POST"])
def reflect():
    """Process events and update suspicion scores.

    Simple Bayesian-style updates:
    - If a banished player was Traitor: reduce suspicion of voters who voted for them
    - If a banished player was Faithful: increase suspicion of voters who voted for them
    - Survival patterns: players who never get murdered get slight suspicion increase
    """
    data = request.json
    game_state = data["game_state"]
    events = data.get("events", [])

    state.day = game_state.get("day", state.day)

    # Initialize suspicions for new players
    for p in game_state.get("players", []):
        if p["id"] != state.player_id and p["id"] not in state.suspicions:
            # If we're traitor, mark fellow traitors with 0 suspicion
            fellow_ids = {t["id"] for t in state.fellow_traitors}
            if p["id"] in fellow_ids:
                state.suspicions[p["id"]] = 0.0
            else:
                state.suspicions[p["id"]] = 0.5  # Neutral starting point

    # Process events for suspicion updates
    for event in events:
        event_lower = event.lower()

        if "was banished" in event_lower and "traitor" in event_lower:
            # A traitor was correctly identified - slightly trust the herd
            for pid in state.suspicions:
                state.suspicions[pid] = max(0.0, state.suspicions[pid] - 0.05)

        elif "was banished" in event_lower and "faithful" in event_lower:
            # An innocent was banished - be more paranoid
            for pid in state.suspicions:
                state.suspicions[pid] = min(1.0, state.suspicions[pid] + 0.05)

        elif "was murdered" in event_lower:
            # Murder victim was definitely Faithful - they can't be traitor
            # Slightly increase suspicion of players who aren't being targeted
            pass

    # Clamp all suspicions to [0, 1]
    for pid in state.suspicions:
        state.suspicions[pid] = max(0.0, min(1.0, state.suspicions[pid]))

    logger.info(f"Reflected on {len(events)} events. Top suspect: {_top_suspect()}")

    return jsonify({"status": "completed", "player_id": state.player_id})


@app.route("/get_suspicions", methods=["GET"])
def get_suspicions():
    """Return current suspicion scores."""
    return jsonify({
        "player_id": state.player_id,
        "suspicions": state.suspicions,
    })


# ---------------------------------------------------------------------------
# Optional endpoints
# ---------------------------------------------------------------------------

@app.route("/choose_murder_victim", methods=["POST"])
def choose_murder_victim():
    """Choose a murder victim (Traitor only).

    Strategy: eliminate the highest social-influence Faithful.
    """
    data = request.json
    game_state = data["game_state"]
    death_list = data.get("death_list")

    targets = get_alive_faithful_targets(game_state)

    if death_list:
        targets = [p for p in targets if p["id"] in death_list]

    if not targets:
        return jsonify({"error": "No valid targets"}), 400

    target = highest_social_influence(targets)
    reasoning = f"Eliminating highest-influence Faithful: {target['name']}"

    logger.info(f"Murder target: {target['name']}: {reasoning}")

    return jsonify({
        "target_player_id": target["id"],
        "reasoning": reasoning,
        "traitor_id": state.player_id,
    })


@app.route("/decide_recruitment", methods=["POST"])
def decide_recruitment():
    """Decide whether to accept Traitor recruitment.

    Strategy: accept if ultimatum, otherwise personality-based.
    """
    data = request.json
    is_ultimatum = data.get("is_ultimatum", False)

    if is_ultimatum:
        return jsonify({"accepts": True, "reasoning": "Survival - accepting ultimatum"})

    # Personality-based: high agreeableness + neuroticism = more likely to accept
    agreeableness = state.personality.get("agreeableness", 0.5)
    neuroticism = state.personality.get("neuroticism", 0.5)
    accepts = (agreeableness + neuroticism) / 2 > 0.6

    return jsonify({
        "accepts": accepts,
        "reasoning": f"Personality-based (A={agreeableness:.2f}, N={neuroticism:.2f})",
    })


@app.route("/vote_to_end", methods=["POST"])
def vote_to_end():
    """Vote whether to END the game or continue BANISHing.

    Strategy:
    - Traitor: END if we have majority
    - Faithful: BANISH unless very low max suspicion
    """
    data = request.json
    game_state = data["game_state"]

    if state.is_traitor:
        fellow_ids = {t["id"] for t in state.fellow_traitors} | {state.player_id}
        alive = [p for p in game_state["players"] if p["alive"]]
        traitor_count = sum(1 for p in alive if p["id"] in fellow_ids)
        faithful_count = len(alive) - traitor_count

        if traitor_count >= faithful_count:
            return jsonify({"vote": "END", "reasoning": "Traitor majority - safe to end"})
        return jsonify({"vote": "BANISH", "reasoning": "Need more eliminations"})

    # Faithful: only end if low suspicion
    max_sus = max(state.suspicions.values()) if state.suspicions else 0.5
    if max_sus < 0.15:
        return jsonify({"vote": "END", "reasoning": f"Low suspicion (max={max_sus:.2f})"})

    return jsonify({"vote": "BANISH", "reasoning": f"Still suspicious (max={max_sus:.2f})"})


@app.route("/share_or_steal", methods=["POST"])
def share_or_steal():
    """Traitor's Dilemma: SHARE or STEAL."""
    agreeableness = state.personality.get("agreeableness", 0.5)
    decision = "SHARE" if agreeableness > 0.5 else "STEAL"

    return jsonify({
        "decision": decision,
        "reasoning": f"Agreeableness={agreeableness:.2f}",
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _top_suspect() -> str:
    """Get the name of the top suspect (for logging)."""
    if not state.suspicions:
        return "none"
    top_id = max(state.suspicions, key=state.suspicions.get)
    score = state.suspicions[top_id]
    return f"{top_id} ({score:.2f})"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TraitorSim Reference Agent")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    logger.info(f"Starting TraitorSim Reference Agent on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)
