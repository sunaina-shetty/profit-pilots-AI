"""
agents.py — Three independent trading agents (all math/rule-based, no AI inside).

Agent 1 (ORB + VWAP Trend):   Opening Range Breakout with VWAP filter. Long-only.
Agent 2 (News Sentiment):      Imported from news.py — evaluates headline sentiment.
Agent 3 (VWAP-band Reversion): Mean-reversion on VWAP ± 2σ band. Long-only.

Each agent returns: {signal, confidence, reason, facts}
signal ∈ {BUY, SELL, HOLD, VETO_TREND}
"""
import datetime
from typing import Dict, Any, Optional, List

from simulation import config

# ─────────────────────────────────────────────────────────────────────────────
# AGENT 1 — ORB + VWAP Trend (long-only; SELL only exits a held position)
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_orb_vwap_agent(
    candles_5m_today: List[Dict[str, Any]],
    indicators: Dict[str, Any],
    is_holding: bool,
    entry_type: Optional[str],
    entry_price: Optional[float],
    avg_opening_volume: float,
    orb_entry_done_today: bool,
    stop_loss_pct: float,
    highest_close_since_entry: float = 0.0,
) -> Dict[str, Any]:
    """
    C: ORB + VWAP Trend agent.

    Entry rules (when flat):
      - Opening range = first 5-minute bar (09:15 bar).
      - "In play": first_bar.volume >= 1.5 × avg_opening_volume.
      - BUY when closed bar breaks above orb_high, close > VWAP,
        first bar was green (close > open), time 09:20–11:30,
        and orb_entry_done_today is False.

    Exit rules (when holding an ORB trade):
      - Breakout failed: close < orb_high AND close < VWAP.
      - Trailing stop: once profit >= 1R, trail at highest_close - 2×ATR14.
      - 15:15 handled by engine.
    """
    if not candles_5m_today:
        return _hold_result("No candles available yet", {})

    first_bar = candles_5m_today[0]
    orb_high = first_bar["high"]
    orb_low = first_bar["low"]
    first_bar_green = first_bar["close"] > first_bar["open"]
    first_bar_vol = first_bar.get("volume", 0)

    # "In play" check (configurable via config / env)
    in_play_mult = getattr(config, "ORB_IN_PLAY_VOLUME_MULTIPLIER", 1.5)
    in_play = (avg_opening_volume <= 0) or (first_bar_vol >= in_play_mult * avg_opening_volume)

    current_bar = candles_5m_today[-1]
    current_time = current_bar["time"]
    close = current_bar["close"]
    vwap = indicators.get("vwap", 0.0)
    atr = indicators.get("atr", 0.0)

    facts = {
        "orb_high": round(orb_high, 2),
        "orb_low": round(orb_low, 2),
        "first_bar_green": first_bar_green,
        "first_bar_vol": first_bar_vol,
        "avg_opening_volume": round(avg_opening_volume, 0),
        "in_play": in_play,
        "close": round(close, 2),
        "vwap": round(vwap, 2),
        "atr": round(atr, 2),
        "orb_entry_done": orb_entry_done_today,
    }

    if not is_holding:
        if not in_play:
            return {
                "signal": "HOLD",
                "confidence": 0.40,
                "reason": f"Stock not in play today (opening volume {first_bar_vol:,.0f} < "
                          f"{in_play_mult}× avg {avg_opening_volume:,.0f})",
                "facts": facts,
            }

        if orb_entry_done_today:
            return _hold_result("ORB entry already used today (max 1 per day)", facts)

        if not first_bar_green:
            return _hold_result("First bar bearish — ORB setup requires green open bar", facts)

        # Time gate: entries only 09:20–11:30
        window_end = getattr(config, "ORB_ENTRY_WINDOW_END", "11:30")
        if current_time < "09:20" or current_time > window_end:
            return _hold_result(
                f"Outside ORB entry window (09:20–{window_end}); current {current_time}",
                facts,
            )

        # Breakout check
        if close > orb_high and close > vwap:
            conf = round(0.65 + min(0.25, (close - orb_high) / (orb_high + 1e-9) * 50), 2)
            return {
                "signal": "BUY",
                "confidence": min(0.90, conf),
                "reason": (f"ORB breakout confirmed: close ₹{close:.2f} > ORB high ₹{orb_high:.2f} "
                           f"and above VWAP ₹{vwap:.2f}; stock in play (vol {first_bar_vol:,.0f})"),
                "facts": facts,
                "orb_high": orb_high,
                "orb_low": orb_low,
                "is_in_play": in_play,
            }

        return _hold_result(
            f"Waiting for ORB breakout above ₹{orb_high:.2f} (close ₹{close:.2f}, VWAP ₹{vwap:.2f})",
            facts,
        )

    else:
        # Holding an ORB trade — check exits
        if entry_type != "orb":
            # Not our trade; don't interfere
            return _hold_result("Holding non-ORB trade; ORB agent watching", facts)

        entry_p = entry_price or close
        initial_risk = entry_p * (stop_loss_pct / 100.0)
        profit = close - entry_p
        max_profit = (highest_close_since_entry - entry_p) if highest_close_since_entry > 0 else profit

        # Breakout failed exit
        if close < orb_high and close < vwap:
            return {
                "signal": "SELL",
                "confidence": 0.85,
                "reason": (f"ORB breakout failed: close ₹{close:.2f} retreated below "
                           f"ORB high ₹{orb_high:.2f} and VWAP ₹{vwap:.2f}"),
                "facts": facts,
            }

        # Trailing stop after position has reached 1R profit
        if max_profit >= initial_risk and atr > 0 and highest_close_since_entry > 0:
            trailing_mult = getattr(config, "ORB_TRAILING_ATR_MULTIPLIER", 2.0)
            trailing_stop = highest_close_since_entry - trailing_mult * atr
            if close < trailing_stop:
                return {
                    "signal": "SELL",
                    "confidence": 0.80,
                    "reason": (f"Trailing ATR stop hit: close ₹{close:.2f} < "
                               f"trailing stop ₹{trailing_stop:.2f} "
                               f"(high ₹{highest_close_since_entry:.2f} - {trailing_mult}×ATR ₹{atr:.2f})"),
                    "facts": facts,
                }

        return _hold_result(
            f"ORB trade intact: close ₹{close:.2f}, VWAP ₹{vwap:.2f}, P&L ₹{profit:.2f}",
            facts,
        )


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 3 — VWAP-band Mean Reversion
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_vwap_reversion_agent(
    candles_5m_today: List[Dict[str, Any]],
    indicators: Dict[str, Any],
    is_holding: bool,
    entry_type: Optional[str],
    entry_time_str: Optional[str],
    entry_price: Optional[float],
    stop_loss_pct: float,
    round_trip_cost_pct: float,
) -> Dict[str, Any]:
    """
    D: VWAP-band Mean Reversion agent (long-only; RANGE days only).

    Entry (when flat, >= 12 bars, 10:30–14:30, RANGE day):
      close <= VWAP - 2σ AND RSI14 < 35 AND current_bar.close > prev_bar.high (reversal candle)
      Cost filter: skip if expected move < 3 × round_trip_cost.

    Exit (when holding a reversion trade):
      - price >= VWAP → "mean reversion target reached"
      - close <= VWAP - 3σ → "thesis broken"
      - 90-minute time stop
      - User stop-loss handled by broker.

    Also emits VETO_TREND when close >= VWAP + 2σ (market overextended).
    """
    if not candles_5m_today:
        return _hold_result("No candles available yet", {})

    close = float(candles_5m_today[-1]["close"])
    vwap = indicators.get("vwap", 0.0)
    rsi = indicators.get("rsi", 50.0)
    sigma = indicators.get("vwap_sigma", 0.0)
    bars_count = len(candles_5m_today)
    current_time = candles_5m_today[-1]["time"]

    facts = {
        "close": round(close, 2),
        "vwap": round(vwap, 2),
        "sigma": round(sigma, 4),
        "rsi": round(rsi, 1),
        "bars_count": bars_count,
        "current_time": current_time,
    }

    # Veto check: market extended above VWAP + 2σ — block trend agent entry
    if sigma > 0 and close >= vwap + 2.0 * sigma:
        facts["veto_reason"] = f"Close ₹{close:.2f} >= VWAP+2σ ₹{vwap + 2*sigma:.2f}"
        return {
            "signal": "VETO_TREND",
            "confidence": 0.80,
            "reason": f"Market extended: close ₹{close:.2f} ≥ VWAP+2σ ₹{vwap + 2*sigma:.2f}; blocking trend entry",
            "facts": facts,
        }

    if not is_holding:
        # Need at least 12 bars and correct time window
        if bars_count < 12:
            return _hold_result(f"Only {bars_count} bars; need >= 12 for σ estimate", facts)

        if current_time < "10:30" or current_time > "14:30":
            return _hold_result(
                f"Outside reversion window (10:30–14:30); current {current_time}", facts
            )

        if sigma <= 0:
            return _hold_result("VWAP sigma not yet computable", facts)

        lower_band_2 = vwap - 2.0 * sigma

        # Must be at or below lower 2σ band
        if close > lower_band_2:
            return _hold_result(
                f"Close ₹{close:.2f} not at extreme (VWAP-2σ ₹{lower_band_2:.2f})", facts
            )

        # RSI filter
        if rsi >= 35.0:
            return _hold_result(f"RSI {rsi:.1f} not oversold enough (need < 35)", facts)

        # Reversal candle: current bar closes above previous bar's high
        if len(candles_5m_today) >= 2:
            prev_high = candles_5m_today[-2]["high"]
            if close <= prev_high:
                return _hold_result(
                    f"No reversal candle: close ₹{close:.2f} <= prev high ₹{prev_high:.2f}", facts
                )
        else:
            prev_high = close

        # F: Cost filter — skip if expected move < 3 × round-trip cost
        expected_move_pct = (vwap - close) / (close + 1e-9)
        if round_trip_cost_pct > 0 and expected_move_pct < 3.0 * round_trip_cost_pct:
            skip_msg = (
                f"Skipped cost filter: expected move {expected_move_pct*100:.3f}% "
                f"< 3× round-trip cost {round_trip_cost_pct*100:.3f}%"
            )
            return _hold_result(skip_msg, facts)

        conf = round(0.60 + min(0.25, (lower_band_2 - close) / (sigma + 1e-9) * 0.10), 2)
        return {
            "signal": "BUY",
            "confidence": min(0.85, conf),
            "reason": (f"VWAP mean-reversion setup: close ₹{close:.2f} at VWAP-2σ ₹{lower_band_2:.2f}, "
                       f"RSI {rsi:.1f} < 35, reversal candle confirmed; targeting VWAP ₹{vwap:.2f}"),
            "facts": facts,
        }

    else:
        # Holding a reversion trade — check exits
        if entry_type != "reversion":
            return _hold_result("Holding non-reversion trade; reversion agent watching", facts)

        # Exit 1: Price reached VWAP
        if close >= vwap:
            return {
                "signal": "SELL",
                "confidence": 0.85,
                "reason": f"Mean reversion target reached: close ₹{close:.2f} >= VWAP ₹{vwap:.2f}",
                "facts": facts,
            }

        # Exit 2: Thesis broken — price fell below VWAP - 3σ
        if sigma > 0:
            lower_band_3 = vwap - 3.0 * sigma
            if close <= lower_band_3:
                return {
                    "signal": "SELL",
                    "confidence": 0.90,
                    "reason": (f"Reversion thesis broken: close ₹{close:.2f} <= VWAP-3σ ₹{lower_band_3:.2f}; "
                               "exit before further loss"),
                    "facts": facts,
                }

        # Exit 3: 90-minute time stop
        if entry_time_str:
            try:
                entry_dt = datetime.datetime.strptime(entry_time_str, "%H:%M")
                curr_dt = datetime.datetime.strptime(current_time, "%H:%M")
                minutes_held = (curr_dt - entry_dt).seconds // 60
                if minutes_held >= 90:
                    return {
                        "signal": "SELL",
                        "confidence": 0.75,
                        "reason": f"90-minute time stop: held {minutes_held} min without reaching VWAP target",
                        "facts": facts,
                    }
            except Exception:
                pass

        return _hold_result(
            f"Holding reversion trade: close ₹{close:.2f}, target VWAP ₹{vwap:.2f}",
            facts,
        )


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY WRAPPERS — kept so existing tests that import the old names still pass
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_trend_agent(indicators: Dict[str, Any], is_holding: bool) -> Dict[str, Any]:
    """
    Legacy wrapper. New code should call evaluate_orb_vwap_agent() directly.
    Kept for backward compatibility with the existing test suite.
    Falls back to the old EMA/RSI/VWAP logic when no 5m candles are available.
    """
    price = indicators.get("price", 0.0)
    ema9 = indicators.get("ema9", 0.0)
    ema21 = indicators.get("ema21", 0.0)
    rsi = indicators.get("rsi", 50.0)
    vwap = indicators.get("vwap", 0.0)
    p30m = indicators.get("price_30m_ago", price)
    closes_below_vwap = indicators.get("closes_below_vwap_count", 0)

    facts = {
        "price": price, "ema9": ema9, "ema21": ema21,
        "rsi": rsi, "vwap": vwap, "price_30m_ago": p30m,
        "closes_below_vwap": closes_below_vwap,
    }

    if not is_holding:
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
                "facts": facts,
            }
        elif ema9 < ema21:
            return {"signal": "HOLD", "confidence": 0.50,
                    "reason": "Downtrend, staying out (EMA9 below EMA21)", "facts": facts}
        else:
            return {"signal": "HOLD", "confidence": 0.40,
                    "reason": f"Consolidating/neutral trend (score {score}/4)", "facts": facts}
    else:
        if ema9 < ema21:
            return {"signal": "SELL", "confidence": 0.85,
                    "reason": f"Trend breakdown: EMA9 ({ema9}) crossed below EMA21 ({ema21})", "facts": facts}
        elif closes_below_vwap >= 2:
            return {"signal": "SELL", "confidence": 0.80,
                    "reason": f"Lost VWAP support: closed below VWAP ({vwap}) for 2 consecutive bars",
                    "facts": facts}
        else:
            return {"signal": "HOLD", "confidence": 0.65,
                    "reason": "Uptrend intact: EMA9 above EMA21, holding above VWAP", "facts": facts}


