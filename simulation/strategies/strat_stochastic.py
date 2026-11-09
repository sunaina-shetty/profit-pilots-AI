"""
strat_stochastic.py — Strategy 10: Stochastic (14, 3, 3) + EMA 50/200
Category: MEAN_REVERSION / MOMENTUM
"""
from typing import Dict, Any, List, Optional
from simulation.strategies.base import BaseStrategy

class StochasticEmaStrategy(BaseStrategy):
    id = "strat_stochastic_ema"
    name = "Stochastic (14,3,3) + EMA 50/200"
    category = "MEAN_REVERSION"
    description = "Trend-filtered oscillator system. Buys oversold Stochastic %K/%D crossovers below 25 when supported by the intermediate EMA 50 or long-term EMA 200 trend."
    formula = "BUY: %K crosses above %D AND %K <= 25 AND Close >= EMA 50. SELL/EXIT: %K crosses below %D AND %K >= 75."
    win_rate_target = "61% - 67%"
    risk_level = "LOW"
    default_params = {
        "oversold_threshold": 25.0,
        "overbought_threshold": 75.0,
        "min_bars": 7
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

        k = float(indicators.get("stoch_k", 50.0))
        d = float(indicators.get("stoch_d", 50.0))
        ema50 = float(indicators.get("ema50", close))
        ema200 = float(indicators.get("ema200", close))

        os_th = self.get_param("oversold_threshold", 25.0)
        ob_th = self.get_param("overbought_threshold", 75.0)
        trend_ok = close >= (ema50 * 0.998) or close >= (ema200 * 0.998)

        facts = {
            "strategy": self.id,
            "close": round(close, 2),
            "stoch_k": round(k, 1),
            "stoch_d": round(d, 1),
            "ema50": round(ema50, 2),
            "ema200": round(ema200, 2),
            "trend_ok": trend_ok,
            "bars_count": bars_count
        }

        min_bars = self.get_param("min_bars", 7)
        if bars_count < min_bars:
            return {
                "score": 0.0,
                "confidence": 10.0,
                "signal": "HOLD",
                "reason": f"Warming up Stochastic oscillator ({bars_count}/{min_bars})",
                "facts": facts
            }

        if not is_holding:
            if k >= d and k <= os_th and trend_ok:
                conviction = min(1.0, 0.50 + (os_th - k) / 30.0)
                return {
                    "score": round(conviction, 3),
                    "confidence": 76.0,
                    "signal": "BUY",
                    "reason": f"Oversold Stochastic crossover: %K ({k:.1f}) >= %D ({d:.1f}) <= {os_th:.0f}, above EMA support",
                    "facts": facts
                }
            elif k <= d and k >= ob_th:
                conviction = max(-1.0, -0.50 - (k - ob_th) / 30.0)
                return {
                    "score": round(conviction, 3),
                    "confidence": 74.0,
                    "signal": "SELL",
                    "reason": f"Overbought Stochastic rejection: %K ({k:.1f}) <= %D ({d:.1f}) >= {ob_th:.0f}",
                    "facts": facts
                }
            else:
                score = round((50.0 - k) / 100.0 * 0.4, 3)
                score = max(-0.20, min(0.20, score))
                return {
                    "score": score,
                    "confidence": 35.0,
                    "signal": "HOLD",
                    "reason": f"Stochastic %K {k:.1f}, %D {d:.1f}; waiting for oversold/overbought extremity",
                    "facts": facts
                }
        else:
            if position_side == "LONG":
                if k <= d and k >= ob_th:
                    return {
                        "score": -0.80,
                        "confidence": 80.0,
                        "signal": "SELL",
                        "reason": f"Overbought exit: %K {k:.1f} crossed below %D {d:.1f} at {ob_th:.0f}",
                        "facts": facts
                    }
                return {
                    "score": 0.40,
                    "confidence": 60.0,
                    "signal": "HOLD",
                    "reason": f"Stochastic trade intact (%K {k:.1f})",
                    "facts": facts
                }
            else:
                if k >= d and k <= os_th:
                    return {
                        "score": 0.80,
                        "confidence": 80.0,
                        "signal": "BUY",
                        "reason": f"Covering short on oversold Stochastic %K {k:.1f}",
                        "facts": facts
                    }
                return {
                    "score": -0.40,
                    "confidence": 60.0,
                    "signal": "HOLD",
                    "reason": f"Short Stochastic trade intact",
                    "facts": facts
                }

