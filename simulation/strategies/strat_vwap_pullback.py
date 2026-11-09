"""
strat_vwap_pullback.py — Strategy 3: VWAP + EMA 9/21 Pullback
Category: TREND / PULLBACK
"""
from typing import Dict, Any, List, Optional
from simulation.strategies.base import BaseStrategy

class VwapPullbackStrategy(BaseStrategy):
    id = "strat_vwap_pullback"
    name = "VWAP + EMA Pullback"
    category = "TREND"
    description = "Intraday trend pullback system. Enters when an uptrending stock pulls back into dynamic support (EMA 9 or VWAP) and prints a bullish reversal candle."
    formula = "BUY: Close > VWAP AND EMA9 > EMA21 AND Low <= EMA9*1.002 AND Close > Open (Bullish Bounce). SELL/EXIT: Close < VWAP."
    win_rate_target = "62% - 68%"
    risk_level = "MODERATE"
    default_params = {
        "pullback_tolerance_pct": 0.003,
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
        open_p = float(curr_bar.get("open", 0.0))
        low = float(curr_bar.get("low", 0.0))
        bars_count = len(candles_5m_today)

        vwap = float(indicators.get("vwap", close))
        ema9 = float(indicators.get("ema9", close))
        ema21 = float(indicators.get("ema21", close))

        is_green = close >= open_p
        tol = self.get_param("pullback_tolerance_pct", 0.003)
        near_support = (low <= ema9 * (1.0 + tol)) or (low <= vwap * (1.0 + tol))

        facts = {
            "strategy": self.id,
            "close": round(close, 2),
            "vwap": round(vwap, 2),
            "ema9": round(ema9, 2),
            "ema21": round(ema21, 2),
            "is_green": is_green,
            "near_support": near_support,
            "bars_count": bars_count
        }

        min_bars = self.get_param("min_bars", 6)
        if bars_count < min_bars:
            return {
                "score": 0.0,
                "confidence": 10.0,
                "signal": "HOLD",
                "reason": f"Waiting for opening VWAP stability ({bars_count}/{min_bars})",
                "facts": facts
            }

        if not is_holding:
            # Bullish Pullback
            if close > vwap and ema9 >= ema21 and near_support and is_green:
                conviction = 0.65
                return {
                    "score": round(conviction, 3),
                    "confidence": 75.0,
                    "signal": "BUY",
                    "reason": f"Bullish pullback bounce off support: close ₹{close:.2f} > VWAP ₹{vwap:.2f}, EMA9 ₹{ema9:.2f} >= EMA21 ₹{ema21:.2f}",
                    "facts": facts
                }
            # Bearish Pullback
            elif close < vwap and ema9 < ema21:
                conviction = -0.55
                return {
                    "score": round(conviction, 3),
                    "confidence": 65.0,
                    "signal": "SELL",
                    "reason": f"Bearish trend below VWAP: close ₹{close:.2f} < VWAP ₹{vwap:.2f}, EMA9 ₹{ema9:.2f} < EMA21 ₹{ema21:.2f}",
                    "facts": facts
                }
            else:
                score = 0.20 if close > vwap else -0.20
                return {
                    "score": score,
                    "confidence": 40.0,
                    "signal": "HOLD",
                    "reason": f"Price ₹{close:.2f} relative to VWAP ₹{vwap:.2f}; awaiting clean pullback bounce",
                    "facts": facts
                }
        else:
            if position_side == "LONG":
                if close < vwap * 0.997:
                    return {
                        "score": -0.80,
                        "confidence": 80.0,
                        "signal": "SELL",
                        "reason": f"VWAP breach exit: close ₹{close:.2f} < VWAP ₹{vwap:.2f}",
                        "facts": facts
                    }
                return {
                    "score": 0.40,
                    "confidence": 60.0,
                    "signal": "HOLD",
                    "reason": f"Holding pullback trade above VWAP ₹{vwap:.2f}",
                    "facts": facts
                }
            else:
                if close > vwap * 1.003:
                    return {
                        "score": 0.80,
                        "confidence": 80.0,
                        "signal": "BUY",
                        "reason": f"Covering short on VWAP reclaim ₹{vwap:.2f}",
                        "facts": facts
                    }
                return {
                    "score": -0.40,
                    "confidence": 60.0,
                    "signal": "HOLD",
                    "reason": f"Short intact below VWAP ₹{vwap:.2f}",
                    "facts": facts
                }

