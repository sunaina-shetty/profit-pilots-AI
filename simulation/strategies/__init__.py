"""
simulation.strategies package — 10 Configurable Quantitative Trading Strategies.
"""
from simulation.strategies.base import BaseStrategy
from simulation.strategies.registry import (
    STRATEGY_CLASSES, list_all_strategies, get_strategy,
    AGENT1_RECOMMENDED_IDS, AGENT3_RECOMMENDED_IDS
)

__all__ = [
    "BaseStrategy",
    "STRATEGY_CLASSES",
    "list_all_strategies",
    "get_strategy",
    "AGENT1_RECOMMENDED_IDS",
    "AGENT3_RECOMMENDED_IDS"
]

