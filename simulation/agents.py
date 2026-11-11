"""
agents.py — Three independent trading agents with graded continuous scores (-1.0 to +1.0).

Agent 1 (ORB + VWAP Trend):
  - Opening range = first 3 five-minute bars (first 15 min: 09:15-09:30).
  - Price > ORB high -> positive score scaled by breakout distance relative to range.
  - Price < ORB low  -> negative score scaled by breakdown distance relative to range.
  - Inside range     -> small lean based on position in range.
  - Zero-width range guardrail.
  - Removed "first bar must be green" constraint.

Agent 2 (News Sentiment):
  - Evaluated in simulation.news, returns directional net sentiment (-1.0 to +1.0).

Agent 3 (VWAP-band Mean Reversion):
  - z = (price - VWAP) / sigma.
  - Score = -clamp(z / 2, -1.0, 1.0); acts from ~1σ.
  - RSI(14) adjustments: < 35 -> +0.2, > 65 -> -0.2.
  - Skip if fewer than 12 bars exist.

Each agent returns: { score: -1..+1, confidence: 0..100, signal: BUY|SELL|HOLD, reason: str, facts: dict }
"""
import datetime
from typing import Dict, Any, Optional, List
from simulation import config
from simulation.config import DEFAULT_CONFIG

# ─────────────────────────────────────────────────────────────────────────────
# AGENT 1 — ORB + VWAP Trend (Graded Continuous Score)
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_orb_vwap_agent(
    candles_5m_today: List[Dict[str, Any]],
    indicators: Dict[str, Any],
    is_holding: bool,
    entry_type: Optional[str] = None,
    entry_price: Optional[float] = None,
    avg_opening_volume: float = 0.0,
    orb_entry_done_today: bool = False,
    stop_loss_pct: float = 1.0,
    highest_close_since_entry: float = 0.0,
    position_side: str = "LONG",
) -> Dict[str, Any]:
    """
    Agent 1 — ORB + VWAP Trend Agent.
    Calculates opening range from the first 3 five-minute bars (first 15 min).
    Returns continuous score in [-1.0, +1.0] and confidence in [0, 100].
    """
    if not candles_5m_today:
        return {
            "score": 0.0,
            "confidence": 0.0,
            "signal": "HOLD",
            "reason": "No candles available yet",
            "facts": {}
        }

    current_bar = candles_5m_today[-1]
    current_time = str(current_bar.get("time_str") or current_bar.get("time") or "09:15")
    close = float(current_bar.get("close", 0.0))
    vwap = float(indicators.get("vwap", close))
    atr = float(indicators.get("atr", 0.0))

    # Opening Range: first 3 five-minute bars (first 15 min)
    bars_count = len(candles_5m_today)
    if bars_count <= 3:
        range_bars = candles_5m_today[:max(1, bars_count - 1)] if bars_count > 1 else candles_5m_today[:1]
    else:
        range_bars = candles_5m_today[:3]

    orb_high = max(float(b["high"]) for b in range_bars)
    orb_low = min(float(b["low"]) for b in range_bars)

    first_bar = candles_5m_today[0]
    first_bar_vol = first_bar.get("volume", 0)
    first_bar_green = first_bar["close"] >= first_bar["open"]

    # In play check
    in_play_mult = getattr(config, "ORB_IN_PLAY_VOLUME_MULTIPLIER", 1.5)
    in_play = (avg_opening_volume <= 0) or (first_bar_vol >= in_play_mult * avg_opening_volume)

    # Range width with zero-width guardrail
    min_guard = max(close * DEFAULT_CONFIG.orb_min_range_pct, DEFAULT_CONFIG.tick_size)
    range_width = max(orb_high - orb_low, min_guard)

    facts = {
        "orb_high": round(orb_high, 2),
        "orb_low": round(orb_low, 2),
        "range_width": round(range_width, 2),
        "bars_count": bars_count,
        "first_bar_green": first_bar_green,
        "first_bar_vol": first_bar_vol,
        "avg_opening_volume": round(avg_opening_volume, 0),
        "in_play": in_play,
        "close": round(close, 2),
        "vwap": round(vwap, 2),
        "atr": round(atr, 2),
        "orb_entry_done": orb_entry_done_today,
    }

    # ─────────────────────────────────────────────────────────────
    # CASE 1: Flat -> evaluate entry score
    # ─────────────────────────────────────────────────────────────
    if not is_holding:
        if not in_play:
            return {
                "score": 0.0,
                "confidence": 40.0,
                "signal": "HOLD",
                "reason": f"Stock not in play today (opening volume {first_bar_vol:,.0f} < {in_play_mult}x avg {avg_opening_volume:,.0f})",
                "facts": facts,
                "orb_high": orb_high,
                "orb_low": orb_low,
                "is_in_play": in_play
            }

        if close > orb_high:
            # Bullish Breakout above ORB High
            breakout_dist = close - orb_high
            breakout_ratio = breakout_dist / range_width
            score = min(1.0, round(0.40 + breakout_ratio * 0.60, 3))
            
            if close > vwap:
                score = min(1.0, score + 0.10)
                
            conf = min(95.0, round(50.0 + min(45.0, breakout_ratio * 50.0), 1))
            sig = "BUY"
            reason = (f"ORB breakout above high ₹{orb_high:.2f} (+₹{breakout_dist:.2f}, "
                      f"{breakout_ratio*100:.1f}% of range; VWAP ₹{vwap:.2f})")
        elif close < orb_low:
            # Bearish Breakdown below ORB Low
            breakdown_dist = orb_low - close
            breakdown_ratio = breakdown_dist / range_width
            score = -min(1.0, round(0.40 + breakdown_ratio * 0.60, 3))
            
            if close < vwap:
                score = max(-1.0, score - 0.10)
                
            conf = min(95.0, round(50.0 + min(45.0, breakdown_ratio * 50.0), 1))
            sig = "SELL"
            reason = (f"ORB breakdown below low ₹{orb_low:.2f} (-₹{breakdown_dist:.2f}, "
                      f"{breakdown_ratio*100:.1f}% of range; VWAP ₹{vwap:.2f})")
        else:
            # Inside Range -> small lean based on position in range
            mid = (orb_high + orb_low) / 2.0
            half_width = range_width / 2.0
            lean = (close - mid) / (half_width + 1e-9)
            score = round(max(-0.25, min(0.25, lean * 0.25)), 3)
            conf = min(60.0, round(30.0 + abs(lean) * 20.0, 1))
            sig = "HOLD"
            reason = (f"Inside opening range (₹{orb_low:.2f} - ₹{orb_high:.2f}, "
                      f"lean {score:+.2f}, VWAP ₹{vwap:.2f})")

        facts["score"] = score
        return {
            "score": score,
            "confidence": conf,
            "signal": sig,
            "reason": reason,
            "facts": facts,
            "orb_high": orb_high,
            "orb_low": orb_low,
            "is_in_play": in_play
        }

    # ─────────────────────────────────────────────────────────────
    # CASE 2: Holding Position -> evaluate exit rules
    # ─────────────────────────────────────────────────────────────
    entry_p = entry_price or close
    side = position_side.upper()
    profit = (close - entry_p) if side == "LONG" else (entry_p - close)
    initial_risk = entry_p * (stop_loss_pct / 100.0)
    max_profit = (highest_close_since_entry - entry_p) if (highest_close_since_entry > 0 and side == "LONG") else profit

    if side == "LONG":
        # Breakout failed exit: closed back below orb_high AND below VWAP
        if close < orb_high and close < vwap:
            return {
                "score": -0.80,
                "confidence": 85.0,
                "signal": "SELL",
                "reason": f"ORB breakout failed: close ₹{close:.2f} retreated below high ₹{orb_high:.2f} and VWAP ₹{vwap:.2f}",
                "facts": facts
            }
        # Trailing stop if in profit >= 1R
        if max_profit >= initial_risk and atr > 0 and highest_close_since_entry > 0:
            trailing_stop = highest_close_since_entry - DEFAULT_CONFIG.atr_stop_multiplier * atr
            if close < trailing_stop:
                return {
                    "score": -0.85,
                    "confidence": 80.0,
                    "signal": "SELL",
                    "reason": f"Trailing ATR stop hit: close ₹{close:.2f} < trailing stop ₹{trailing_stop:.2f}",
                    "facts": facts
                }
        return {
            "score": 0.40,
            "confidence": 60.0,
            "signal": "HOLD",
            "reason": f"ORB trade intact: close ₹{close:.2f}, VWAP ₹{vwap:.2f}, P&L ₹{profit:.2f}",
            "facts": facts
        }
    else:
        # SHORT position exit checks
        if close > orb_low and close > vwap:
            return {
                "score": 0.80,
                "confidence": 85.0,
                "signal": "BUY",
                "reason": f"ORB breakdown failed: price rallied above low ₹{orb_low:.2f} and VWAP ₹{vwap:.2f}",
                "facts": facts
            }
        return {
            "score": -0.40,
            "confidence": 60.0,
            "signal": "HOLD",
            "reason": f"ORB short position intact (close ₹{close:.2f}, VWAP ₹{vwap:.2f}, P&L ₹{profit:.2f})",
            "facts": facts
        }


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 3 — VWAP-band Mean Reversion (Graded Continuous Score)
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_vwap_reversion_agent(
    candles_5m_today: List[Dict[str, Any]],
    indicators: Dict[str, Any],
    is_holding: bool,
    entry_type: Optional[str] = None,
    entry_time_str: Optional[str] = None,
    entry_price: Optional[float] = None,
    stop_loss_pct: float = 1.0,
    round_trip_cost_pct: float = 0.001,
    position_side: str = "LONG",
) -> Dict[str, Any]:
    """
    Agent 3 — VWAP-band Mean Reversion Agent.
    z = (price - VWAP) / sigma.
    Score = -clamp(z / 2, -1.0, 1.0); acts from ~1σ.
    RSI(14): < 35 -> +0.2 boost; > 65 -> -0.2 drag.
    Skip if fewer than 12 bars exist.
    """
    if not candles_5m_today:
        return {"score": 0.0, "confidence": 0.0, "signal": "HOLD", "reason": "No candles", "facts": {}}

    close = float(candles_5m_today[-1]["close"])
    vwap = float(indicators.get("vwap", close))
    rsi = float(indicators.get("rsi", 50.0))
    sigma = float(indicators.get("vwap_sigma", 0.0))
    bars_count = len(candles_5m_today)
    current_time = candles_5m_today[-1].get("time", "10:30")

    effective_sigma = sigma if sigma > 0 else max(close * 0.002, 0.10)
    z = (close - vwap) / (effective_sigma + 1e-9)

    facts = {
        "close": round(close, 2),
        "vwap": round(vwap, 2),
        "sigma": round(effective_sigma, 4),
        "z_score": round(z, 2),
        "rsi": round(rsi, 1),
        "bars_count": bars_count,
    }

    # VETO check: market extended above VWAP + 2σ
    if sigma > 0 and close >= vwap + 2.0 * sigma:
        facts["veto_reason"] = f"Close ₹{close:.2f} >= VWAP+2σ ₹{vwap + 2*sigma:.2f}"
        return {
            "score": -0.80,
            "confidence": 80.0,
            "signal": "VETO_TREND",
            "reason": f"Market extended: close ₹{close:.2f} >= VWAP+2σ ₹{vwap + 2*sigma:.2f}; blocking trend entry",
            "facts": facts,
        }

    # ─────────────────────────────────────────────────────────────
    # CASE 1: Flat -> evaluate entry
    # ─────────────────────────────────────────────────────────────
    if not is_holding:
        if bars_count < 12:
            return {
                "score": 0.0,
                "confidence": 20.0,
                "signal": "HOLD",
                "reason": f"Only {bars_count} bars; need >= 12 for σ estimate",
                "facts": facts
            }

        # Base mean reversion score: -clamp(z / 2, -1.0, 1.0)
        base_score = -max(-1.0, min(1.0, z / DEFAULT_CONFIG.vwap_sigma_multiplier))

        rsi_adj = 0.0
        if rsi < DEFAULT_CONFIG.vwap_rsi_oversold:
            rsi_adj = 0.20
        elif rsi > DEFAULT_CONFIG.vwap_rsi_overbought:
            rsi_adj = -0.20

        final_score = max(-1.0, min(1.0, round(base_score + rsi_adj, 3)))
        conf_base = min(95.0, max(30.0, 40.0 + abs(z) * 25.0 + (abs(rsi - 50.0) / 50.0) * 20.0))
        confidence = round(conf_base, 1)

        facts["score"] = final_score

        if final_score >= 0.20 or (z <= -1.8 and rsi < 35):
            sig = "BUY"
            reason = (f"VWAP mean-reversion setup: close ₹{close:.2f} at VWAP-2σ, "
                      f"RSI {rsi:.1f} < 35; targeting VWAP ₹{vwap:.2f}")
        elif final_score <= -0.20 or (z >= 1.8 and rsi > 65):
            sig = "SELL"
            reason = (f"VWAP overextended peak (z={z:.2f}σ, RSI {rsi:.1f}); "
                      f"fading back to VWAP ₹{vwap:.2f}")
        else:
            sig = "HOLD"
            reason = f"Normal VWAP band (z={z:.2f}σ, RSI {rsi:.1f}, score {final_score:+.2f})"

        return {
            "score": final_score,
            "confidence": confidence,
            "signal": sig,
            "reason": reason,
            "facts": facts
        }

    # ─────────────────────────────────────────────────────────────
    # CASE 2: Holding Position -> evaluate mean reversion exit
    # ─────────────────────────────────────────────────────────────
    side = position_side.upper()
    if side == "LONG":
        if close >= vwap:
            return {
                "score": -0.80,
                "confidence": 85.0,
                "signal": "SELL",
                "reason": f"Mean reversion target reached: close ₹{close:.2f} >= VWAP ₹{vwap:.2f}",
                "facts": facts
            }
        # Thesis broken: fell below VWAP - 3 sigma
        if z <= -3.0 or (sigma > 0 and close <= (vwap - 3.0 * sigma)):
            return {
                "score": -0.90,
                "confidence": 90.0,
                "signal": "SELL",
                "reason": f"Reversion thesis broken: close ₹{close:.2f} <= VWAP-3σ; exit before further loss",
                "facts": facts
            }
        # 90-minute time stop
        if entry_time_str:
            try:
                entry_dt = datetime.datetime.strptime(entry_time_str, "%H:%M")
                curr_dt = datetime.datetime.strptime(current_time, "%H:%M")
                minutes_held = (curr_dt - entry_dt).seconds // 60
                if minutes_held >= 90:
                    return {
                        "score": -0.75,
                        "confidence": 75.0,
                        "signal": "SELL",
                        "reason": f"90-minute time stop: held {minutes_held} min without reaching VWAP target",
                        "facts": facts,
                    }
            except Exception:
                pass

        return {
            "score": 0.30,
            "confidence": 55.0,
            "signal": "HOLD",
            "reason": f"Holding reversion trade: close ₹{close:.2f}, target VWAP ₹{vwap:.2f}",
            "facts": facts
        }
    else:
        if close <= vwap:
            return {
                "score": 0.80,
                "confidence": 85.0,
                "signal": "BUY",
                "reason": f"Mean reversion short target reached: close ₹{close:.2f} <= VWAP ₹{vwap:.2f}",
                "facts": facts
            }
        if z >= 3.0 or (sigma > 0 and close >= (vwap + 3.0 * sigma)):
            return {
                "score": 0.90,
                "confidence": 90.0,
                "signal": "BUY",
                "reason": f"Reversion short thesis broken: close rose above VWAP + 3σ (z={z:.2f})",
                "facts": facts
            }
        return {
            "score": -0.30,
            "confidence": 55.0,
            "signal": "HOLD",
            "reason": f"Holding reversion short: close ₹{close:.2f}, target VWAP ₹{vwap:.2f}",
            "facts": facts
        }


