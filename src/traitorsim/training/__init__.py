"""Training data integration module for TraitorSim.

This module provides access to training data extracted from The Traitors UK Season 1,
including player profiles, strategies, dialogue templates, and phase norms.
"""

from .training_data_loader import TrainingDataLoader
from .strategy_advisor import StrategyAdvisor
from .dialogue_generator import DialogueGenerator
from .behavior_modulator import BehaviorModulator

__all__ = [
    "TrainingDataLoader",
    "StrategyAdvisor",
    "DialogueGenerator",
    "BehaviorModulator",
]
