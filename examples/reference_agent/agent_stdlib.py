#!/usr/bin/env python3
"""TraitorSim Reference Agent — stdlib-only HTTP server (no Flask required).

Protocol v1.0: /health, /initialize, /vote, /reflect, /get_suspicions,
/choose_murder_victim, etc.

Usage:
    python3 agent_stdlib.py --port 9090
"""

import argparse
import json
import logging
import os
import random
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent state
# ---------------------------------------------------------------------------

class AgentState:
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
    return [p for p in game_state.get("players", []) if p["alive"] and p["id"] != state.player_id]


def get_alive_faithful_targets(game_state: Dict) -> List[Dict]:
    fellow_ids = {t["id"] for t in state.fellow_traitors}
    return [p for p in game_state.get("players", []) if p["alive"] and p["id"] != state.player_id and p["id"] not in fellow_ids]


def most_suspicious(players: List[Dict]) -> Dict:
    if not players:
        return {}
    return max(players, key=lambda p: state.suspicions.get(p["id"], 0.5))


def highest_social_influence(players: List[Dict]) -> Dict:
    if not players:
        return {}
    return max(players, key=lambda p: p.get("stats", {}).get("social_influence", 0.5))


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def _json_response(handler, data, status=200):
    body = json.dumps(data).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler) -> Dict:
    length = int(handler.headers.get("Content-Length", 0))
    return json.loads(handler.rfile.read(length)) if length > 0 else {}


def handle_health(handler):
    _json_response(handler, {
        "status": "ok",
        "agent_name": state.player_name or "ReferenceBot",
        "protocol_version": "1.0",
    })


def handle_initialize(handler):
    data = _read_json(handler)
    state.player = data["player"]
    state.role = data["player"]["role"]
    state.game_id = data.get("game_id", "")
    state.fellow_traitors = data.get("fellow_traitors", [])
    state.suspicions = {}
    state.vote_history = []
    state.day = 0
    logger.info(f"Initialized as {state.player_name} (role: {state.role}, game: {state.game_id})")
    if state.is_traitor:
        fellow_names = [t["name"] for t in state.fellow_traitors]
        logger.info(f"Fellow traitors: {fellow_names}")
    _json_response(handler, {"status": "initialized", "player_id": state.player_id, "player_name": state.player_name})


def handle_vote(handler):
    data = _read_json(handler)
    game_state = data["game_state"]
    eligible = data.get("eligible_targets", [])
    others = get_alive_others(game_state)
    if eligible:
        others = [p for p in others if p["id"] in eligible]
    if not others:
        return _json_response(handler, {"target_player_id": state.player_id, "reasoning": "No valid targets"})

    if state.is_traitor:
        faithful = get_alive_faithful_targets(game_state)
        targets = [p for p in faithful if p["id"] in [o["id"] for o in others]]
        target = highest_social_influence(targets) if targets else random.choice(others)
        reasoning = f"Targeting high-influence Faithful ({target['name']})" if targets else "Random (no clear Faithful target)"
    else:
        target = most_suspicious(others)
        sus = state.suspicions.get(target["id"], 0.5)
        reasoning = f"Most suspicious (suspicion: {sus:.2f})"

    logger.info(f"Voting for {target['name']}: {reasoning}")
    _json_response(handler, {"target_player_id": target["id"], "reasoning": reasoning, "voter_id": state.player_id})


def handle_reflect(handler):
    data = _read_json(handler)
    game_state = data["game_state"]
    events = data.get("events", [])
    state.day = game_state.get("day", state.day)

    for p in game_state.get("players", []):
        if p["id"] != state.player_id and p["id"] not in state.suspicions:
            fellow_ids = {t["id"] for t in state.fellow_traitors}
            state.suspicions[p["id"]] = 0.0 if p["id"] in fellow_ids else 0.5

    for event in events:
        event_lower = event.lower()
        if "was banished" in event_lower and "traitor" in event_lower:
            for pid in state.suspicions:
                state.suspicions[pid] = max(0.0, state.suspicions[pid] - 0.05)
        elif "was banished" in event_lower and "faithful" in event_lower:
            for pid in state.suspicions:
                state.suspicions[pid] = min(1.0, state.suspicions[pid] + 0.05)

    for pid in state.suspicions:
        state.suspicions[pid] = max(0.0, min(1.0, state.suspicions[pid]))

    logger.info(f"Reflected on {len(events)} events.")
    _json_response(handler, {"status": "completed", "player_id": state.player_id})


