"""
regime.py — Market Regime Detection (Plain Python, math only).

Classifies the market into one of three regimes:
  - TREND: After 10:00, price outside opening range AND ADX14(5m) > 20 (or early ORB breakout).
  - RANGE: Price inside opening range for >= 6 bars AND ADX14(5m) < 20.
  - UNCLEAR: Otherwise.
"""
from typing import List, Dict, Any, Tuple

def detect_regime(
    candles_5m_today: List[Dict[str, Any]],
    orb_high: float,
    orb_low: float,
    indicators: Dict[str, Any]
) -> Tuple[str, str]:
    """
    Detects market regime for the current 5-minute bar.
    Returns: (regime, reason) where regime in ("TREND", "RANGE", "UNCLEAR")
    """
    if not candles_5m_today or orb_high <= 0:
        return "UNCLEAR", "Awaiting opening range formation"

    current_bar = candles_5m_today[-1]
    current_time = current_bar.get("time", "09:15")
    close = float(current_bar.get("close", 0.0))
    adx = float(indicators.get("adx", 0.0))

    # Check consecutive bars inside opening range
    bars_inside_orb = 0
    for bar in reversed(candles_5m_today):
        c = float(bar.get("close", 0.0))
        if orb_low <= c <= orb_high:
            bars_inside_orb += 1
        else:
            break

    # 1. RANGE Day check:
    # Price inside the opening range for >= 6 bars AND ADX < 20
    if bars_inside_orb >= 6 and adx < 20.0:
        return "RANGE", f"RANGE day: inside ORB (₹{orb_low:.2f}-₹{orb_high:.2f}) for {bars_inside_orb} bars, ADX {adx:.1f} < 20"

    # 2. TREND Day check:
    # After 10:00, price outside opening range AND ADX > 20
    is_outside_orb = (close > orb_high or close < orb_low)
    if current_time >= "10:00":
        if is_outside_orb and adx > 20.0:
            direction = "above high" if close > orb_high else "below low"
            return "TREND", f"TREND day: price ₹{close:.2f} {direction} ORB with ADX {adx:.1f} > 20"
    else:
        # Before 10:00: early breakout above ORB high is an emerging trend
        if close > orb_high:
            return "TREND", f"Early TREND breakout: price ₹{close:.2f} above ORB high ₹{orb_high:.2f}"

    return "UNCLEAR", f"UNCLEAR regime: ADX {adx:.1f}, ORB range ₹{orb_low:.2f}-₹{orb_high:.2f}, close ₹{close:.2f}"

