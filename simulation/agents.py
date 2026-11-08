from typing import Dict, Any, Optional

def evaluate_trend_agent(indicators: Dict[str, Any], is_holding: bool) -> Dict[str, Any]:
    """
    TREND AGENT (math only):
    - When flat: score 4 checks (price > VWAP, EMA9 > EMA21, RSI 48-72, price > 30m ago).
      BUY if EMA9 > EMA21 and score >= 3.
      When bearish and flat say HOLD ("downtrend, staying out"), never SELL.
    - When holding:
      SELL if EMA9 falls below EMA21 or price closes below VWAP twice in a row, else HOLD.
    """
    price = indicators.get("price", 0.0)
    ema9 = indicators.get("ema9", 0.0)
    ema21 = indicators.get("ema21", 0.0)
    rsi = indicators.get("rsi", 50.0)
    vwap = indicators.get("vwap", 0.0)
    p30m = indicators.get("price_30m_ago", price)
    closes_below_vwap = indicators.get("closes_below_vwap_count", 0)

    facts = {
        "price": price,
        "ema9": ema9,
        "ema21": ema21,
        "rsi": rsi,
        "vwap": vwap,
        "price_30m_ago": p30m,
        "closes_below_vwap": closes_below_vwap
    }

    if not is_holding:
        # Score 4 checks
        c1 = price > vwap
        c2 = ema9 > ema21
        c3 = 48.0 <= rsi <= 72.0
        c4 = price > p30m
        score = sum([c1, c2, c3, c4])
        facts["score"] = score

        if ema9 > ema21 and score >= 3:
            conf = round(0.60 + (score / 4.0) * 0.35, 2)
            return {
                "signal": "BUY",
                "confidence": conf,
                "reason": f"Strong uptrend alignment: EMA9>EMA21, score {score}/4 (price>VWAP, RSI {rsi}, price>30m ago)",
                "facts": facts
            }
        elif ema9 < ema21:
            return {
                "signal": "HOLD",
                "confidence": 0.50,
                "reason": "Downtrend, staying out (EMA9 below EMA21)",
                "facts": facts
            }
        else:
            return {
                "signal": "HOLD",
                "confidence": 0.40,
                "reason": f"Consolidating/neutral trend (score {score}/4)",
                "facts": facts
            }
    else:
        # When holding: check exit conditions
        if ema9 < ema21:
            return {
                "signal": "SELL",
                "confidence": 0.85,
                "reason": f"Trend breakdown: EMA9 ({ema9}) crossed below EMA21 ({ema21})",
                "facts": facts
            }
        elif closes_below_vwap >= 2:
            return {
                "signal": "SELL",
                "confidence": 0.80,
                "reason": f"Lost VWAP support: closed below VWAP ({vwap}) for 2 consecutive bars",
                "facts": facts
            }
        else:
            return {
                "signal": "HOLD",
                "confidence": 0.65,
                "reason": f"Uptrend intact: EMA9 above EMA21, holding above VWAP",
                "facts": facts
            }

def evaluate_contrarian_agent(
    indicators: Dict[str, Any],
    is_holding: bool,
    entry_type: Optional[str] = None,
    entry_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    CONTRARIAN AGENT (math only):
    - Overheated flags:
      1) price > VWAP + 2*ATR
      2) RSI > 75
      3) %B > 1.0
    - When flat:
      - 2+ flags -> SELL meaning "don't chase" (veto);
      - RSI < 32 and %B < 0.15 -> BUY (oversold bounce);
      - else HOLD.
    - When holding a dip-buy:
      - SELL once price is back at VWAP (price >= vwap) or RSI > 55.
    - When holding a trend trade:
      - SELL if 2+ flags and in profit (price > entry_price).
    """
    price = indicators.get("price", 0.0)
    vwap = indicators.get("vwap", 0.0)
    atr = indicators.get("atr", 1.0)
    rsi = indicators.get("rsi", 50.0)
    pct_b = indicators.get("pct_b", 0.5)

    f1 = price > (vwap + 2.0 * atr)
    f2 = rsi > 75.0
    f3 = pct_b > 1.0
    overheated_flags_count = sum([f1, f2, f3])

    facts = {
        "overheated_flags": overheated_flags_count,
        "price_vs_vwap_2atr": round(price - (vwap + 2.0 * atr), 2),
        "rsi": rsi,
        "pct_b": pct_b
    }

    if not is_holding:
        if overheated_flags_count >= 2:
            return {
                "signal": "SELL",
                "confidence": 0.85,
                "reason": f"Overheated extreme ({overheated_flags_count} flags: RSI {rsi}, %B {pct_b}); don't chase top",
                "facts": facts
            }
        elif rsi < 32.0 and pct_b < 0.15:
            return {
                "signal": "BUY",
                "confidence": 0.80,
                "reason": f"Oversold capitulation bounce setup (RSI {rsi} < 32, %B {pct_b} < 0.15)",
                "facts": facts
            }
        else:
            return {
                "signal": "HOLD",
                "confidence": 0.45,
                "reason": "Within normal statistical boundaries (no crowd extreme)",
                "facts": facts
            }
    else:
        # Holding
        if entry_type == "dip":
            if price >= vwap or rsi > 55.0:
                return {
                    "signal": "SELL",
                    "confidence": 0.85,
                    "reason": f"Dip-buy target reached: price back at VWAP ({vwap}) or RSI {rsi} > 55",
                    "facts": facts
                }
            else:
                return {
                    "signal": "HOLD",
                    "confidence": 0.60,
                    "reason": f"Holding dip-buy: awaiting mean reversion back to VWAP ({vwap})",
                    "facts": facts
                }
        else:
            # Trend trade
            in_profit = (entry_price is not None and price > entry_price)
            if overheated_flags_count >= 2 and in_profit:
                return {
                    "signal": "SELL",
                    "confidence": 0.80,
                    "reason": f"Take profit into euphoric spike: {overheated_flags_count} overheated flags and in profit",
                    "facts": facts
                }
            else:
                return {
                    "signal": "HOLD",
                    "confidence": 0.50,
                    "reason": "No exhaustion signal detected on trend trade",
                    "facts": facts
                }

