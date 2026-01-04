"""Mission types for TraitorSim.

Each mission tests different player attributes and creates opportunities
for trust matrix updates and strategic gameplay.
"""

from .base import BaseMission, MissionResult
from .skill_check import SkillCheckMission
from .funeral import FuneralMission
from .laser_heist import LaserHeistMission
from .cabin_creepies import CabinCreepiesMission
from .crossbow import CrossbowMission

# All available mission types
MISSION_TYPES = [
    SkillCheckMission,
    FuneralMission,
    LaserHeistMission,
    CabinCreepiesMission,
    CrossbowMission,
]

# Mission names for display
MISSION_NAMES = {
    SkillCheckMission: "Skill Check",
    FuneralMission: "The Funeral",
    LaserHeistMission: "Laser Heist",
    CabinCreepiesMission: "Cabin Creepies",
    CrossbowMission: "Crossbow Challenge",
}

__all__ = [
    "BaseMission",
    "MissionResult",
    "SkillCheckMission",
    "FuneralMission",
    "LaserHeistMission",
    "CabinCreepiesMission",
    "CrossbowMission",
    "MISSION_TYPES",
    "MISSION_NAMES",
]
