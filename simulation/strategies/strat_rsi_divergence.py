"""
strat_rsi_divergence.py — Strategy 8: RSI Divergence + EMA Crossover
Category: REVERSAL / DIVERGENCE
"""
from typing import Dict, Any, List, Optional
from simulation.strategies.base import BaseStrategy

class RsiDivergenceEmaStrategy(BaseStrategy):
    id = "strat_rsi_divergence"
    name = "RSI Divergence + EMA Cross"
    category = "REVERSAL"
    description = "Leading reversal system. Detects bullish divergence where price prints a lower swing low while RSI prints a higher low, confirmed by an EMA 9 crossover above EMA 21."
    formula = "BUY: Bullish Divergence (Price Lower Low, RSI Higher Low) AND EMA9 >= EMA21. SELL/EXIT: EMA9 < EMA21 OR RSI > 70."
    win_rate_target = "63% - 69%"
    risk_level = "LOW"
    default_params = {
        "lookback_bars": 12,
        "rsi_divergence_min_diff": 2.0,
        "min_bars": 8
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

        ema9 = float(indicators.get("ema9", close))
        ema21 = float(indicators.get("ema21", close))
        rsi = float(indicators.get("rsi", 50.0))

        lookback = min(self.get_param("lookback_bars", 12), bars_count)

        # Detect divergence across lookback window
        bullish_div = False
        bearish_div = False
        if bars_count >= 8:
            recent_candles = candles_5m_today[-lookback:]
            prior_low = min(float(c["low"]) for c in recent_candles[:-2]) if len(recent_candles) > 3 else close
            curr_low = float(curr_bar.get("low", close))

            # RSI check
            rsi_series = indicators.get("_rsi_series")
            if rsi_series is not None and len(rsi_series) >= lookback:
                recent_rsi = rsi_series.iloc[-lookback:].values
                prior_rsi_min = float(min(recent_rsi[:-2])) if len(recent_rsi) > 3 else rsi
                curr_rsi = rsi

                # Price LL but RSI HL (Bullish Divergence)
                if curr_low < prior_low and (curr_rsi > prior_rsi_min + self.get_param("rsi_divergence_min_diff", 2.0)):
                    bullish_div = True
                # Price HH but RSI LH (Bearish Divergence)
                elif curr_bar.get("high", close) > max(float(c["high"]) for c in recent_candles[:-2]) and curr_rsi < max(recent_rsi[:-2]) - 2.0:
                    bearish_div = True

        facts = {
            "strategy": self.id,
            "close": round(close, 2),
            "ema9": round(ema9, 2),
            "ema21": round(ema21, 2),
            "rsi": round(rsi, 1),
            "bullish_divergence": bullish_div,
            "bearish_divergence": bearish_div,
            "bars_count": bars_count
        }

        min_bars = self.get_param("min_bars", 8)
        if bars_count < min_bars:
            return {
                "score": 0.0,
                "confidence": 10.0,
                "signal": "HOLD",
                "reason": f"Scanning divergence history ({bars_count}/{min_bars})",
                "facts": facts
            }

        if not is_holding:
            if (bullish_div and ema9 >= ema21) or (rsi < 35 and ema9 > ema21):
                return {
                    "score": 0.70,
                    "confidence": 80.0,
                    "signal": "BUY",
                    "reason": f"Bullish RSI divergence confirmed with EMA9 ₹{ema9:.2f} >= EMA21 ₹{ema21:.2f} cross",
                    "facts": facts
                }
            elif bearish_div or (rsi > 68 and ema9 < ema21):
                return {
                    "score": -0.65,
                    "confidence": 75.0,
                    "signal": "SELL",
                    "reason": f"Bearish divergence / momentum exhaustion (RSI {rsi:.1f}, EMA9 < EMA21)",
                    "facts": facts
                }
            else:
                score = 0.15 if ema9 > ema21 else -0.15
                return {
                    "score": score,
                    "confidence": 35.0,
                    "signal": "HOLD",
                    "reason": f"Monitoring RSI swing patterns (RSI {rsi:.1f}, EMA9 ₹{ema9:.2f})",
                    "facts": facts
                }
        else:
            if position_side == "LONG":
                if ema9 < ema21 or rsi >= 70.0:
                    return {
                        "score": -0.80,
                        "confidence": 80.0,
                        "signal": "SELL",
                        "reason": f"Reversal profit taken: EMA9 < EMA21 or RSI {rsi:.1f} >= 70",
                        "facts": facts
                    }
                return {
                    "score": 0.40,
                    "confidence": 60.0,
                    "signal": "HOLD",
                    "reason": f"RSI divergence reversal intact (RSI {rsi:.1f})",
                    "facts": facts
                }
            else:
                if ema9 > ema21 or rsi <= 30.0:
                    return {
                        "score": 0.80,
                        "confidence": 80.0,
                        "signal": "BUY",
                        "reason": f"Covering short on RSI oversold {rsi:.1f}",
                        "facts": facts
                    }
                return {
                    "score": -0.40,
                    "confidence": 60.0,
                    "signal": "HOLD",
                    "reason": f"Short reversal intact",
                    "facts": facts
                }

