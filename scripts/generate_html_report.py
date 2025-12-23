#!/usr/bin/env python3
"""Generate a beautiful HTML report from TraitorSim game logs.

Usage:
    # From Docker logs
    docker logs traitorsim-orchestrator 2>&1 | python scripts/generate_html_report.py

    # From a log file
    python scripts/generate_html_report.py < game_logs.txt

    # With output file
    python scripts/generate_html_report.py --output reports/game_001.html < logs.txt
"""

import re
import sys
import json
import argparse
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from enum import Enum


class EventType(Enum):
    GAME_START = "game_start"
    DAY_START = "day_start"
    BREAKFAST = "breakfast"
    MURDER_REVEAL = "murder_reveal"
    MISSION = "mission"
    SHIELD_AWARD = "shield_award"
    DAGGER_AWARD = "dagger_award"
    SEER_AWARD = "seer_award"
    SEER_USED = "seer_used"
    SOCIAL = "social"
    ROUND_TABLE = "round_table"
    VOTE = "vote"
    BANISHMENT = "banishment"
    TIE = "tie"
    TURRET = "turret"
    SHIELD_PROTECTION = "shield_protection"
    RECRUITMENT = "recruitment"
    DEATH_LIST = "death_list"
    VOTE_TO_END = "vote_to_end"
    TRAITORS_DILEMMA = "traitors_dilemma"
    GAME_END = "game_end"
    NARRATIVE = "narrative"


@dataclass
class GameEvent:
    """A single event in the game."""
    day: int
    phase: str
    event_type: EventType
    content: str
    players_involved: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class Player:
    """Player information extracted from logs."""
    name: str
    role: str = "Unknown"
    archetype: str = ""
    alive: bool = True
    fate: str = ""  # "murdered", "banished", "winner"
    eliminated_day: int = 0


@dataclass
class GameReport:
    """Complete game report data."""
    events: List[GameEvent] = field(default_factory=list)
    players: Dict[str, Player] = field(default_factory=dict)
    winner: str = ""
    total_days: int = 0
    prize_pot: int = 0
    traitors: List[str] = field(default_factory=list)
    faithfuls: List[str] = field(default_factory=list)


