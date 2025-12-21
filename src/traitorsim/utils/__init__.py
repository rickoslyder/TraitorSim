"""Utility modules for TraitorSim."""

from .logger import setup_logger
from .world_flavor import (
    IN_UNIVERSE_BRANDS,
    FORBIDDEN_BRANDS,
    LEGENDARY_SEASONS,
    get_brand,
    detect_forbidden_brands,
    get_random_season_reference,
    get_random_location,
    format_currency,
    validate_lore_consistency,
)

__all__ = [
    "setup_logger",
    "IN_UNIVERSE_BRANDS",
    "FORBIDDEN_BRANDS",
    "LEGENDARY_SEASONS",
    "get_brand",
    "detect_forbidden_brands",
    "get_random_season_reference",
    "get_random_location",
    "format_currency",
    "validate_lore_consistency",
]