def evaluate_contrarian_agent(
    indicators: Dict[str, Any],
    is_holding: bool,
    entry_type: Optional[str] = None,
    entry_price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Legacy wrapper. New code should call evaluate_vwap_reversion_agent() directly.
    Kept for backward compatibility with the existing test suite.
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
        "pct_b": pct_b,
    }

    if not is_holding:
        if overheated_flags_count >= 2:
            return {"signal": "SELL", "confidence": 0.85,
                    "reason": f"Overheated extreme ({overheated_flags_count} flags: RSI {rsi}, %B {pct_b}); don't chase top",
                    "facts": facts}
        elif rsi < 32.0 and pct_b < 0.15:
            return {"signal": "BUY", "confidence": 0.80,
                    "reason": f"Oversold capitulation bounce setup (RSI {rsi} < 32, %B {pct_b} < 0.15)",
                    "facts": facts}
        else:
            return {"signal": "HOLD", "confidence": 0.45,
                    "reason": "Within normal statistical boundaries (no crowd extreme)", "facts": facts}
    else:
        if entry_type == "dip":
            if price >= vwap or rsi > 55.0:
                return {"signal": "SELL", "confidence": 0.85,
                        "reason": f"Dip-buy target reached: price back at VWAP ({vwap}) or RSI {rsi} > 55",
                        "facts": facts}
            else:
                return {"signal": "HOLD", "confidence": 0.60,
                        "reason": f"Holding dip-buy: awaiting mean reversion back to VWAP ({vwap})", "facts": facts}
        else:
            in_profit = (entry_price is not None and price > entry_price)
            if overheated_flags_count >= 2 and in_profit:
                return {"signal": "SELL", "confidence": 0.80,
                        "reason": f"Take profit into euphoric spike: {overheated_flags_count} overheated flags and in profit",
                        "facts": facts}
            else:
                return {"signal": "HOLD", "confidence": 0.50,
                        "reason": "No exhaustion signal detected on trend trade", "facts": facts}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _hold_result(reason: str, facts: Dict[str, Any]) -> Dict[str, Any]:
    return {"signal": "HOLD", "confidence": 0.40, "reason": reason, "facts": facts}
