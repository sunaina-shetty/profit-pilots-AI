"""
registry.py — Central Strategy Registry for ProfitPilot AI.
Manages the catalog of all 10 technical trading strategies, instantiation,
and metadata querying for the UI Strategy Library and Agent Configuration tabs.
"""
from typing import Dict, Any, List, Optional, Type
from simulation.strategies.base import BaseStrategy
from simulation.strategies.strat_ema_rsi_vol import EmaRsiVolumeStrategy
from simulation.strategies.strat_supertrend import SupertrendEma200Strategy
from simulation.strategies.strat_vwap_pullback import VwapPullbackStrategy
from simulation.strategies.strat_orb import OpeningRangeBreakoutStrategy
from simulation.strategies.strat_macd import MacdRsiEma200Strategy
from simulation.strategies.strat_bb_rsi import BollingerBandsRsiStrategy
from simulation.strategies.strat_adx_di import AdxDiEma200Strategy
from simulation.strategies.strat_rsi_divergence import RsiDivergenceEmaStrategy
from simulation.strategies.strat_donchian import DonchianBreakoutStrategy
from simulation.strategies.strat_stochastic import StochasticEmaStrategy

STRATEGY_CLASSES: Dict[str, Type[BaseStrategy]] = {
    "strat_ema_rsi_vol": EmaRsiVolumeStrategy,
    "strat_supertrend_ema200": SupertrendEma200Strategy,
    "strat_vwap_pullback": VwapPullbackStrategy,
    "strat_orb": OpeningRangeBreakoutStrategy,
    "strat_macd_rsi_ema200": MacdRsiEma200Strategy,
    "strat_bb_rsi_reversal": BollingerBandsRsiStrategy,
    "strat_adx_di_regime": AdxDiEma200Strategy,
    "strat_rsi_divergence": RsiDivergenceEmaStrategy,
    "strat_donchian_breakout": DonchianBreakoutStrategy,
    "strat_stochastic_ema": StochasticEmaStrategy,
}

# Categorized recommendations for agents
AGENT1_RECOMMENDED_IDS = [
    "strat_orb",
    "strat_ema_rsi_vol",
    "strat_supertrend_ema200",
    "strat_vwap_pullback",
    "strat_macd_rsi_ema200",
    "strat_adx_di_regime",
    "strat_donchian_breakout",
]

AGENT3_RECOMMENDED_IDS = [
    "strat_bb_rsi_reversal",
    "strat_stochastic_ema",
    "strat_rsi_divergence",
    "strat_vwap_pullback",
]

def list_all_strategies() -> List[Dict[str, Any]]:
    """Returns a list of metadata for all registered strategies."""
    items = []
    for strat_id, cls in STRATEGY_CLASSES.items():
        instance = cls()
        meta = instance.to_dict()
        meta["recommended_for_agent1"] = strat_id in AGENT1_RECOMMENDED_IDS
        meta["recommended_for_agent3"] = strat_id in AGENT3_RECOMMENDED_IDS
        items.append(meta)
    return items

def get_strategy(strategy_id: str, custom_params: Optional[Dict[str, Any]] = None) -> BaseStrategy:
    """Instantiates a strategy by ID with optional custom parameters."""
    cls = STRATEGY_CLASSES.get(strategy_id)
    if not cls:
        raise ValueError(f"Unknown strategy ID: '{strategy_id}'")
    return cls(custom_params=custom_params)

