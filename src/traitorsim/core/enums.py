"""Enumerations for game states and roles."""

from enum import Enum


class GamePhase(Enum):
    """Game phase states representing the current point in the day/night cycle."""

    INIT = "initialization"
    BREAKFAST = "breakfast"
    MISSION = "mission"
    SOCIAL = "social"
    ROUNDTABLE = "round_table"
    TURRET = "turret"
    ENDED = "game_ended"


class Role(Enum):
    """Player roles in the game."""

    FAITHFUL = "faithful"
    TRAITOR = "traitor"
