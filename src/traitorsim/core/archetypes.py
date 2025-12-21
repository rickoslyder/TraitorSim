"""Casting archetypes from The Traitors World Bible.

Defines 13 distinct character archetypes with personality ranges,
demographic templates, and strategic profiles for grounded AI personas.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import random


@dataclass
class ArchetypeDefinition:
    """Definition of a casting archetype from World Bible."""

    id: str  # e.g., "prodigy", "charming_sociopath"
    name: str  # e.g., "The Prodigy"
    description: str  # Brief archetype description

    # OCEAN trait ranges (not single values - allow variance within archetype)
    ocean_ranges: Dict[str, Tuple[float, float]]
    # e.g., {"openness": (0.75, 0.95), "conscientiousness": (0.60, 0.85)}

    # Stat biases (skill ranges for missions)
    stat_ranges: Dict[str, Tuple[float, float]]
    # e.g., {"intellect": (0.70, 0.95), "social_influence": (0.60, 0.90)}

    # Demographic templates for Deep Research prompting
    age_range: Tuple[int, int] = (24, 55)  # Default adult range
    typical_occupations: List[str] = field(default_factory=list)
    geographic_bias: List[str] = field(default_factory=lambda: ["urban UK"])
    socioeconomic_class: List[str] = field(default_factory=lambda: ["middle-class"])

    # Strategic profile
    strategic_drive: str = "Survival"
    gameplay_tendency: str = "Cautious and observant"

    def sample_ocean(self) -> Dict[str, float]:
        """Sample OCEAN traits from archetype ranges."""
        return {
            trait: random.uniform(low, high)
            for trait, (low, high) in self.ocean_ranges.items()
        }

    def sample_stats(self) -> Dict[str, float]:
        """Sample mission stats from archetype ranges."""
        return {
            stat: random.uniform(low, high)
            for stat, (low, high) in self.stat_ranges.items()
        }

    def sample_demographics(self) -> Dict[str, any]:
        """Sample demographic template."""
        return {
            "age": random.randint(*self.age_range),
            "occupation": random.choice(self.typical_occupations) if self.typical_occupations else "student",
            "location": random.choice(self.geographic_bias),
            "socioeconomic": random.choice(self.socioeconomic_class)
        }


# ============================================================================
# ARCHETYPE REGISTRY - All 13 archetypes from World Bible
# ============================================================================

ARCHETYPE_REGISTRY: Dict[str, ArchetypeDefinition] = {

    # 1. The Prodigy
    "prodigy": ArchetypeDefinition(
        id="prodigy",
        name="The Prodigy",
        description="Exceptionally skilled Faithful who excels at identifying Traitors but is eliminated before the finale due to being a threat",
        ocean_ranges={
            "openness": (0.80, 0.95),
            "conscientiousness": (0.70, 0.90),
            "extraversion": (0.50, 0.75),
            "agreeableness": (0.45, 0.70),
            "neuroticism": (0.25, 0.50)
        },
        stat_ranges={
            "intellect": (0.75, 0.95),
            "dexterity": (0.60, 0.80),
            "social_influence": (0.60, 0.85)
        },
        age_range=(25, 40),
        typical_occupations=["data analyst", "teacher", "researcher", "software engineer", "psychologist"],
        geographic_bias=["London", "Manchester", "Edinburgh", "urban UK"],
        socioeconomic_class=["middle-class", "upper-middle"],
        strategic_drive="Truth-seeking and logical deduction",
        gameplay_tendency="Analytical; tracks voting patterns and behavioral tells"
    ),

    # 2. The Charming Sociopath
    "charming_sociopath": ArchetypeDefinition(
        id="charming_sociopath",
        name="The Charming Sociopath",
        description="Charismatic Traitor whose good looks and magnetic personality allow them to evade detection despite erratic behavior",
        ocean_ranges={
            "openness": (0.60, 0.80),
            "conscientiousness": (0.30, 0.55),
            "extraversion": (0.80, 0.95),
            "agreeableness": (0.20, 0.40),
            "neuroticism": (0.20, 0.45)
        },
        stat_ranges={
            "intellect": (0.55, 0.75),
            "dexterity": (0.60, 0.80),
            "social_influence": (0.80, 0.95)
        },
        age_range=(24, 38),
        typical_occupations=["sales executive", "influencer", "personal trainer", "bartender", "actor"],
        geographic_bias=["London", "Brighton", "Manchester", "urban UK"],
        socioeconomic_class=["working-class", "middle-class"],
        strategic_drive="Manipulation through charm and charisma",
        gameplay_tendency="Deflects suspicion with charm; builds loyal followers"
    ),

    # 3. The Misguided Survivor
    "misguided_survivor": ArchetypeDefinition(
        id="misguided_survivor",
        name="The Misguided Survivor",
        description="Players who conflate longevity with skill, failing to recognize they're kept around due to incompetence",
        ocean_ranges={
            "openness": (0.20, 0.40),
            "conscientiousness": (0.40, 0.65),
            "extraversion": (0.45, 0.70),
            "agreeableness": (0.55, 0.80),
            "neuroticism": (0.60, 0.85)
        },
        stat_ranges={
            "intellect": (0.30, 0.50),
            "dexterity": (0.35, 0.60),
            "social_influence": (0.40, 0.60)
        },
        age_range=(35, 60),
        typical_occupations=["retail worker", "call center agent", "delivery driver", "cleaner", "security guard"],
        geographic_bias=["suburban UK", "small towns", "provincial cities"],
        socioeconomic_class=["working-class", "lower-middle"],
        strategic_drive="Survival over strategy; believes longevity = competence",
        gameplay_tendency="Passive follower; survives by being non-threatening"
    ),

    # 4. The Comedic Psychic
    "comedic_psychic": ArchetypeDefinition(
        id="comedic_psychic",
        name="The Comedic Psychic",
        description="Attention-seeking players who make wild accusations and dramatic pronouncements about Traitor identities",
        ocean_ranges={
            "openness": (0.65, 0.85),
            "conscientiousness": (0.20, 0.45),
            "extraversion": (0.75, 0.95),
            "agreeableness": (0.35, 0.60),
            "neuroticism": (0.55, 0.80)
        },
        stat_ranges={
            "intellect": (0.40, 0.65),
            "dexterity": (0.45, 0.70),
            "social_influence": (0.60, 0.80)
        },
        age_range=(22, 45),
        typical_occupations=["comedian", "entertainer", "social media manager", "radio presenter", "party planner"],
        geographic_bias=["London", "Manchester", "Glasgow", "urban UK"],
        socioeconomic_class=["working-class", "middle-class"],
        strategic_drive="Entertainment and spotlight; craves attention",
        gameplay_tendency="Dramatic accusations; often wrong but memorable"
    ),

    # 5. The Bitter Traitor
    "bitter_traitor": ArchetypeDefinition(
        id="bitter_traitor",
        name="The Bitter Traitor",
        description="Banished Traitors who leave breadcrumbs pointing to their former allies out of spite",
        ocean_ranges={
            "openness": (0.45, 0.70),
            "conscientiousness": (0.35, 0.60),
            "extraversion": (0.40, 0.65),
            "agreeableness": (0.15, 0.35),
            "neuroticism": (0.65, 0.90)
        },
        stat_ranges={
            "intellect": (0.50, 0.75),
            "dexterity": (0.45, 0.70),
            "social_influence": (0.45, 0.70)
        },
        age_range=(28, 50),
        typical_occupations=["middle manager", "accountant", "IT support", "administrator", "council worker"],
        geographic_bias=["suburban UK", "Midlands", "Northern England"],
        socioeconomic_class=["lower-middle", "middle-class"],
        strategic_drive="Vengeance when betrayed; burns bridges",
        gameplay_tendency="Drops hints about fellow Traitors when banished"
    ),

    # 6. The Infatuated Faithful
    "infatuated_faithful": ArchetypeDefinition(
        id="infatuated_faithful",
        name="The Infatuated Faithful",
        description="Players whose romantic interest in a Traitor clouds their judgment, leading to disastrous decisions",
        ocean_ranges={
            "openness": (0.55, 0.80),
            "conscientiousness": (0.40, 0.65),
            "extraversion": (0.60, 0.85),
            "agreeableness": (0.75, 0.95),
            "neuroticism": (0.50, 0.75)
        },
        stat_ranges={
            "intellect": (0.30, 0.50),
            "dexterity": (0.50, 0.70),
            "social_influence": (0.55, 0.75)
        },
        age_range=(21, 35),
        typical_occupations=["nurse", "primary teacher", "care worker", "florist", "veterinary assistant"],
        geographic_bias=["suburban UK", "small towns", "rural areas"],
        socioeconomic_class=["working-class", "lower-middle"],
        strategic_drive="Emotional connection over logic; loyalty to crush",
        gameplay_tendency="Defends romantic interest despite red flags"
    ),

    # 7. The Quirky Outsider
    "quirky_outsider": ArchetypeDefinition(
        id="quirky_outsider",
        name="The Quirky Outsider",
        description="Neurodivergent or unconventional players who face undue suspicion simply for not conforming",
        ocean_ranges={
            "openness": (0.75, 0.95),
            "conscientiousness": (0.40, 0.70),
            "extraversion": (0.25, 0.55),
            "agreeableness": (0.50, 0.75),
            "neuroticism": (0.45, 0.70)
        },
        stat_ranges={
            "intellect": (0.65, 0.90),
            "dexterity": (0.40, 0.65),
            "social_influence": (0.35, 0.60)
        },
        age_range=(22, 45),
        typical_occupations=["librarian", "archivist", "graphic designer", "researcher", "museum curator"],
        geographic_bias=["Brighton", "Edinburgh", "Cambridge", "quirky UK towns"],
        socioeconomic_class=["middle-class", "upper-middle"],
        strategic_drive="Authenticity; misunderstood for being different",
        gameplay_tendency="Misread due to unconventional behavior patterns"
    ),

    # 8. The Incompetent Authority
    "incompetent_authority": ArchetypeDefinition(
        id="incompetent_authority",
        name="The Incompetent Authority Figure",
        description="Retired law enforcement or military personnel who play so poorly it raises concerns about their professional competence",
        ocean_ranges={
            "openness": (0.30, 0.50),
            "conscientiousness": (0.60, 0.80),  # Facade
            "extraversion": (0.55, 0.75),
            "agreeableness": (0.40, 0.65),
            "neuroticism": (0.35, 0.60)
        },
        stat_ranges={
            "intellect": (0.30, 0.50),  # Low actual intellect despite facade
            "dexterity": (0.50, 0.70),
            "social_influence": (0.55, 0.75)  # Relies on authority
        },
        age_range=(45, 65),
        typical_occupations=["retired police officer", "ex-military", "former detective", "security consultant", "probation officer"],
        geographic_bias=["suburban UK", "provincial cities", "military towns"],
        socioeconomic_class=["middle-class", "upper-middle"],
        strategic_drive="Leverage perceived credibility; overconfident",
        gameplay_tendency="Trusted initially due to background; makes poor deductions"
    ),

    # 9. The Zealot
    "zealot": ArchetypeDefinition(
        id="zealot",
        name="The Zealot",
        description="Players who immerse themselves completely in their role, taking it on as core personality; potentially sanctimonious",
        ocean_ranges={
            "openness": (0.20, 0.40),
            "conscientiousness": (0.75, 0.95),
            "extraversion": (0.50, 0.75),
            "agreeableness": (0.30, 0.55),
            "neuroticism": (0.40, 0.65)
        },
        stat_ranges={
            "intellect": (0.55, 0.80),
            "dexterity": (0.50, 0.75),
            "social_influence": (0.60, 0.80)
        },
        age_range=(30, 55),
        typical_occupations=["charity worker", "religious leader", "teacher", "activist", "politician"],
        geographic_bias=["across UK", "urban and rural"],
        socioeconomic_class=["middle-class", "upper-middle"],
        strategic_drive="Moral righteousness; sees game as crusade",
        gameplay_tendency="High conviction; sanctimonious about 'playing fairly'"
    ),

    # 10. The Romantic
    "romantic": ArchetypeDefinition(
        id="romantic",
        name="The Romantic",
        description="Believes being a Traitor is inherently evil; assumes friends would never betray them",
        ocean_ranges={
            "openness": (0.60, 0.85),
            "conscientiousness": (0.50, 0.75),
            "extraversion": (0.65, 0.90),
            "agreeableness": (0.80, 0.95),
            "neuroticism": (0.35, 0.60)
        },
        stat_ranges={
            "intellect": (0.45, 0.70),
            "dexterity": (0.50, 0.75),
            "social_influence": (0.65, 0.85)
        },
        age_range=(24, 42),
        typical_occupations=["wedding planner", "poet", "artist", "musician", "counselor"],
        geographic_bias=["London", "Oxford", "Bath", "romantic UK cities"],
        socioeconomic_class=["middle-class", "upper-middle"],
        strategic_drive="Friendship loyalty; naively trusting",
        gameplay_tendency="Refuses to suspect friends; overlaps with 'mission performance = Faithful'"
    ),

    # 11. The Smug Player
    "smug_player": ArchetypeDefinition(
        id="smug_player",
        name="The Smug Player",
        description="Exhibits moral superiority, admonishing others for unethical play or 'dirty' tactics",
        ocean_ranges={
            "openness": (0.45, 0.70),
            "conscientiousness": (0.65, 0.85),
            "extraversion": (0.55, 0.80),
            "agreeableness": (0.25, 0.45),
            "neuroticism": (0.30, 0.55)
        },
        stat_ranges={
            "intellect": (0.60, 0.85),
            "dexterity": (0.50, 0.75),
            "social_influence": (0.55, 0.80)
        },
        age_range=(28, 50),
        typical_occupations=["lawyer", "university lecturer", "journalist", "doctor", "civil servant"],
        geographic_bias=["London", "Oxford", "Cambridge", "Edinburgh"],
        socioeconomic_class=["upper-middle", "upper"],
        strategic_drive="Moral superiority; judges others' tactics",
        gameplay_tendency="Sanctimonious about 'proper' gameplay; alienates others"
    ),

    # 12. The Mischievous Operator
    "mischievous_operator": ArchetypeDefinition(
        id="mischievous_operator",
        name="The Mischievous Operator",
        description="Employs Machiavellian tactics, forms overt alliances, and clearly enjoys the thrill of deception",
        ocean_ranges={
            "openness": (0.70, 0.90),
            "conscientiousness": (0.30, 0.50),
            "extraversion": (0.70, 0.90),
            "agreeableness": (0.25, 0.50),
            "neuroticism": (0.25, 0.50)
        },
        stat_ranges={
            "intellect": (0.65, 0.90),
            "dexterity": (0.60, 0.85),
            "social_influence": (0.75, 0.95)
        },
        age_range=(25, 45),
        typical_occupations=["political strategist", "poker player", "entrepreneur", "marketing executive", "game designer"],
        geographic_bias=["London", "Manchester", "Bristol", "urban UK"],
        socioeconomic_class=["middle-class", "upper-middle"],
        strategic_drive="Machiavellian manipulation; thrill of the game",
        gameplay_tendency="Forms alliances; bends truth; enjoys strategic chaos"
    ),

    # 13. The Charismatic Leader
    "charismatic_leader": ArchetypeDefinition(
        id="charismatic_leader",
        name="The Charismatic Leader",
        description="Highly valued team member with strong influence over Round Table discussions; dangerous as Traitor, helpful as Faithful",
        ocean_ranges={
            "openness": (0.60, 0.85),
            "conscientiousness": (0.65, 0.85),
            "extraversion": (0.75, 0.95),
            "agreeableness": (0.55, 0.80),
            "neuroticism": (0.20, 0.45)
        },
        stat_ranges={
            "intellect": (0.70, 0.90),
            "dexterity": (0.60, 0.80),
            "social_influence": (0.80, 0.95)
        },
        age_range=(30, 55),
        typical_occupations=["CEO", "headteacher", "union organizer", "motivational speaker", "team captain"],
        geographic_bias=["London", "Manchester", "Birmingham", "major UK cities"],
        socioeconomic_class=["middle-class", "upper-middle", "upper"],
        strategic_drive="Leadership and group influence",
        gameplay_tendency="Dominates Round Table; sways group opinion; forms voting blocs"
    ),
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def select_archetype_for_cast(
    existing_archetypes: List[str],
    max_per_archetype: int = 2
) -> ArchetypeDefinition:
    """Select archetype ensuring diversity in cast.

    Args:
        existing_archetypes: List of archetype IDs already selected
        max_per_archetype: Maximum instances of same archetype

    Returns:
        ArchetypeDefinition for new player
    """
    from collections import Counter

    archetype_counts = Counter(existing_archetypes)

    # Filter out archetypes at max capacity
    available = [
        archetype for archetype_id, archetype in ARCHETYPE_REGISTRY.items()
        if archetype_counts.get(archetype_id, 0) < max_per_archetype
    ]

    if not available:
        # All archetypes at capacity, allow overflow
        available = list(ARCHETYPE_REGISTRY.values())

    return random.choice(available)


def get_archetype(archetype_id: str) -> Optional[ArchetypeDefinition]:
    """Get archetype by ID.

    Args:
        archetype_id: Archetype identifier

    Returns:
        ArchetypeDefinition or None if not found
    """
    return ARCHETYPE_REGISTRY.get(archetype_id)


def list_archetypes() -> List[str]:
    """List all archetype IDs."""
    return list(ARCHETYPE_REGISTRY.keys())
