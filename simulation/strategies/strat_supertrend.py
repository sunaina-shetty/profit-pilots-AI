"""
strat_supertrend.py — Strategy 2: Supertrend (10, 3) + EMA 200
Category: TREND
"""
from typing import Dict, Any, List, Optional
from simulation.strategies.base import BaseStrategy

class SupertrendEma200Strategy(BaseStrategy):
    id = "strat_supertrend_ema200"
    name = "Supertrend (10,3) + EMA 200"
    category = "TREND"
    description = "Institutional trend-following strategy using Supertrend (10, 3) trailing support, filtered by EMA 200 macro trend bias."
    formula = "BUY: Supertrend Direction == Bullish (1) AND Close > EMA 200. SELL/EXIT: Supertrend Direction == Bearish (-1)."
    win_rate_target = "60% - 66%"
    risk_level = "LOW"
    default_params = {
        "period": 10,
        "multiplier": 3.0,
        "use_ema200_filter": True,
        "min_bars": 5
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
        if not candles_5m_today:
            return {"score": 0.0, "confidence": 0.0, "signal": "HOLD", "reason": "No candles", "facts": {}}

        curr_bar = candles_5m_today[-1]
        close = float(curr_bar.get("close", 0.0))
        bars_count = len(candles_5m_today)

        st_val = float(indicators.get("supertrend", close))
        st_dir = int(indicators.get("supertrend_dir", 1))
        ema200 = float(indicators.get("ema200", close))

        use_filter = self.get_param("use_ema200_filter", True)
        macro_bullish = (close >= ema200 * 0.998) if use_filter else True

        facts = {
            "strategy": self.id,
            "close": round(close, 2),
            "supertrend": round(st_val, 2),
            "supertrend_dir": "BULLISH" if st_dir == 1 else "BEARISH",
            "ema200": round(ema200, 2),
            "macro_bullish": macro_bullish,
            "bars_count": bars_count
        }

        min_bars = self.get_param("min_bars", 5)
        if bars_count < min_bars:
            return {
                "score": 0.0,
                "confidence": 10.0,
                "signal": "HOLD",
                "reason": f"Warming up indicators ({bars_count}/{min_bars})",
                "facts": facts
            }

        st_dist_pct = (close - st_val) / max(1e-4, close)

        if not is_holding:
            if st_dir == 1 and macro_bullish:
                conviction = min(1.0, 0.45 + min(0.35, st_dist_pct * 30.0))
                return {
                    "score": round(conviction, 3),
                    "confidence": 75.0,
                    "signal": "BUY",
                    "reason": f"Supertrend Bullish ₹{st_val:.2f} & Price ₹{close:.2f} above EMA200 ₹{ema200:.2f}",
                    "facts": facts
                }
            elif st_dir == -1:
                conviction = max(-1.0, -0.45 - min(0.35, abs(st_dist_pct) * 30.0))
                return {
                    "score": round(conviction, 3),
                    "confidence": 70.0,
                    "signal": "SELL",
                    "reason": f"Supertrend Bearish resistance at ₹{st_val:.2f}",
                    "facts": facts
                }
            else:
                return {
                    "score": 0.10,
                    "confidence": 35.0,
                    "signal": "HOLD",
                    "reason": f"Supertrend Bullish but price ₹{close:.2f} below EMA200 ₹{ema200:.2f} filter",
                    "facts": facts
                }
        else:
            if position_side == "LONG":
                if st_dir == -1 or close < st_val:
                    return {
                        "score": -0.85,
                        "confidence": 85.0,
                        "signal": "SELL",
                        "reason": f"Supertrend trailing stop hit: ₹{close:.2f} < ₹{st_val:.2f}",
                        "facts": facts
                    }
                return {
                    "score": 0.50,
                    "confidence": 70.0,
                    "signal": "HOLD",
                    "reason": f"Supertrend holding long: support ₹{st_val:.2f}",
                    "facts": facts
                }
            else:
                if st_dir == 1 or close > st_val:
                    return {
                        "score": 0.85,
                        "confidence": 85.0,
                        "signal": "BUY",
                        "reason": f"Supertrend short covered: ₹{close:.2f} > ₹{st_val:.2f}",
                        "facts": facts
                    }
                return {
                    "score": -0.50,
                    "confidence": 70.0,
                    "signal": "HOLD",
                    "reason": f"Supertrend holding short: resistance ₹{st_val:.2f}",
                    "facts": facts
                }

