"""
strat_ema_rsi_vol.py — Strategy 1: EMA 9/21 + RSI + Volume
Category: TREND
"""
from typing import Dict, Any, List, Optional
from simulation.strategies.base import BaseStrategy

class EmaRsiVolumeStrategy(BaseStrategy):
    id = "strat_ema_rsi_vol"
    name = "EMA 9/21 + RSI + Volume"
    category = "TREND"
    description = "Captures trending intraday momentum when fast EMA 9 leads EMA 21, RSI confirms directional push (> 50), and volume is elevated."
    formula = "BUY: EMA9 > EMA21 AND RSI > 50 AND Volume >= Vol SMA. SELL/EXIT: EMA9 < EMA21 OR RSI < 45."
    win_rate_target = "58% - 64%"
    risk_level = "MODERATE"
    default_params = {
        "rsi_bullish_min": 50.0,
        "rsi_bearish_max": 45.0,
        "volume_factor": 1.0,
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
        vol = float(curr_bar.get("volume", 0.0))
        bars_count = len(candles_5m_today)

        ema9 = float(indicators.get("ema9", close))
        ema21 = float(indicators.get("ema21", close))
        rsi = float(indicators.get("rsi", 50.0))
        vol_sma = float(indicators.get("volume_sma", vol))

        facts = {
            "strategy": self.id,
            "close": round(close, 2),
            "ema9": round(ema9, 2),
            "ema21": round(ema21, 2),
            "rsi": round(rsi, 1),
            "volume": vol,
            "vol_sma": round(vol_sma, 0),
            "bars_count": bars_count
        }

        min_bars = self.get_param("min_bars", 5)
        if bars_count < min_bars:
            return {
                "score": 0.0,
                "confidence": 10.0,
                "signal": "HOLD",
                "reason": f"Accumulating warmup bars ({bars_count}/{min_bars})",
                "facts": facts
            }

        rsi_bull = self.get_param("rsi_bullish_min", 50.0)
        rsi_bear = self.get_param("rsi_bearish_max", 45.0)
        vol_factor = self.get_param("volume_factor", 1.0)
        vol_ok = vol >= (vol_sma * vol_factor * 0.8)

        # Spread between EMA9 and EMA21
        ema_spread = (ema9 - ema21) / max(1e-4, close)

        if not is_holding:
            if ema9 > ema21 and rsi >= rsi_bull and vol_ok:
                conviction = min(1.0, 0.40 + (rsi - 50.0) / 50.0 + ema_spread * 20.0)
                conf = round(min(90.0, 50.0 + (rsi - 50.0) + (10.0 if vol >= vol_sma else 0.0)), 1)
                return {
                    "score": round(conviction, 3),
                    "confidence": conf,
                    "signal": "BUY",
                    "reason": f"Bullish trend alignment: EMA9 ₹{ema9:.2f} > EMA21 ₹{ema21:.2f}, RSI {rsi:.1f} >= {rsi_bull:.0f}, vol {vol:.0f}",
                    "facts": facts
                }
            elif ema9 < ema21 and rsi < rsi_bear:
                conviction = max(-1.0, -0.40 - (50.0 - rsi) / 50.0)
                conf = round(min(85.0, 50.0 + (50.0 - rsi)), 1)
                return {
                    "score": round(conviction, 3),
                    "confidence": conf,
                    "signal": "SELL",
                    "reason": f"Bearish alignment: EMA9 ₹{ema9:.2f} < EMA21 ₹{ema21:.2f}, RSI {rsi:.1f} < {rsi_bear:.0f}",
                    "facts": facts
                }
            else:
                score = round(ema_spread * 10.0, 3)
                score = max(-0.25, min(0.25, score))
                return {
                    "score": score,
                    "confidence": 40.0,
                    "signal": "HOLD",
                    "reason": f"EMA9 ₹{ema9:.2f}, EMA21 ₹{ema21:.2f}, RSI {rsi:.1f}; waiting for alignment",
                    "facts": facts
                }
        else:
            # Active Position Exit Rules
            if position_side == "LONG":
                if ema9 < ema21 or rsi < rsi_bear:
                    return {
                        "score": -0.80,
                        "confidence": 80.0,
                        "signal": "SELL",
                        "reason": f"Trend exit triggered: EMA9 ₹{ema9:.2f} crossed EMA21 ₹{ema21:.2f} or RSI {rsi:.1f} < {rsi_bear:.0f}",
                        "facts": facts
                    }
                return {
                    "score": 0.40,
                    "confidence": 60.0,
                    "signal": "HOLD",
                    "reason": f"Trend intact: EMA9 ₹{ema9:.2f} > EMA21 ₹{ema21:.2f}, RSI {rsi:.1f}",
                    "facts": facts
                }
            else:
                # SHORT
                if ema9 > ema21 or rsi > rsi_bull:
                    return {
                        "score": 0.80,
                        "confidence": 80.0,
                        "signal": "BUY",
                        "reason": f"Short exit triggered: EMA9 ₹{ema9:.2f} > EMA21 ₹{ema21:.2f}",
                        "facts": facts
                    }
                return {
                    "score": -0.40,
                    "confidence": 60.0,
                    "signal": "HOLD",
                    "reason": f"Short trend intact: EMA9 < EMA21, RSI {rsi:.1f}",
                    "facts": facts
                }

