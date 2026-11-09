"""
strat_donchian.py — Strategy 9: Donchian Channel (20) + EMA 200 + Volume
Category: BREAKOUT
"""
from typing import Dict, Any, List, Optional
from simulation.strategies.base import BaseStrategy

class DonchianBreakoutStrategy(BaseStrategy):
    id = "strat_donchian_breakout"
    name = "Donchian Channel (20) + Volume"
    category = "BREAKOUT"
    description = "Turtle-trading inspired channel breakout system. Triggers on a decisive breakout above the 20-bar Donchian upper band backed by above-average volume and EMA 200 support."
    formula = "BUY: Close >= Donchian Upper Band AND Volume >= Vol SMA AND Close >= EMA 200. SELL/EXIT: Close < Donchian Midline."
    win_rate_target = "58% - 65%"
    risk_level = "MODERATE"
    default_params = {
        "channel_period": 20,
        "volume_factor": 1.0,
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
        vol = float(curr_bar.get("volume", 0.0))
        bars_count = len(candles_5m_today)

        d_up = float(indicators.get("donchian_upper", close))
        d_lo = float(indicators.get("donchian_lower", close))
        d_mid = float(indicators.get("donchian_mid", close))
        vol_sma = float(indicators.get("volume_sma", vol))
        ema200 = float(indicators.get("ema200", close))

        vol_ok = vol >= (vol_sma * self.get_param("volume_factor", 1.0) * 0.8)
        macro_ok = close >= (ema200 * 0.998)
        breakout = close >= (d_up * 0.999)

        facts = {
            "strategy": self.id,
            "close": round(close, 2),
            "donchian_upper": round(d_up, 2),
            "donchian_lower": round(d_lo, 2),
            "donchian_mid": round(d_mid, 2),
            "volume": vol,
            "vol_sma": round(vol_sma, 0),
            "ema200": round(ema200, 2),
            "breakout": breakout,
            "bars_count": bars_count
        }

        min_bars = self.get_param("min_bars", 8)
        if bars_count < min_bars:
            return {
                "score": 0.0,
                "confidence": 10.0,
                "signal": "HOLD",
                "reason": f"Establishing 20-bar Donchian channel ({bars_count}/{min_bars})",
                "facts": facts
            }

        if not is_holding:
            if breakout and vol_ok and macro_ok:
                conviction = min(1.0, 0.55 + (0.2 if vol >= vol_sma else 0.0))
                return {
                    "score": round(conviction, 3),
                    "confidence": 78.0,
                    "signal": "BUY",
                    "reason": f"20-bar Donchian breakout at ₹{d_up:.2f} with volume ({vol:.0f}), above EMA200",
                    "facts": facts
                }
            elif close <= d_lo * 1.001:
                return {
                    "score": -0.60,
                    "confidence": 70.0,
                    "signal": "SELL",
                    "reason": f"20-bar Donchian breakdown below ₹{d_lo:.2f}",
                    "facts": facts
                }
            else:
                score = round((close - d_mid) / max(1.0, d_up - d_lo + 1e-4) * 0.4, 3)
                score = max(-0.20, min(0.20, score))
                return {
                    "score": score,
                    "confidence": 35.0,
                    "signal": "HOLD",
                    "reason": f"Price inside Donchian Channel [₹{d_lo:.2f} - ₹{d_up:.2f}], mid ₹{d_mid:.2f}",
                    "facts": facts
                }
        else:
            if position_side == "LONG":
                if close < d_mid:
                    return {
                        "score": -0.80,
                        "confidence": 80.0,
                        "signal": "SELL",
                        "reason": f"Donchian midline cross exit: close ₹{close:.2f} < midline ₹{d_mid:.2f}",
                        "facts": facts
                    }
                return {
                    "score": 0.40,
                    "confidence": 60.0,
                    "signal": "HOLD",
                    "reason": f"Channel breakout intact above mid ₹{d_mid:.2f}",
                    "facts": facts
                }
            else:
                if close > d_mid:
                    return {
                        "score": 0.80,
                        "confidence": 80.0,
                        "signal": "BUY",
                        "reason": f"Donchian midline covered short: close ₹{close:.2f} > midline ₹{d_mid:.2f}",
                        "facts": facts
                    }
                return {
                    "score": -0.40,
                    "confidence": 60.0,
                    "signal": "HOLD",
                    "reason": f"Short channel intact",
                    "facts": facts
                }

