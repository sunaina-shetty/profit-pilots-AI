"""
strat_orb.py — Strategy 4: Opening Range Breakout (ORB)
Category: BREAKOUT
"""
from typing import Dict, Any, List, Optional
from simulation.strategies.base import BaseStrategy
from simulation import config
from simulation.config import DEFAULT_CONFIG

class OpeningRangeBreakoutStrategy(BaseStrategy):
    id = "strat_orb"
    name = "Opening Range Breakout (ORB)"
    category = "BREAKOUT"
    description = "Classic intraday breakout system. Determines opening range from 09:15-09:30. Enters when price breaks out of the range with volume and VWAP support."
    formula = "BUY: Close > ORB High AND Close > VWAP AND Volume confirmed. SELL/EXIT: Trailing stop or breakdown."
    win_rate_target = "56% - 62%"
    risk_level = "MODERATE"
    default_params = {
        "range_bars": 3,
        "entry_window_end": "14:45",
        "trailing_atr_multiplier": 1.5
    }

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
        from simulation.agents import evaluate_orb_vwap_agent

        avg_opening_volume = kwargs.get("avg_opening_volume", 0.0)
        orb_entry_done_today = kwargs.get("orb_entry_done_today", False)
        stop_loss_pct = kwargs.get("stop_loss_pct", 1.0)
        entry_type = kwargs.get("entry_type", "orb")

        res = evaluate_orb_vwap_agent(
            candles_5m_today=candles_5m_today,
            indicators=indicators,
            is_holding=is_holding,
            entry_type=entry_type,
            entry_price=entry_price,
            avg_opening_volume=avg_opening_volume,
            orb_entry_done_today=orb_entry_done_today,
            stop_loss_pct=stop_loss_pct,
            highest_close_since_entry=highest_close_since_entry,
            position_side=position_side
        )
        res["facts"]["strategy"] = self.id
        return res