class LogParser:
    """Parse TraitorSim logs into structured events."""

    # Pattern to extract message from Python logging format:
    # HH:MM:SS - logger - LEVEL - message
    # or: YYYY-MM-DD HH:MM:SS,mmm - logger - LEVEL - message
    LOG_PREFIX_PATTERN = re.compile(
        r'^(?:\d{4}-\d{2}-\d{2}\s+)?'  # Optional date
        r'(?:\d{1,2}:\d{2}:\d{2}(?:,\d{3})?)\s+'  # Time with optional ms
        r'-\s+[^\s]+\s+'  # Logger name
        r'-\s+(?:DEBUG|INFO|WARNING|ERROR|CRITICAL)\s+'  # Log level
        r'-\s+'  # Separator
    )

    def __init__(self):
        self.report = GameReport()
        self.current_day = 0
        self.current_phase = ""

    def _extract_message(self, line: str) -> str:
        """Extract the actual log message, stripping Python logging prefix if present."""
        # Try to strip the logging prefix (timestamp - logger - LEVEL - )
        match = self.LOG_PREFIX_PATTERN.match(line)
        if match:
            return line[match.end():]
        return line

    def parse(self, log_text: str) -> GameReport:
        """Parse full log text into a GameReport."""
        lines = log_text.split('\n')

        for i, line in enumerate(lines):
            self._parse_line(line, i, lines)

        return self.report

    def _parse_line(self, line: str, index: int, all_lines: List[str]):
        """Parse a single log line."""
        line = line.strip()
        if not line:
            return

        # Extract actual message (strips Python logging prefix if present)
        message = self._extract_message(line)

        # Day header - check both the raw line and extracted message
        # Format: "DAY 2" (standalone) or inside log prefix
        day_match = re.match(r'^DAY (\d+)$', message)
        if day_match:
            self.current_day = int(day_match.group(1))
            self.report.total_days = max(self.report.total_days, self.current_day)
            self._add_event(EventType.DAY_START, f"Day {self.current_day} begins")
            return

        # Phase headers (use message for cleaner matching)
        if "--- Breakfast Phase ---" in message:
            self.current_phase = "breakfast"
            self._add_event(EventType.BREAKFAST, "Breakfast Phase")
        elif "--- Mission Phase ---" in message:
            self.current_phase = "mission"
            self._add_event(EventType.MISSION, "Mission Phase")
        elif "--- Social Phase ---" in message:
            self.current_phase = "social"
            self._add_event(EventType.SOCIAL, "Social Phase")
        elif "--- Round Table Phase ---" in message:
            self.current_phase = "round_table"
            self._add_event(EventType.ROUND_TABLE, "Round Table Phase")
        elif "--- Turret Phase ---" in message:
            self.current_phase = "turret"
            self._add_event(EventType.TURRET, "Turret Phase")
        elif "--- Vote to End ---" in message:
            self.current_phase = "vote_to_end"
            self._add_event(EventType.VOTE_TO_END, "Vote to End")

        # Murder reveal (breakfast)
        murder_match = re.search(r'"([^"]+) was found murdered', message)
        if murder_match:
            victim = murder_match.group(1)
            self._add_event(
                EventType.MURDER_REVEAL,
                f"{victim} was found murdered",
                players=[victim],
                metadata={"victim": victim}
            )
            self._update_player(victim, alive=False, fate="murdered", eliminated_day=self.current_day)

        # Shield protection
        shield_match = re.search(r'🛡️\s+([^\s]+(?:\s+[^\s]+)*?) was PROTECTED', message)
        if shield_match:
            player = shield_match.group(1).strip()
            self._add_event(
                EventType.SHIELD_PROTECTION,
                f"{player} was protected by the Shield!",
                players=[player]
            )

        # Shield award
        shield_award_match = re.search(r'🛡️\s+([^\s]+(?:\s+[^\s]+)*?) won the SHIELD', message)
        if shield_award_match:
            player = shield_award_match.group(1).strip()
            self._add_event(
                EventType.SHIELD_AWARD,
                f"{player} won the Shield",
                players=[player]
            )

        # Dagger award
        dagger_match = re.search(r'🗡️\s+([^\s]+(?:\s+[^\s]+)*?) (?:won the DAGGER|chose the DAGGER)', message)
        if dagger_match:
            player = dagger_match.group(1).strip()
            self._add_event(
                EventType.DAGGER_AWARD,
                f"{player} won the Dagger",
                players=[player]
            )

        # Seer power award
        seer_award_match = re.search(r'👁️\s+([^\s]+(?:\s+[^\s]+)*?) won the SEER POWER', message)
        if seer_award_match:
            player = seer_award_match.group(1).strip()
            self._add_event(
                EventType.SEER_AWARD,
                f"{player} won the Seer Power",
                players=[player]
            )

        # Seer used
        seer_learn_match = re.search(r'👁️\s+([^\s]+(?:\s+[^\s]+)*?) learns: ([^\s]+(?:\s+[^\s]+)*?) is a (TRAITOR|FAITHFUL)', message)
        if seer_learn_match:
            seer = seer_learn_match.group(1).strip()
            target = seer_learn_match.group(2).strip()
            role = seer_learn_match.group(3)
            self._add_event(
                EventType.SEER_USED,
                f"{seer} learns {target} is a {role}",
                players=[seer, target],
                metadata={"seer": seer, "target": target, "revealed_role": role}
            )

        # Voting
        vote_match = re.search(r'([^\s]+(?:\s+[^\s]+)*?) voted for ([^\s]+(?:\s+[^\s]+)*?)$', message)
        if vote_match and self.current_phase == "round_table":
            voter = vote_match.group(1).strip()
            target = vote_match.group(2).strip()
            self._add_event(
                EventType.VOTE,
                f"{voter} voted for {target}",
                players=[voter, target],
                metadata={"voter": voter, "target": target}
            )

        # Banishment
        banish_match = re.search(r'([^\s]+(?:\s+[^\s]+)*?) has been BANISHED', message)
        if banish_match:
            player = banish_match.group(1).strip()
            self._add_event(
                EventType.BANISHMENT,
                f"{player} has been banished",
                players=[player]
            )
            self._update_player(player, alive=False, fate="banished", eliminated_day=self.current_day)

        # Role reveal on banishment
        role_reveal = re.search(r'([^\s]+(?:\s+[^\s]+)*?) was a (TRAITOR|FAITHFUL)', message)
        if role_reveal:
            player = role_reveal.group(1).strip()
            role = role_reveal.group(2)
            self._update_player(player, role=role)
            if role == "TRAITOR":
                if player not in self.report.traitors:
                    self.report.traitors.append(player)
            else:
                if player not in self.report.faithfuls:
                    self.report.faithfuls.append(player)

        # 2025 rule - no reveal
        no_reveal_match = re.search(r"2025 RULE: ([^\s]+(?:\s+[^\s]+)*?)'s role is NOT revealed", message)
        if no_reveal_match:
            player = no_reveal_match.group(1).strip()
            self._add_event(
                EventType.NARRATIVE,
                f"2025 Rule: {player}'s role remains hidden",
                players=[player]
            )

        # Tie detected
        if "TIE:" in message:
            self._add_event(EventType.TIE, message)

        # Death list
        death_list_match = re.search(r'📜 DEATH LIST: (.+)$', message)
        if death_list_match:
            names = death_list_match.group(1)
            self._add_event(
                EventType.DEATH_LIST,
                f"Death List: {names}",
                metadata={"death_list": names}
            )

        # Recruitment
        recruitment_match = re.search(r'(RECRUITMENT|ULTIMATUM): ([^\s]+(?:\s+[^\s]+)*?)$', message)
        if recruitment_match:
            offer_type = recruitment_match.group(1)
            target = recruitment_match.group(2).strip()
            self._add_event(
                EventType.RECRUITMENT,
                f"{offer_type} offered to {target}",
                players=[target],
                metadata={"type": offer_type}
            )

        # Recruitment accept/refuse
        accept_match = re.search(r'✅ ([^\s]+(?:\s+[^\s]+)*?) ACCEPTED recruitment', message)
        if accept_match:
            player = accept_match.group(1).strip()
            self._add_event(
                EventType.RECRUITMENT,
                f"{player} ACCEPTED recruitment - now a Traitor!",
                players=[player],
                metadata={"accepted": True}
            )
            self._update_player(player, role="TRAITOR (recruited)")
            if player not in self.report.traitors:
                self.report.traitors.append(player)

        refuse_match = re.search(r'❌ ([^\s]+(?:\s+[^\s]+)*?) REFUSED', message)
        if refuse_match:
            player = refuse_match.group(1).strip()
            self._add_event(
                EventType.RECRUITMENT,
                f"{player} REFUSED recruitment",
                players=[player],
                metadata={"accepted": False}
            )

        # Murder by traitors
        traitor_murder_match = re.search(r'Traitors murdered: ([^\s]+(?:\s+[^\s]+)*?)$', message)
        if traitor_murder_match:
            victim = traitor_murder_match.group(1).strip()
            # Already handled by murder reveal at breakfast

        # Game winner
        winner_match = re.search(r'WINNERS: (TRAITOR|FAITHFUL)', message)
        if winner_match:
            self.report.winner = winner_match.group(1)
            self._add_event(
                EventType.GAME_END,
                f"Game Over - {self.report.winner}S WIN!",
                metadata={"winner": self.report.winner}
            )

        # Prize pot (handle both $ and £)
        pot_match = re.search(r'Prize pot: [£$]?([\d,]+)', message)
        if pot_match:
            self.report.prize_pot = int(pot_match.group(1).replace(',', ''))

        # Traitor's Dilemma
        if "TRAITOR'S DILEMMA" in message:
            self._add_event(EventType.TRAITORS_DILEMMA, "Traitor's Dilemma begins")

        dilemma_choice = re.search(r'([^\s]+(?:\s+[^\s]+)*?) chose: (SHARE|STEAL)', message)
        if dilemma_choice:
            player = dilemma_choice.group(1).strip()
            choice = dilemma_choice.group(2)
            self._add_event(
                EventType.TRAITORS_DILEMMA,
                f"{player} chose {choice}",
                players=[player],
                metadata={"choice": choice}
            )

        # Player initialization (from game start)
        # Format: "3 Traitors: Alice, Bob, Charlie" or "Traitors: ['Player1', 'Player2']"
        player_init = re.search(r'(\d+) Traitors?: (.+)$', message)
        if player_init:
            traitors = player_init.group(2).split(', ')
            for t in traitors:
                t = t.strip()
                self._update_player(t, role="TRAITOR")
                if t not in self.report.traitors:
                    self.report.traitors.append(t)

        # Alternative format: "Traitors: ['Player6', 'Player7', 'Player14']"
        traitor_list_match = re.search(r"Traitors: \[([^\]]+)\]", message)
        if traitor_list_match:
            # Parse Python-style list
            traitor_str = traitor_list_match.group(1)
            # Extract quoted names
            traitors = re.findall(r"'([^']+)'", traitor_str)
            for t in traitors:
                t = t.strip()
                self._update_player(t, role="TRAITOR")
                if t not in self.report.traitors:
                    self.report.traitors.append(t)

        # Player count: "Initialized 24 players"
        player_count_match = re.search(r'Initialized (\d+) players?', message)
        if player_count_match:
            count = int(player_count_match.group(1))
            # Initialize placeholder players if we don't have them yet
            for i in range(count):
                player_name = f"Player{i}"
                if player_name not in self.report.players:
                    self._update_player(player_name, role="FAITHFUL")
                    if player_name not in self.report.faithfuls:
                        self.report.faithfuls.append(player_name)

    def _add_event(self, event_type: EventType, content: str,
                   players: List[str] = None, metadata: Dict = None):
        """Add an event to the report."""
        event = GameEvent(
            day=self.current_day,
            phase=self.current_phase,
            event_type=event_type,
            content=content,
            players_involved=players or [],
            metadata=metadata or {}
        )
        self.report.events.append(event)

    def _update_player(self, name: str, **kwargs):
        """Update player information."""
        if name not in self.report.players:
            self.report.players[name] = Player(name=name)

        player = self.report.players[name]
        for key, value in kwargs.items():
            if hasattr(player, key):
                setattr(player, key, value)


