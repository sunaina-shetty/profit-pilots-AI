"""
decision.py — Council Decision Engine using Continuous Weighted Scoring.

Council = weighted score, not unanimous gate:
  - Regime-aware weights:
      TREND: ORB 0.5, News 0.3, VWAP 0.2
      RANGE: ORB 0.2, News 0.3, VWAP 0.5
      UNCLEAR / DEFAULT: ORB 0.35, News 0.30, VWAP 0.35
  - S = weighted sum of agent scores (-1.0 to +1.0)
  - Agreement = fraction of active agents whose sign matches sign(S)
  - Confidence % = 100 * clamp(|S| * 1.6 * (0.6 + 0.4 * agreement), 0, 1)
  - BUY if S >= 0.15 and confidence >= 40
  - SELL if S <= -0.15 and confidence >= 40
  - HOLD otherwise, with reason explaining distance to trigger (e.g. "Score +0.09, needs +0.15 for BUY")
  - News VETO: only on strong-negative for BUY (< -0.50) and strong-positive for SHORT (> +0.50).
"""
import math
from typing import Dict, Any, Optional
from simulation.config import DEFAULT_CONFIG

def decide_action(
    trend_res: Dict[str, Any],
    news_res: Dict[str, Any],
    contrarian_res: Dict[str, Any],
    is_holding: bool,
    entry_type: Optional[str] = "orb",
    regime: Optional[str] = None,
    regime_reason: Optional[str] = "",
    agent_mode: str = "combined",
    position_side: str = "LONG",
) -> Dict[str, Any]:
    """
    Evaluates Council Consensus via continuous weighted scoring.
    Supports both graded continuous score dictionaries and legacy signal string dictionaries.
    """
    t_sig = trend_res.get("signal", "HOLD")
    n_sig = news_res.get("signal", "HOLD")
    n_conf = float(news_res.get("confidence", 0.0))
    c_sig = contrarian_res.get("signal", "HOLD")

    # 1. Extract agent scores with fallback from signal strings
    if "score" in trend_res:
        s_orb = float(trend_res["score"])
    else:
        s_orb = 0.60 if t_sig == "BUY" else (-0.60 if t_sig == "SELL" else 0.0)

    if "score" in news_res:
        s_news = float(news_res["score"])
    else:
        s_news = 0.60 if n_sig == "BUY" else (-0.60 if n_sig == "SELL" else 0.0)

    if "score" in contrarian_res:
        s_vwap = float(contrarian_res["score"])
    else:
        s_vwap = 0.60 if c_sig == "BUY" else (-0.80 if c_sig in ("SELL", "VETO_TREND") else 0.0)

    is_legacy_call = (regime is None)
    if regime is None:
        if t_sig == "BUY" or abs(s_orb) > abs(s_vwap):
            regime = "TREND"
        elif c_sig == "BUY" or abs(s_vwap) > 0.40:
            regime = "RANGE"
        else:
            regime = "UNCLEAR"

    regime_upper = (regime or "UNCLEAR").upper()
    if regime_upper == "TREND":
        weights = DEFAULT_CONFIG.weights_trend
    elif regime_upper == "RANGE":
        weights = DEFAULT_CONFIG.weights_range
    else:
        weights = DEFAULT_CONFIG.weights_unclear

    w_orb = weights.get("orb", 0.35)
    w_news = weights.get("news", 0.30)
    w_vwap = weights.get("vwap", 0.35)

    if agent_mode == "agent1_only":
        w_orb, w_news, w_vwap = 0.70, 0.30, 0.0
    elif agent_mode == "agent3_only":
        w_orb, w_news, w_vwap = 0.0, 0.30, 0.70

    S = (w_orb * s_orb) + (w_news * s_news) + (w_vwap * s_vwap)
    S = max(-1.0, min(1.0, round(S, 3)))

    active_scores = [s_orb, s_news, s_vwap]
    if agent_mode == "agent1_only":
        active_scores = [s_orb, s_news]
    elif agent_mode == "agent3_only":
        active_scores = [s_news, s_vwap]

    if abs(S) < 1e-4:
        agreement = 1.0
    else:
        target_sign = 1 if S > 0 else -1
        matches = sum(1 for s in active_scores if (s * target_sign) > 0)
        agreement = matches / max(1, len(active_scores))

    raw_conf = abs(S) * 1.6 * (0.6 + 0.4 * agreement)
    confidence = round(100.0 * max(0.0, min(1.0, raw_conf)), 1)

    # ─────────────────────────────────────────────────────────────
    # CASE 1: Holding an open position -> evaluate exits
    # ─────────────────────────────────────────────────────────────
    if is_holding:
        side = position_side.upper()
        if side == "LONG":
            if S <= DEFAULT_CONFIG.sell_trigger_score and confidence >= DEFAULT_CONFIG.exit_flip_min_confidence:
                return {
                    "action": "SELL",
                    "size": "full",
                    "rule": f"Council Flip to SELL: Score {S:+.2f}, Conf {confidence:.0f}%",
                    "entry_type": None,
                    "approved": True,
                    "rejection_reason": "",
                    "score": S,
                    "confidence": confidence,
                    "agreement": agreement,
                    "weights": weights
                }
            if s_news < DEFAULT_CONFIG.news_buy_veto_threshold or (n_sig == "SELL" and n_conf >= 0.60):
                return {
                    "action": "SELL",
                    "size": "full",
                    "rule": f"News VETO Exit: Strongly negative headlines ({news_res.get('reason', '')})",
                    "entry_type": None,
                    "approved": True,
                    "rejection_reason": "",
                    "score": S,
                    "confidence": confidence,
                    "agreement": agreement,
                    "weights": weights
                }
            if entry_type in ("orb", "trend") and t_sig == "SELL":
                return {
                    "action": "SELL",
                    "size": "full",
                    "rule": f"Agent 1 Exit: {trend_res.get('reason', 'Trailing stop or breakout breakdown')}",
                    "entry_type": None,
                    "approved": True,
                    "rejection_reason": "",
                    "score": S,
                    "confidence": confidence,
                    "agreement": agreement,
                    "weights": weights
                }
            if entry_type in ("reversion", "dip") and c_sig == "SELL":
                return {
                    "action": "SELL",
                    "size": "full",
                    "rule": f"Agent 3 Exit: {contrarian_res.get('reason', 'Mean reversion target reached')}",
                    "entry_type": None,
                    "approved": True,
                    "rejection_reason": "",
                    "score": S,
                    "confidence": confidence,
                    "agreement": agreement,
                    "weights": weights
                }
        else:
            # SHORT position exits
            if S >= DEFAULT_CONFIG.buy_trigger_score and confidence >= DEFAULT_CONFIG.exit_flip_min_confidence:
                return {
                    "action": "BUY",
                    "size": "full",
                    "rule": f"Council Flip to BUY: Score {S:+.2f}, Conf {confidence:.0f}%",
                    "entry_type": None,
                    "approved": True,
                    "rejection_reason": "",
                    "score": S,
                    "confidence": confidence,
                    "agreement": agreement,
                    "weights": weights
                }
            if s_news > DEFAULT_CONFIG.news_short_veto_threshold:
                return {
                    "action": "BUY",
                    "size": "full",
                    "rule": f"News VETO Exit: Strongly positive headlines ({s_news:+.2f} > +0.50)",
                    "entry_type": None,
                    "approved": True,
                    "rejection_reason": "",
                    "score": S,
                    "confidence": confidence,
                    "agreement": agreement,
                    "weights": weights
                }

        return {
            "action": "HOLD",
            "size": "none",
            "rule": f"Holding {side} position: Score {S:+.2f}, Conf {confidence:.0f}%, guardrails intact",
            "entry_type": entry_type,
            "approved": False,
            "rejection_reason": "Exit criteria not triggered",
            "score": S,
            "confidence": confidence,
            "agreement": agreement,
            "weights": weights
        }

    # ─────────────────────────────────────────────────────────────
    # CASE 2: Flat -> evaluate entry signals
    # ─────────────────────────────────────────────────────────────

    # News Agent VETO: strongly negative headlines
    if (s_news < DEFAULT_CONFIG.news_buy_veto_threshold) or (n_sig == "SELL" and n_conf >= 0.60):
        return {
            "action": "HOLD",
            "size": "none",
            "rule": f"Vetoed by News Agent: strongly negative headlines ({news_res.get('reason', '')})",
            "entry_type": None,
            "approved": False,
            "rejection_reason": "Vetoed by News Agent (negative headlines)",
            "score": S,
            "confidence": confidence,
            "agreement": agreement,
            "weights": weights
        }

    # Agent 3 VETO: overheated conditions
    if c_sig in ("VETO_TREND", "SELL") and (S > 0 or t_sig == "BUY"):
        return {
            "action": "HOLD",
            "size": "none",
            "rule": f"Vetoed by Agent 3: Overheated conditions ({contrarian_res.get('reason', '')})",
            "entry_type": None,
            "approved": False,
            "rejection_reason": "Vetoed by Agent 3 (overheated conditions)",
            "score": S,
            "confidence": confidence,
            "agreement": agreement,
            "weights": weights
        }

    buy_thresh = DEFAULT_CONFIG.buy_trigger_score
    sell_thresh = DEFAULT_CONFIG.sell_trigger_score
    min_conf = DEFAULT_CONFIG.min_confidence

    # 6. Check Decision Triggers:
    buy_thresh = DEFAULT_CONFIG.buy_trigger_score
    sell_thresh = DEFAULT_CONFIG.sell_trigger_score
    min_conf = DEFAULT_CONFIG.min_confidence

    # BUY Entry
    if (S >= buy_thresh and confidence >= min_conf) or (t_sig == "BUY" and regime_upper == "TREND" and not is_legacy_call) or (c_sig == "BUY" and is_legacy_call):
        if c_sig == "BUY" and (is_legacy_call or regime_upper == "RANGE"):
            size = "half" if is_legacy_call else "full"
            e_type = "reversion"
            rule_msg = f"Agent 3 VWAP Reversion Entry: {contrarian_res.get('reason', '')}"
        elif s_orb >= s_vwap and (s_orb > 0.15 or t_sig == "BUY"):
            size = "full"
            e_type = "orb"
            rule_msg = f"Agent 1 ORB Trend Entry: {trend_res.get('reason', '')}" if is_legacy_call else f"Council Consensus BUY: Score {S:+.2f} >= {buy_thresh:+.2f}, Conf {confidence:.0f}%"
        else:
            size = "full"
            e_type = "council"
            rule_msg = f"Council Consensus BUY: Score {S:+.2f} >= {buy_thresh:+.2f}, Conf {confidence:.0f}%"

        return {
            "action": "BUY",
            "size": size,
            "rule": rule_msg,
            "entry_type": e_type,
            "approved": True,
            "rejection_reason": "",
            "score": S,
            "confidence": confidence,
            "agreement": agreement,
            "weights": weights
        }

    # SELL Entry (Short)
    if S <= sell_thresh and confidence >= min_conf:
        if s_orb <= s_vwap and s_orb < -0.15:
            e_type = "orb"
        elif s_vwap < -0.15:
            e_type = "reversion"
        else:
            e_type = "council"

        rule_msg = (f"Council Consensus SELL: Score {S:+.2f} <= {sell_thresh:+.2f}, "
                    f"Confidence {confidence:.0f}% >= {min_conf:.0f}% (regime: {regime})")
        return {
            "action": "SELL",
            "size": "full",
            "rule": rule_msg,
            "entry_type": e_type,
            "approved": True,
            "rejection_reason": "",
            "score": S,
            "confidence": confidence,
            "agreement": agreement,
            "weights": weights
        }

    # HOLD: Reason explaining distance to trigger
    if S >= 0.0:
        gap = buy_thresh - S
        if S < buy_thresh:
            reason = f"Score {S:+.2f}, needs +{buy_thresh:.2f} for BUY (gap: {gap:+.2f}, conf {confidence:.0f}%)"
            rej = f"Score {S:+.2f} below +{buy_thresh:.2f} trigger"
        else:
            reason = f"Score {S:+.2f} reached trigger, but confidence {confidence:.0f}% < {min_conf:.0f}%"
            rej = f"Confidence {confidence:.0f}% below {min_conf:.0f}%"
    else:
        gap = S - sell_thresh
        if S > sell_thresh:
            reason = f"Score {S:+.2f}, needs {sell_thresh:.2f} for SELL (gap: {gap:+.2f}, conf {confidence:.0f}%)"
            rej = f"Score {S:+.2f} above {sell_thresh:.2f} trigger"
        else:
            reason = f"Score {S:+.2f} reached trigger, but confidence {confidence:.0f}% < {min_conf:.0f}%"
            rej = f"Confidence {confidence:.0f}% below {min_conf:.0f}%"

    return {
        "action": "HOLD",
        "size": "none",
        "rule": reason,
        "entry_type": None,
        "approved": False,
        "rejection_reason": rej,
        "score": S,
        "confidence": confidence,
        "agreement": agreement,
        "weights": weights
    }
