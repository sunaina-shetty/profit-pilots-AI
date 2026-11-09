"""
base.py — Abstract Base Class for all 10 Technical Trading Strategies in ProfitPilot AI.
Every strategy implements the same contract:
  - id: Unique machine-readable identifier
  - name: Display name
  - category: "TREND" | "BREAKOUT" | "MEAN_REVERSION" | "MOMENTUM"
  - description: Human-readable strategy description
  - formula: Underlying quantitative formula/rules
  - win_rate_target: Target win rate range
  - risk_level: "LOW" | "MODERATE" | "HIGH"
  - default_params: Default parameter dictionary
  - evaluate(): Evaluates candle stream & indicators to return continuous score (-1 to +1),
    confidence (0 to 100), signal (BUY/SELL/HOLD), rationale, and facts.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseStrategy(ABC):
    id: str = "base_strategy"
    name: str = "Base Strategy"
    category: str = "TREND"  # TREND | BREAKOUT | MEAN_REVERSION | MOMENTUM
    description: str = ""
    formula: str = ""
    win_rate_target: str = "55% - 60%"
    risk_level: str = "MODERATE"
    default_params: Dict[str, Any] = {}

    def __init__(self, custom_params: Optional[Dict[str, Any]] = None):
        self.params: Dict[str, Any] = {**self.default_params}
        if custom_params:
            self.params.update(custom_params)

    def get_param(self, key: str, default: Any = None) -> Any:
        return self.params.get(key, default if default is not None else self.default_params.get(key))

    def set_param(self, key: str, value: Any) -> None:
        self.params[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Metadata for UI catalog and API endpoints."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "formula": self.formula,
            "win_rate_target": self.win_rate_target,
            "risk_level": self.risk_level,
            "params": self.params,
            "default_params": self.default_params
        }

    @abstractmethod
    def evaluate(
        self,
        candles_5m_today: List[Dict[str, Any]],
        indicators: Dict[str, Any],
        is_holding: bool = False,
        position_side: str = "LONG",
        entry_price: Optional[float] = None,
        highest_close_since_entry: float = 0.0,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Evaluate market condition for the current candle.
        Returns:
            score: float in [-1.0, 1.0] (continuous conviction)
            confidence: float in [0.0, 100.0]
            signal: "BUY" | "SELL" | "HOLD" | "VETO_TREND"
            reason: str human-readable explanation
            facts: dict of quantitative metrics for inspection
        """
        pass