def generate_html(report: GameReport) -> str:
    """Generate HTML report from parsed game data."""

    # Group events by day
    events_by_day: Dict[int, List[GameEvent]] = {}
    for event in report.events:
        day = event.day
        if day not in events_by_day:
            events_by_day[day] = []
        events_by_day[day].append(event)

    # Build player cards
    player_cards = []
    for name, player in sorted(report.players.items()):
        status_class = "alive" if player.alive else "eliminated"
        role_class = "traitor" if "TRAITOR" in player.role else "faithful" if player.role != "Unknown" else ""
        fate_icon = ""
        if player.fate == "murdered":
            fate_icon = "💀"
        elif player.fate == "banished":
            fate_icon = "🚪"
        elif report.winner and player.alive:
            fate_icon = "🏆"

        player_cards.append(f'''
            <div class="player-card {status_class} {role_class}">
                <div class="player-avatar">{name[0]}</div>
                <div class="player-name">{name}</div>
                <div class="player-role">{player.role}</div>
                <div class="player-fate">{fate_icon} {player.fate.title() if player.fate else "Alive"}</div>
                {f'<div class="player-day">Day {player.eliminated_day}</div>' if player.eliminated_day else ''}
            </div>
        ''')

    # Build timeline
    timeline_html = []
    for day in sorted(events_by_day.keys()):
        if day == 0:
            continue  # Skip pre-game events

        events = events_by_day[day]
        day_events = []

        for event in events:
            if event.event_type == EventType.DAY_START:
                continue  # Skip day markers in event list

            icon = _get_event_icon(event.event_type)
            css_class = _get_event_class(event.event_type)

            day_events.append(f'''
                <div class="event {css_class}">
                    <span class="event-icon">{icon}</span>
                    <span class="event-content">{event.content}</span>
                </div>
            ''')

        if day_events:
            timeline_html.append(f'''
                <div class="day-section">
                    <div class="day-header">
                        <span class="day-number">Day {day}</span>
                    </div>
                    <div class="day-events">
                        {''.join(day_events)}
                    </div>
                </div>
            ''')

    # Winner announcement
    winner_section = ""
    if report.winner:
        winner_class = "traitor-win" if report.winner == "TRAITOR" else "faithful-win"
        winner_section = f'''
            <div class="winner-banner {winner_class}">
                <h2>🏆 {report.winner}S WIN! 🏆</h2>
                <p>Final Prize Pot: ${report.prize_pot:,}</p>
            </div>
        '''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TraitorSim Game Report</title>
    <style>
        :root {{
            --bg-dark: #1a1a2e;
            --bg-card: #16213e;
            --accent-red: #e94560;
            --accent-gold: #ffd700;
            --accent-green: #4ecca3;
            --text-light: #eaeaea;
            --text-muted: #8892b0;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--bg-dark) 0%, #0f0f23 100%);
            color: var(--text-light);
            min-height: 100vh;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}

        header {{
            text-align: center;
            padding: 3rem 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 2rem;
        }}

        h1 {{
            font-size: 3rem;
            background: linear-gradient(45deg, var(--accent-red), var(--accent-gold));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }}

        .subtitle {{
            color: var(--text-muted);
            font-size: 1.2rem;
        }}

        .stats {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 1.5rem;
            flex-wrap: wrap;
        }}

        .stat {{
            background: var(--bg-card);
            padding: 1rem 2rem;
            border-radius: 10px;
            text-align: center;
        }}

        .stat-value {{
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent-gold);
        }}

        .stat-label {{
            color: var(--text-muted);
            font-size: 0.9rem;
        }}

        .winner-banner {{
            text-align: center;
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
        }}

        .traitor-win {{
            background: linear-gradient(135deg, rgba(233, 69, 96, 0.3), rgba(233, 69, 96, 0.1));
            border: 2px solid var(--accent-red);
        }}

        .faithful-win {{
            background: linear-gradient(135deg, rgba(78, 204, 163, 0.3), rgba(78, 204, 163, 0.1));
            border: 2px solid var(--accent-green);
        }}

        section {{
            margin-bottom: 3rem;
        }}

        h2 {{
            font-size: 1.8rem;
            margin-bottom: 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--accent-red);
        }}

        .players-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 1rem;
        }}

        .player-card {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
            border: 2px solid transparent;
        }}

        .player-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }}

        .player-card.traitor {{
            border-color: var(--accent-red);
        }}

        .player-card.faithful {{
            border-color: var(--accent-green);
        }}

        .player-card.eliminated {{
            opacity: 0.6;
        }}

        .player-avatar {{
            width: 60px;
            height: 60px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--accent-red), var(--accent-gold));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: bold;
            margin: 0 auto 1rem;
        }}

        .player-card.faithful .player-avatar {{
            background: linear-gradient(135deg, var(--accent-green), #45b7a0);
        }}

        .player-name {{
            font-weight: bold;
            font-size: 1.1rem;
            margin-bottom: 0.25rem;
        }}

        .player-role {{
            color: var(--text-muted);
            font-size: 0.85rem;
        }}

        .player-fate {{
            margin-top: 0.5rem;
            font-size: 0.9rem;
        }}

        .player-day {{
            color: var(--text-muted);
            font-size: 0.8rem;
        }}

        .timeline {{
            position: relative;
        }}

        .timeline::before {{
            content: '';
            position: absolute;
            left: 30px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: linear-gradient(to bottom, var(--accent-red), var(--accent-gold));
        }}

        .day-section {{
            margin-bottom: 2rem;
            padding-left: 60px;
            position: relative;
        }}

        .day-header {{
            position: relative;
        }}

        .day-number {{
            position: absolute;
            left: -50px;
            width: 40px;
            height: 40px;
            background: var(--accent-red);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            font-size: 0.7rem;
        }}

        .day-events {{
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1rem;
        }}

        .event {{
            padding: 0.75rem;
            border-radius: 8px;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
        }}

        .event:last-child {{
            margin-bottom: 0;
        }}

        .event:hover {{
            background: rgba(255,255,255,0.05);
        }}

        .event-icon {{
            font-size: 1.2rem;
            min-width: 24px;
        }}

        .event-content {{
            flex: 1;
        }}

        .event.murder {{
            background: rgba(233, 69, 96, 0.15);
            border-left: 3px solid var(--accent-red);
        }}

        .event.shield {{
            background: rgba(255, 215, 0, 0.15);
            border-left: 3px solid var(--accent-gold);
        }}

        .event.banishment {{
            background: rgba(139, 69, 19, 0.2);
            border-left: 3px solid #8b4513;
        }}

        .event.seer {{
            background: rgba(138, 43, 226, 0.15);
            border-left: 3px solid #8a2be2;
        }}

        .event.game-end {{
            background: linear-gradient(135deg, rgba(255, 215, 0, 0.2), rgba(233, 69, 96, 0.2));
            border: 2px solid var(--accent-gold);
            font-weight: bold;
            font-size: 1.1rem;
        }}

        footer {{
            text-align: center;
            padding: 2rem;
            color: var(--text-muted);
            border-top: 1px solid rgba(255,255,255,0.1);
            margin-top: 2rem;
        }}

        @media (max-width: 768px) {{
            h1 {{
                font-size: 2rem;
            }}

            .stats {{
                flex-direction: column;
                align-items: center;
            }}

            .timeline::before {{
                left: 20px;
            }}

            .day-section {{
                padding-left: 45px;
            }}

            .day-number {{
                left: -35px;
                width: 30px;
                height: 30px;
                font-size: 0.6rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>TraitorSim</h1>
            <p class="subtitle">Game Report</p>
            <div class="stats">
                <div class="stat">
                    <div class="stat-value">{report.total_days}</div>
                    <div class="stat-label">Days Played</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(report.players)}</div>
                    <div class="stat-label">Players</div>
                </div>
                <div class="stat">
                    <div class="stat-value">{len(report.traitors)}</div>
                    <div class="stat-label">Traitors</div>
                </div>
                <div class="stat">
                    <div class="stat-value">${report.prize_pot:,}</div>
                    <div class="stat-label">Prize Pot</div>
                </div>
            </div>
        </header>

        {winner_section}

        <section>
            <h2>Players</h2>
            <div class="players-grid">
                {''.join(player_cards)}
            </div>
        </section>

        <section>
            <h2>Timeline</h2>
            <div class="timeline">
                {''.join(timeline_html)}
            </div>
        </section>

        <footer>
            <p>Generated by TraitorSim Report Generator</p>
            <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>

    <script>
        // Add smooth scrolling for timeline
        document.querySelectorAll('.day-header').forEach(header => {{
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => {{
                const events = header.nextElementSibling;
                events.style.display = events.style.display === 'none' ? 'block' : 'none';
            }});
        }});
    </script>
</body>
</html>'''

    return html


def _get_event_icon(event_type: EventType) -> str:
    """Get emoji icon for event type."""
    icons = {
        EventType.MURDER_REVEAL: "💀",
        EventType.SHIELD_PROTECTION: "🛡️",
        EventType.SHIELD_AWARD: "🛡️",
        EventType.DAGGER_AWARD: "🗡️",
        EventType.SEER_AWARD: "👁️",
        EventType.SEER_USED: "👁️",
        EventType.BANISHMENT: "🚪",
        EventType.VOTE: "🗳️",
        EventType.TIE: "⚖️",
        EventType.DEATH_LIST: "📜",
        EventType.RECRUITMENT: "🎭",
        EventType.VOTE_TO_END: "🏁",
        EventType.TRAITORS_DILEMMA: "⚔️",
        EventType.GAME_END: "🏆",
        EventType.BREAKFAST: "☀️",
        EventType.MISSION: "🎯",
        EventType.SOCIAL: "💬",
        EventType.ROUND_TABLE: "⭕",
        EventType.TURRET: "🌙",
    }
    return icons.get(event_type, "•")


def _get_event_class(event_type: EventType) -> str:
    """Get CSS class for event type."""
    classes = {
        EventType.MURDER_REVEAL: "murder",
        EventType.SHIELD_PROTECTION: "shield",
        EventType.SHIELD_AWARD: "shield",
        EventType.BANISHMENT: "banishment",
        EventType.SEER_AWARD: "seer",
        EventType.SEER_USED: "seer",
        EventType.GAME_END: "game-end",
    }
    return classes.get(event_type, "")


def main():
    parser = argparse.ArgumentParser(description='Generate HTML report from TraitorSim logs')
    parser.add_argument('--output', '-o', default='report.html', help='Output HTML file')
    parser.add_argument('--json', action='store_true', help='Also output JSON data')
    args = parser.parse_args()

    # Read log from stdin
    log_text = sys.stdin.read()

    if not log_text.strip():
        print("Error: No log data provided. Pipe logs to stdin.", file=sys.stderr)
        print("Usage: docker logs traitorsim-orchestrator 2>&1 | python scripts/generate_html_report.py", file=sys.stderr)
        sys.exit(1)

    # Parse logs
    log_parser = LogParser()
    report = log_parser.parse(log_text)

    # Generate HTML
    html = generate_html(report)

    # Write output
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"Report generated: {args.output}")

    # Optionally output JSON
    if args.json:
        json_output = args.output.replace('.html', '.json')
        data = {
            'total_days': report.total_days,
            'prize_pot': report.prize_pot,
            'winner': report.winner,
            'traitors': report.traitors,
            'faithfuls': report.faithfuls,
            'players': {name: asdict(p) for name, p in report.players.items()},
            'events': [
                {
                    'day': e.day,
                    'phase': e.phase,
                    'type': e.event_type.value,
                    'content': e.content,
                    'players': e.players_involved,
                    'metadata': e.metadata
                }
                for e in report.events
            ]
        }
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"JSON data: {json_output}")

    # Summary
    print(f"\nGame Summary:")
    print(f"  Days: {report.total_days}")
    print(f"  Players: {len(report.players)}")
    print(f"  Winner: {report.winner or 'Unknown'}")
    print(f"  Prize Pot: ${report.prize_pot:,}")


if __name__ == '__main__':
    main()
