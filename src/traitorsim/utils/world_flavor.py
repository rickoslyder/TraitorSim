"""World Bible flavor utilities.

This module provides in-universe brand names and cultural references
to maintain lore consistency across the simulation.
"""

from typing import Optional, List

# In-Universe Brands (World Bible Compliant)
IN_UNIVERSE_BRANDS = {
    # Food & Beverage
    "water": "Highland Spring Co.",
    "coffee": "Cairngorm Coffee Roasters",
    "tea": "Speyside Tea Company",
    "snacks": "Heather & Thistle Crisps",
    "meals": "Loch Provisions",
    "breakfast": "Castle Kitchen",
    "alcohol": "Royal Oak Spirits",
    "beer": "Caledonian Brew Co.",
    "whisky": "Glen Ardross Distillery",

    # Lifestyle & Retail
    "clothing": "Baronial Casual Wear",
    "outdoor_gear": "Tartan & Stone Outfitters",
    "toiletries": "Inverness Essentials",
    "pharmacy": "Highland Remedies",
    "general_store": "The Provisions Guild",

    # Media & Entertainment
    "production": "CastleVision",
    "streaming": "Highland Play",
    "newspaper": "The Highland Herald",
    "magazine": "Scotland Today",
    "radio": "BBC Radio Highland",

    # Technology & Communication
    "internet": "ScotNet",
    "mobile": "Thistle Mobile",
    "social_media": "ThistleConnect",
    "email": "HighlandMail",

    # Transportation
    "rail": "Highland Rail",
    "bus": "Stagecoach Scotland",
    "taxi": "Castle Cabs",
    "rideshare": "ThistleRide",

    # Financial
    "bank": "Bank of the Highlands",
    "payment": "ScotsCard",
    "currency": "Pound Sterling (£)",

    # Healthcare
    "hospital": "Inverness Royal Infirmary",
    "clinic": "Highland Medical Centre",
}

# Forbidden Real-World Brands (for validation)
FORBIDDEN_BRANDS = [
    # Social Media
    "facebook", "twitter", "instagram", "tiktok", "snapchat", "linkedin",
    "whatsapp", "telegram", "signal",

    # Tech
    "google", "amazon", "apple", "microsoft", "meta", "netflix", "spotify",
    "uber", "lyft", "airbnb",

    # Food & Retail
    "starbucks", "costa", "pret", "mcdonald's", "kfc", "subway", "tesco",
    "sainsbury's", "asda", "waitrose", "marks & spencer", "primark",

    # Generic
    "youtube", "reddit", "discord", "slack",
]

# Legendary Seasons (for referencing past games)
LEGENDARY_SEASONS = [
    {
        "season": 1,
        "title": "The Aberdeen Blindside",
        "year": 2019,
        "winner": "Faithfuls",
        "signature_moment": "The infamous breakfast order tell that revealed all three Traitors"
    },
    {
        "season": 2,
        "title": "The Edinburgh Strategy",
        "year": 2020,
        "winner": "Traitors",
        "signature_moment": "The first successful recruitment ultimatum"
    },
    {
        "season": 3,
        "title": "The Inverness Gambit",
        "year": 2021,
        "winner": "Faithfuls",
        "signature_moment": "The shield bluff that exposed a Traitor network"
    },
]

# Cultural Context (for persona backstories)
SCOTTISH_LOCATIONS = [
    "Aberdeen", "Edinburgh", "Glasgow", "Inverness", "Dundee", "Perth",
    "Stirling", "Fort William", "Oban", "Isle of Skye", "Highlands",
    "Lowlands", "Fife", "Aberdeenshire", "Angus", "Argyll"
]

UK_LOCATIONS = [
    "London", "Manchester", "Birmingham", "Liverpool", "Leeds", "Newcastle",
    "Bristol", "Cardiff", "Belfast", "Oxford", "Cambridge", "Brighton",
    "York", "Bath", "Cornwall", "Devon", "Sussex", "Kent"
]


def get_brand(category: str, default: Optional[str] = None) -> str:
    """Get in-universe brand name for category.

    Args:
        category: Brand category (e.g., "coffee", "water")
        default: Default value if category not found

    Returns:
        In-universe brand name

    Example:
        >>> get_brand("coffee")
        'Cairngorm Coffee Roasters'
    """
    return IN_UNIVERSE_BRANDS.get(category, default or f"Highland {category.title()}")


def detect_forbidden_brands(text: str) -> List[str]:
    """Detect real-world brands in text using word boundaries.

    Args:
        text: Text to check

    Returns:
        List of detected forbidden brands

    Example:
        >>> detect_forbidden_brands("I love Starbucks and Facebook")
        ['starbucks', 'facebook']
        >>> detect_forbidden_brands("I won't pretend")
        []
    """
    import re
    text_lower = text.lower()
    detected = []

    for brand in FORBIDDEN_BRANDS:
        # Use word boundaries to avoid matching substrings within words
        # e.g., "pret" should not match "pretend"
        pattern = r'\b' + re.escape(brand) + r'\b'
        if re.search(pattern, text_lower):
            detected.append(brand)

    return detected


def get_random_season_reference() -> str:
    """Get a random legendary season reference.

    Returns:
        Formatted season reference string

    Example:
        >>> get_random_season_reference()
        'Season 1: The Aberdeen Blindside (2019) - Won by Faithfuls'
    """
    import random
    season = random.choice(LEGENDARY_SEASONS)
    return (
        f"Season {season['season']}: {season['title']} ({season['year']}) - "
        f"Won by {season['winner']}"
    )


def get_random_location(scotland_only: bool = False) -> str:
    """Get a random location for demographic generation.

    Args:
        scotland_only: If True, only return Scottish locations

    Returns:
        Location name

    Example:
        >>> get_random_location(scotland_only=True)
        'Edinburgh'
    """
    import random

    if scotland_only:
        return random.choice(SCOTTISH_LOCATIONS)
    else:
        all_locations = SCOTTISH_LOCATIONS + UK_LOCATIONS
        return random.choice(all_locations)


def format_currency(amount: float) -> str:
    """Format amount in UK currency.

    Args:
        amount: Amount in pounds

    Returns:
        Formatted currency string

    Example:
        >>> format_currency(1500.50)
        '£1,500.50'
    """
    return f"£{amount:,.2f}"


def validate_lore_consistency(text: str) -> dict:
    """Validate text for lore consistency.

    Args:
        text: Text to validate

    Returns:
        Dict with validation results:
        - is_valid: bool
        - forbidden_brands: List[str]
        - warnings: List[str]

    Example:
        >>> result = validate_lore_consistency("I shop at Tesco")
        >>> result['is_valid']
        False
        >>> result['forbidden_brands']
        ['tesco']
    """
    forbidden = detect_forbidden_brands(text)
    warnings = []

    # Check for common anachronisms
    if "smartphone" in text.lower():
        warnings.append("Use 'mobile phone' instead of 'smartphone'")

    if "app" in text.lower() and "mobile app" not in text.lower():
        warnings.append("Specify 'mobile app' or 'ScotNet app' for clarity")

    return {
        "is_valid": len(forbidden) == 0,
        "forbidden_brands": forbidden,
        "warnings": warnings,
    }
