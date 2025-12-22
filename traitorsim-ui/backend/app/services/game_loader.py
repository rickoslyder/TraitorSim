"""Game loader service - Parse and validate game JSON files."""

from typing import Any
from pydantic import BaseModel, Field
from enum import Enum


class Role(str, Enum):
    FAITHFUL = "faithful"
    TRAITOR = "traitor"


class EventType(str, Enum):
    GAME_START = "GAME_START"
    DAY_START = "DAY_START"
    PHASE_CHANGE = "PHASE_CHANGE"
    MISSION_SUCCESS = "MISSION_SUCCESS"
    MISSION_FAIL = "MISSION_FAIL"
    SHIELD_AWARDED = "SHIELD_AWARDED"
    SEER_AWARDED = "SEER_AWARDED"
    DAGGER_AWARDED = "DAGGER_AWARDED"
    VOTE = "VOTE"
    TIE_VOTE = "TIE_VOTE"
    REVOTE = "REVOTE"
    BANISHMENT = "BANISHMENT"
    MURDER_ATTEMPT = "MURDER_ATTEMPT"
    MURDER_SUCCESS = "MURDER_SUCCESS"
    MURDER_BLOCKED = "MURDER_BLOCKED"
    RECRUITMENT_OFFER = "RECRUITMENT_OFFER"
    RECRUITMENT_ACCEPTED = "RECRUITMENT_ACCEPTED"
    RECRUITMENT_REFUSED = "RECRUITMENT_REFUSED"
    SEER_USED = "SEER_USED"
    VOTE_TO_END = "VOTE_TO_END"
    GAME_END = "GAME_END"


class Personality(BaseModel):
    openness: float = Field(ge=0.0, le=1.0)
    conscientiousness: float = Field(ge=0.0, le=1.0)
    extraversion: float = Field(ge=0.0, le=1.0)
    agreeableness: float = Field(ge=0.0, le=1.0)
    neuroticism: float = Field(ge=0.0, le=1.0)


class Stats(BaseModel):
    intellect: float = Field(ge=0.0, le=1.0)
    dexterity: float = Field(ge=0.0, le=1.0)
    composure: float = Field(ge=0.0, le=1.0)
    social_influence: float = Field(ge=0.0, le=1.0)


class Player(BaseModel):
    id: str
    name: str
    role: Role
    archetype: str = ""
    archetype_name: str = ""
    alive: bool = True
    eliminated_day: int | None = None
    elimination_type: str | None = None
    personality: Personality | None = None
    stats: Stats | None = None
    backstory: str | None = None


class GameEvent(BaseModel):
    type: EventType
    day: int
    phase: str
    actor: str | None = None
    target: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    narrative: str | None = None


class TrustSnapshot(BaseModel):
    day: int
    phase: str
    matrix: dict[str, dict[str, float]]


class GameSession(BaseModel):
    """Complete game session data."""
    total_days: int
    prize_pot: int
    winner: str
    rule_variant: str = "uk"
    players: dict[str, Player]
    events: list[GameEvent]
    trust_snapshots: list[TrustSnapshot] = Field(default_factory=list)


def validate_game_data(data: dict) -> GameSession:
    """Validate and parse raw game JSON data."""
    return GameSession(**data)