# ─────────────────────────────────────────────────────────────────────────────
# DYNAMIC CONFIGURABLE AGENTS (Using Strategy Registry)
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_agent1(
    candles_5m_today: List[Dict[str, Any]],
    indicators: Dict[str, Any],
    is_holding: bool,
    entry_type: Optional[str] = None,
    entry_price: Optional[float] = None,
    avg_opening_volume: float = 0.0,
    orb_entry_done_today: bool = False,
    stop_loss_pct: float = 1.0,
    highest_close_since_entry: float = 0.0,
    position_side: str = "LONG",
    strategy_id: Optional[str] = None,
    strategy_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Agent 1 (Trend/Breakout) — Evaluates user-selected strategy from registry.
    Defaults to strat_orb (ORB).
    """
    from simulation.agent_config import agent_config_manager
    from simulation.strategies.registry import get_strategy

    cfg = agent_config_manager.get_config().get("agent1", {})
    if not cfg.get("enabled", True):
        return {
            "score": 0.0,
            "confidence": 0.0,
            "signal": "HOLD",
            "reason": "Agent 1 is disabled in configuration",
            "strategy_id": "disabled",
            "strategy_name": "Disabled",
            "facts": {"disabled": True}
        }

    sid = strategy_id or cfg.get("strategy_id", "strat_orb")
    params = strategy_params or cfg.get("params", {})
    strategy = get_strategy(sid, params)

    res = strategy.evaluate(
        candles_5m_today=candles_5m_today,
        indicators=indicators,
        is_holding=is_holding,
        position_side=position_side,
        entry_price=entry_price,
        highest_close_since_entry=highest_close_since_entry,
        avg_opening_volume=avg_opening_volume,
        orb_entry_done_today=orb_entry_done_today,
        stop_loss_pct=stop_loss_pct,
        entry_type=entry_type
    )
    res["strategy_id"] = sid
    res["strategy_name"] = strategy.name
    return res


def evaluate_agent3(
    candles_5m_today: List[Dict[str, Any]],
    indicators: Dict[str, Any],
    is_holding: bool,
    entry_type: Optional[str] = None,
    entry_time_str: Optional[str] = None,
    entry_price: Optional[float] = None,
    stop_loss_pct: float = 1.0,
    round_trip_cost_pct: float = 0.001,
    position_side: str = "LONG",
    highest_close_since_entry: float = 0.0,
    strategy_id: Optional[str] = None,
    strategy_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Agent 3 (Mean Reversion/Reversal) — Evaluates user-selected strategy from registry.
    Defaults to strat_bb_rsi_reversal.
    """
    from simulation.agent_config import agent_config_manager
    from simulation.strategies.registry import get_strategy

    cfg = agent_config_manager.get_config().get("agent3", {})
    if not cfg.get("enabled", True):
        return {
            "score": 0.0,
            "confidence": 0.0,
            "signal": "HOLD",
            "reason": "Agent 3 is disabled in configuration",
            "strategy_id": "disabled",
            "strategy_name": "Disabled",
            "facts": {"disabled": True}
        }

    sid = strategy_id or cfg.get("strategy_id", "strat_bb_rsi_reversal")
    params = strategy_params or cfg.get("params", {})
    strategy = get_strategy(sid, params)

    res = strategy.evaluate(
        candles_5m_today=candles_5m_today,
        indicators=indicators,
        is_holding=is_holding,
        position_side=position_side,
        entry_price=entry_price,
        highest_close_since_entry=highest_close_since_entry,
        entry_type=entry_type,
        entry_time_str=entry_time_str,
        stop_loss_pct=stop_loss_pct,
        round_trip_cost_pct=round_trip_cost_pct
    )
    res["strategy_id"] = sid
    res["strategy_name"] = strategy.name
    return res


# ─────────────────────────────────────────────────────────────────────────────
# BACKWARD COMPATIBILITY WRAPPERS
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_trend_agent(indicators: Dict[str, Any], is_holding: bool) -> Dict[str, Any]:
    """Legacy wrapper kept for backward compatibility."""
    price = indicators.get("price", 0.0)
    ema9 = indicators.get("ema9", 0.0)
    ema21 = indicators.get("ema21", 0.0)
    rsi = indicators.get("rsi", 50.0)
    vwap = indicators.get("vwap", 0.0)
    score_val = 1 if ema9 > ema21 else (-1 if ema9 < ema21 else 0)
    sig = "BUY" if score_val > 0 else ("SELL" if score_val < 0 else "HOLD")
    return {
        "score": float(score_val * 0.5),
        "confidence": 60.0,
        "signal": sig,
        "reason": f"EMA trend: EMA9 {'above' if ema9 > ema21 else 'below'} EMA21",
        "facts": {"price": price, "ema9": ema9, "ema21": ema21, "rsi": rsi, "vwap": vwap}
    }

def evaluate_contrarian_agent(
    indicators: Dict[str, Any],
    is_holding: bool,
    entry_type: Optional[str] = None,
    entry_price: Optional[float] = None
) -> Dict[str, Any]:
    """Legacy wrapper kept for backward compatibility."""
    price = indicators.get("price", 0.0)
    vwap = indicators.get("vwap", 0.0)
    rsi = indicators.get("rsi", 50.0)
    sig = "BUY" if rsi < 35 else ("SELL" if rsi > 65 else "HOLD")
    return {
        "score": 0.5 if sig == "BUY" else (-0.5 if sig == "SELL" else 0.0),
        "confidence": 60.0,
        "signal": sig,
        "reason": f"Contrarian RSI: {rsi:.1f}",
        "facts": {"price": price, "vwap": vwap, "rsi": rsi}
    }