def handle_get_suspicions(handler):
    _json_response(handler, {"player_id": state.player_id, "suspicions": state.suspicions})


def handle_choose_murder_victim(handler):
    data = _read_json(handler)
    game_state = data["game_state"]
    death_list = data.get("death_list")
    targets = get_alive_faithful_targets(game_state)
    if death_list:
        targets = [p for p in targets if p["id"] in death_list]
    if not targets:
        return _json_response(handler, {"error": "No valid targets"}, 400)
    target = highest_social_influence(targets)
    logger.info(f"Murder target: {target['name']}")
    _json_response(handler, {"target_player_id": target["id"], "reasoning": f"Highest influence Faithful: {target['name']}", "traitor_id": state.player_id})


def handle_decide_recruitment(handler):
    data = _read_json(handler)
    is_ultimatum = data.get("is_ultimatum", False)
    if is_ultimatum:
        return _json_response(handler, {"accepts": True, "reasoning": "Survival — accepting ultimatum"})
    agreeableness = state.personality.get("agreeableness", 0.5)
    neuroticism = state.personality.get("neuroticism", 0.5)
    accepts = (agreeableness + neuroticism) / 2 > 0.6
    _json_response(handler, {"accepts": accepts, "reasoning": f"Personality-based (A={agreeableness:.2f}, N={neuroticism:.2f})"})


def handle_vote_to_end(handler):
    data = _read_json(handler)
    game_state = data["game_state"]
    if state.is_traitor:
        fellow_ids = {t["id"] for t in state.fellow_traitors} | {state.player_id}
        alive = [p for p in game_state["players"] if p["alive"]]
        traitor_count = sum(1 for p in alive if p["id"] in fellow_ids)
        faithful_count = len(alive) - traitor_count
        vote = "END" if traitor_count >= faithful_count else "BANISH"
        return _json_response(handler, {"vote": vote, "reasoning": "Traitor majority" if vote == "END" else "Need more eliminations"})
    max_sus = max(state.suspicions.values()) if state.suspicions else 0.5
    vote = "END" if max_sus < 0.15 else "BANISH"
    _json_response(handler, {"vote": vote, "reasoning": f"Max suspicion: {max_sus:.2f}"})


def handle_share_or_steal(handler):
    agreeableness = state.personality.get("agreeableness", 0.5)
    decision = "SHARE" if agreeableness > 0.5 else "STEAL"
    _json_response(handler, {"decision": decision, "reasoning": f"Agreeableness={agreeableness:.2f}"})


ROUTES = {
    "/health": ("GET", handle_health),
    "/initialize": ("POST", handle_initialize),
    "/vote": ("POST", handle_vote),
    "/reflect": ("POST", handle_reflect),
    "/get_suspicions": ("GET", handle_get_suspicions),
    "/choose_murder_victim": ("POST", handle_choose_murder_victim),
    "/decide_recruitment": ("POST", handle_decide_recruitment),
    "/vote_to_end": ("POST", handle_vote_to_end),
    "/share_or_steal": ("POST", handle_share_or_steal),
}


class AgentHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        route = ROUTES.get(path)
        if route and route[0] == "GET":
            route[1](self)
        else:
            self.send_response(404, "Not Found")
            self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path
        route = ROUTES.get(path)
        if route and route[0] == "POST":
            route[1](self)
        else:
            self.send_response(404, "Not Found")
            self.end_headers()

    def log_message(self, format, *args):
        logger.info(f"{self.client_address[0]} - {format % args}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TraitorSim Reference Agent (stdlib)")
    parser.add_argument("--port", type=int, default=9090)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), AgentHandler)
    logger.info(f"Reference agent running on {args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
