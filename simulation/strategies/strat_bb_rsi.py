"""
strat_bb_rsi.py — Strategy 6: Bollinger Bands (20, 2) + RSI Reversal
Category: MEAN_REVERSION
"""
from typing import Dict, Any, List, Optional
from simulation.strategies.base import BaseStrategy

class BollingerBandsRsiStrategy(BaseStrategy):
    id = "strat_bb_rsi_reversal"
    name = "Bollinger Bands (20,2) + RSI Reversal"
    category = "MEAN_REVERSION"
    description = "Statistical mean reversion system. Identifies oversold extremes where price touches the Lower Bollinger Band and RSI is below 35, targeting a bounce back to the mean."
    formula = "BUY: Close <= Lower BB * 1.002 AND RSI <= 35. SELL/EXIT: Close >= Upper BB OR RSI >= 65 OR Target Hit."
    win_rate_target = "64% - 70%"
    risk_level = "LOW"
    default_params = {
        "rsi_oversold": 35.0,
        "rsi_overbought": 65.0,
        "pct_b_threshold": 0.15,
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

        bb_up = float(indicators.get("bb_upper", close * 1.02))
        bb_lo = float(indicators.get("bb_lower", close * 0.98))
        bb_mid = float(indicators.get("bb_mid", close))
        pct_b = float(indicators.get("pct_b", 0.5))
        rsi = float(indicators.get("rsi", 50.0))
        vwap = float(indicators.get("vwap", close))

        rsi_os = self.get_param("rsi_oversold", 35.0)
        rsi_ob = self.get_param("rsi_overbought", 65.0)
        pct_b_th = self.get_param("pct_b_threshold", 0.15)

        facts = {
            "strategy": self.id,
            "close": round(close, 2),
            "bb_upper": round(bb_up, 2),
            "bb_lower": round(bb_lo, 2),
            "bb_mid": round(bb_mid, 2),
            "pct_b": round(pct_b, 3),
            "rsi": round(rsi, 1),
            "vwap": round(vwap, 2),
            "bars_count": bars_count
        }

        min_bars = self.get_param("min_bars", 8)
        if bars_count < min_bars:
            return {
                "score": 0.0,
                "confidence": 10.0,
                "signal": "HOLD",
                "reason": f"Accumulating statistical window ({bars_count}/{min_bars})",
                "facts": facts
            }

        # Over-extended caution / veto
        if pct_b >= 1.05 and rsi >= 75.0:
            return {
                "score": -0.80,
                "confidence": 85.0,
                "signal": "VETO_TREND",
                "reason": f"Market overextended above Upper BB (pct_b {pct_b:.2f}, RSI {rsi:.1f}); blocking buy",
                "facts": facts
            }

        if not is_holding:
            # Oversold Mean Reversion Entry
            if (close <= bb_lo * 1.002 or pct_b <= pct_b_th) and rsi <= rsi_os:
                conviction = min(1.0, 0.50 + (rsi_os - rsi) / 40.0 + max(0.0, (pct_b_th - pct_b) * 2.0))
                return {
                    "score": round(conviction, 3),
                    "confidence": 78.0,
                    "signal": "BUY",
                    "reason": f"Oversold mean reversion: close ₹{close:.2f} near Lower BB ₹{bb_lo:.2f} (pct_b {pct_b:.2f}), RSI {rsi:.1f} <= {rsi_os:.0f}",
                    "facts": facts
                }
            # Overbought Mean Reversion Exit / Short
            elif (close >= bb_up * 0.998 or pct_b >= (1.0 - pct_b_th)) and rsi >= rsi_ob:
                conviction = max(-1.0, -0.50 - (rsi - rsi_ob) / 40.0)
                return {
                    "score": round(conviction, 3),
                    "confidence": 75.0,
                    "signal": "SELL",
                    "reason": f"Overbought resistance at Upper BB ₹{bb_up:.2f} (pct_b {pct_b:.2f}), RSI {rsi:.1f} >= {rsi_ob:.0f}",
                    "facts": facts
                }
            else:
                score = round((0.5 - pct_b) * 0.8, 3)
                score = max(-0.25, min(0.25, score))
                return {
                    "score": score,
                    "confidence": 35.0,
                    "signal": "HOLD",
                    "reason": f"Price within normal volatility bands (%B {pct_b:.2f}, RSI {rsi:.1f})",
                    "facts": facts
                }
        else:
            if position_side == "LONG":
                # Exit if target hit (Middle or Upper band or RSI overbought)
                if close >= bb_up or rsi >= rsi_ob or pct_b >= 0.85:
                    return {
                        "score": -0.85,
                        "confidence": 85.0,
                        "signal": "SELL",
                        "reason": f"Mean reversion target reached: close ₹{close:.2f} >= target Upper BB ₹{bb_up:.2f} or RSI {rsi:.1f} >= {rsi_ob:.0f}",
                        "facts": facts
                    }
                return {
                    "score": 0.40,
                    "confidence": 60.0,
                    "signal": "HOLD",
                    "reason": f"Reversion in progress toward mean ₹{bb_mid:.2f} (current ₹{close:.2f})",
                    "facts": facts
                }
            else:
                if close <= bb_lo or rsi <= rsi_os:
                    return {
                        "score": 0.85,
                        "confidence": 85.0,
                        "signal": "BUY",
                        "reason": f"Short target reached at Lower BB ₹{bb_lo:.2f}",
                        "facts": facts
                    }
                return {
                    "score": -0.40,
                    "confidence": 60.0,
                    "signal": "HOLD",
                    "reason": f"Short reversion in progress toward mean ₹{bb_mid:.2f}",
                    "facts": facts
                }

