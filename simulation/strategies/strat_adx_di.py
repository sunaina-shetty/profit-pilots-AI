"""
strat_adx_di.py — Strategy 7: ADX 14 + DI + EMA 200 (Strategy & Market Regime Filter)
Category: TREND / REGIME
"""
from typing import Dict, Any, List, Optional
from simulation.strategies.base import BaseStrategy

class AdxDiEma200Strategy(BaseStrategy):
    id = "strat_adx_di_regime"
    name = "ADX 14 + DI + EMA 200"
    category = "TREND"
    description = "Trend strength and regime filter strategy. Enters when ADX confirms robust directional momentum (ADX > 25), +DI leads -DI, and price is above EMA 200."
    formula = "BUY: ADX >= 25 AND +DI > -DI AND Close >= EMA 200. SELL/EXIT: -DI > +DI OR ADX < 18."
    win_rate_target = "60% - 66%"
    risk_level = "LOW"
    default_params = {
        "adx_threshold": 25.0,
        "adx_exhaustion": 18.0,
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

        adx = float(indicators.get("adx", 20.0))
        pdi = float(indicators.get("pdi", 20.0))
        mdi = float(indicators.get("mdi", 20.0))
        ema200 = float(indicators.get("ema200", close))

        adx_th = self.get_param("adx_threshold", 25.0)
        adx_ex = self.get_param("adx_exhaustion", 18.0)
        macro_ok = close >= (ema200 * 0.998)

        facts = {
            "strategy": self.id,
            "close": round(close, 2),
            "adx": round(adx, 2),
            "pdi": round(pdi, 2),
            "mdi": round(mdi, 2),
            "ema200": round(ema200, 2),
            "macro_ok": macro_ok,
            "bars_count": bars_count
        }

        min_bars = self.get_param("min_bars", 7)
        if bars_count < min_bars:
            return {
                "score": 0.0,
                "confidence": 10.0,
                "signal": "HOLD",
                "reason": f"Warming up ADX directional buffer ({bars_count}/{min_bars})",
                "facts": facts
            }

        if not is_holding:
            if adx >= adx_th and pdi > mdi and macro_ok:
                di_diff = pdi - mdi
                conviction = min(1.0, 0.45 + (adx - adx_th) / 50.0 + di_diff / 50.0)
                return {
                    "score": round(conviction, 3),
                    "confidence": 76.0,
                    "signal": "BUY",
                    "reason": f"Strong trend confirmed: ADX {adx:.1f} >= {adx_th:.0f}, +DI ({pdi:.1f}) > -DI ({mdi:.1f}), above EMA200",
                    "facts": facts
                }
            elif adx >= adx_th and mdi > pdi:
                di_diff = mdi - pdi
                conviction = max(-1.0, -0.45 - (adx - adx_th) / 50.0 - di_diff / 50.0)
                return {
                    "score": round(conviction, 3),
                    "confidence": 72.0,
                    "signal": "SELL",
                    "reason": f"Strong downtrend: ADX {adx:.1f} >= {adx_th:.0f}, -DI ({mdi:.1f}) > +DI ({pdi:.1f})",
                    "facts": facts
                }
            else:
                return {
                    "score": 0.05,
                    "confidence": 30.0,
                    "signal": "HOLD",
                    "reason": f"Market lacks strong directional trend (ADX {adx:.1f} < {adx_th:.0f}); ranging/consolidation",
                    "facts": facts
                }
        else:
            if position_side == "LONG":
                if mdi > pdi or (adx < adx_ex and bars_count > 15):
                    return {
                        "score": -0.80,
                        "confidence": 80.0,
                        "signal": "SELL",
                        "reason": f"Trend exhaustion: -DI {mdi:.1f} crossed +DI {pdi:.1f} or ADX {adx:.1f} < {adx_ex:.0f}",
                        "facts": facts
                    }
                return {
                    "score": 0.45,
                    "confidence": 65.0,
                    "signal": "HOLD",
                    "reason": f"Trend strength persisting (ADX {adx:.1f}, +DI {pdi:.1f})",
                    "facts": facts
                }
            else:
                if pdi > mdi:
                    return {
                        "score": 0.80,
                        "confidence": 80.0,
                        "signal": "BUY",
                        "reason": f"+DI crossed -DI covering short",
                        "facts": facts
                    }
                return {
                    "score": -0.45,
                    "confidence": 65.0,
                    "signal": "HOLD",
                    "reason": f"Downtrend persisting (ADX {adx:.1f})",
                    "facts": facts
                }

