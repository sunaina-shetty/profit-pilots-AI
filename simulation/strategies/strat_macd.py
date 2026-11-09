"""
strat_macd.py — Strategy 5: MACD (12, 26, 9) + RSI + EMA 200
Category: MOMENTUM
"""
from typing import Dict, Any, List, Optional
from simulation.strategies.base import BaseStrategy

class MacdRsiEma200Strategy(BaseStrategy):
    id = "strat_macd_rsi_ema200"
    name = "MACD (12,26,9) + RSI + EMA 200"
    category = "MOMENTUM"
    description = "Institutional momentum trend system. Confirms bullish acceleration when MACD crosses above its Signal line, RSI is above 50, and price is supported by EMA 200."
    formula = "BUY: MACD Line > MACD Signal AND RSI > 50 AND Close >= EMA 200. SELL/EXIT: MACD Line < MACD Signal OR RSI < 45."
    win_rate_target = "57% - 63%"
    risk_level = "MODERATE"
    default_params = {
        "fast_period": 12,
        "slow_period": 26,
        "signal_period": 9,
        "rsi_min": 50.0,
        "min_bars": 6
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

        macd = float(indicators.get("macd_line", 0.0))
        signal = float(indicators.get("macd_signal", 0.0))
        hist = float(indicators.get("macd_hist", 0.0))
        rsi = float(indicators.get("rsi", 50.0))
        ema200 = float(indicators.get("ema200", close))

        rsi_min = self.get_param("rsi_min", 50.0)
        macro_ok = close >= (ema200 * 0.998)

        facts = {
            "strategy": self.id,
            "close": round(close, 2),
            "macd": round(macd, 2),
            "signal": round(signal, 2),
            "hist": round(hist, 2),
            "rsi": round(rsi, 1),
            "ema200": round(ema200, 2),
            "macro_ok": macro_ok,
            "bars_count": bars_count
        }

        min_bars = self.get_param("min_bars", 6)
        if bars_count < min_bars:
            return {
                "score": 0.0,
                "confidence": 10.0,
                "signal": "HOLD",
                "reason": f"Warming up MACD filters ({bars_count}/{min_bars})",
                "facts": facts
            }

        if not is_holding:
            if macd > signal and hist > 0 and rsi >= rsi_min and macro_ok:
                conviction = min(1.0, 0.45 + (rsi - 50.0) / 60.0 + min(0.3, hist / max(1.0, close * 0.001)))
                return {
                    "score": round(conviction, 3),
                    "confidence": 75.0,
                    "signal": "BUY",
                    "reason": f"MACD bullish crossover ({macd:.2f} > {signal:.2f}), RSI {rsi:.1f} >= {rsi_min:.0f}, above EMA200",
                    "facts": facts
                }
            elif macd < signal and hist < 0:
                conviction = max(-1.0, -0.45 - (50.0 - rsi) / 60.0)
                return {
                    "score": round(conviction, 3),
                    "confidence": 65.0,
                    "signal": "SELL",
                    "reason": f"MACD bearish momentum ({macd:.2f} < {signal:.2f}, hist {hist:.2f})",
                    "facts": facts
                }
            else:
                score = 0.20 if hist > 0 else -0.20
                return {
                    "score": score,
                    "confidence": 35.0,
                    "signal": "HOLD",
                    "reason": f"MACD hist {hist:.2f}, RSI {rsi:.1f}; waiting for clear trend acceleration",
                    "facts": facts
                }
        else:
            if position_side == "LONG":
                if macd < signal or hist < -0.05 * close * 0.001:
                    return {
                        "score": -0.80,
                        "confidence": 80.0,
                        "signal": "SELL",
                        "reason": f"MACD momentum loss: line ₹{macd:.2f} crossed signal ₹{signal:.2f}",
                        "facts": facts
                    }
                return {
                    "score": 0.45,
                    "confidence": 65.0,
                    "signal": "HOLD",
                    "reason": f"MACD bullish momentum continuing (hist {hist:.2f})",
                    "facts": facts
                }
            else:
                if macd > signal:
                    return {
                        "score": 0.80,
                        "confidence": 80.0,
                        "signal": "BUY",
                        "reason": f"MACD bullish cross covering short",
                        "facts": facts
                    }
                return {
                    "score": -0.45,
                    "confidence": 65.0,
                    "signal": "HOLD",
                    "reason": f"Short MACD momentum continuing",
                    "facts": facts
                }

