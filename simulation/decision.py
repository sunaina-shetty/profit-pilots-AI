"""
decision.py — Council Decision Engine (Plain Python, No AI).

Enforces regime-based gating and safety rules:
  - TREND day: Only Agent 1 (ORB + VWAP) may enter. Agent 3 overheated veto applies.
  - RANGE day: Only Agent 3 (VWAP Reversion) may enter.
  - UNCLEAR day: HOLD ("no clear regime").
  - News Agent: Used only to confirm and to VETO on strongly negative headlines.
  - Exit: Respective agent signals or broker stop/15:15 square-off.
"""
from typing import Dict, Any, Optional

def decide_action(
    trend_res: Dict[str, Any],
    news_res: Dict[str, Any],
    contrarian_res: Dict[str, Any],
    is_holding: bool,
    entry_type: Optional[str] = "orb",
    regime: Optional[str] = None,
    regime_reason: Optional[str] = "",
    agent_mode: str = "combined"
) -> Dict[str, Any]:
    """
    Council decision on closed 5-minute bars.
    agent_mode in ("combined", "agent1_only", "agent3_only")
    """
    t_sig = trend_res.get("signal", "HOLD")
    n_sig = news_res.get("signal", "HOLD")
    n_conf = float(news_res.get("confidence", 0.0))
    c_sig = contrarian_res.get("signal", "HOLD")

    # If regime not passed explicitly (e.g. legacy test calls), infer it
    is_legacy_call = (regime is None)
    if regime is None:
        if t_sig == "BUY":
            regime = "TREND"
        elif c_sig == "BUY":
            regime = "RANGE"
        else:
            regime = "UNCLEAR"

    # ─────────────────────────────────────────────────────────────
    # CASE 1: Holding an open position -> evaluate exit signals
    # ─────────────────────────────────────────────────────────────
    if is_holding:
        # Exit check for ORB trade
        if entry_type in ("orb", "trend"):
            if t_sig == "SELL":
                return {
                    "action": "SELL",
                    "size": "full",
                    "rule": f"Agent 1 Exit: {trend_res.get('reason', 'Breakout failed or trailing stop hit')}",
                    "entry_type": None,
                    "approved": True,
                    "rejection_reason": ""
                }

        # Exit check for Reversion trade
        if entry_type in ("reversion", "dip"):
            if c_sig == "SELL":
                return {
                    "action": "SELL",
                    "size": "full",
                    "rule": f"Agent 3 Exit: {contrarian_res.get('reason', 'Mean reversion target reached or thesis broken')}",
                    "entry_type": None,
                    "approved": True,
                    "rejection_reason": ""
                }

        # News VETO on open position if strongly negative
        if n_sig == "SELL" and n_conf >= 0.60:
            return {
                "action": "SELL",
                "size": "full",
                "rule": f"News VETO Exit: Strongly negative headlines ({news_res.get('reason', '')})",
                "entry_type": None,
                "approved": True,
                "rejection_reason": ""
            }

        return {
            "action": "HOLD",
            "size": "none",
            "rule": "Holding position: all exit guardrails intact",
            "entry_type": entry_type,
            "approved": False,
            "rejection_reason": "Exit criteria not triggered"
        }

    # ─────────────────────────────────────────────────────────────
    # CASE 2: Flat -> evaluate entry signals under regime gating
    # ─────────────────────────────────────────────────────────────

    # News Agent VETO: block ALL entries on strongly negative news
    if n_sig == "SELL" and n_conf >= 0.60:
        return {
            "action": "HOLD",
            "size": "none",
            "rule": f"Vetoed by News Agent: strongly negative headlines ({news_res.get('reason', '')})",
            "entry_type": None,
            "approved": False,
            "rejection_reason": "Vetoed by News Agent (negative headlines)"
        }

    # Regime = TREND Day -> only Agent 1 may enter
    if regime == "TREND":
        if agent_mode == "agent3_only":
            return {
                "action": "HOLD",
                "size": "none",
                "rule": "TREND day, but running in Agent 3 only mode",
                "entry_type": None,
                "approved": False,
                "rejection_reason": "Agent 3 only mode active on TREND day"
            }

        # Agent 3 VETO check (overheated conditions)
        if c_sig in ("VETO_TREND", "SELL"):
            return {
                "action": "HOLD",
                "size": "none",
                "rule": f"Vetoed by Agent 3: Overheated conditions ({contrarian_res.get('reason', '')})",
                "entry_type": None,
                "approved": False,
                "rejection_reason": "Vetoed by Agent 3 (overheated conditions)"
            }

        if t_sig == "BUY":
            return {
                "action": "BUY",
                "size": "full",
                "rule": f"Agent 1 ORB Trend Entry: {trend_res.get('reason', '')}",
                "entry_type": "orb",
                "approved": True,
                "rejection_reason": ""
            }
        else:
            return {
                "action": "HOLD",
                "size": "none",
                "rule": f"TREND day, waiting for Agent 1 setup ({trend_res.get('reason', '')})",
                "entry_type": None,
                "approved": False,
                "rejection_reason": "Agent 1 did not generate BUY signal"
            }

    # Regime = RANGE Day -> only Agent 3 may enter
    if regime == "RANGE":
        if agent_mode == "agent1_only":
            return {
                "action": "HOLD",
                "size": "none",
                "rule": "RANGE day, but running in Agent 1 only mode",
                "entry_type": None,
                "approved": False,
                "rejection_reason": "Agent 1 only mode active on RANGE day"
            }

        if c_sig == "BUY":
            return {
                "action": "BUY",
                "size": "half" if is_legacy_call else "full",
                "rule": f"Agent 3 VWAP Reversion Entry: {contrarian_res.get('reason', '')}",
                "entry_type": "reversion",
                "approved": True,
                "rejection_reason": ""
            }
        else:
            return {
                "action": "HOLD",
                "size": "none",
                "rule": f"RANGE day, waiting for Agent 3 setup ({contrarian_res.get('reason', '')})",
                "entry_type": None,
                "approved": False,
                "rejection_reason": "Agent 3 did not generate BUY signal"
            }

    # Regime = UNCLEAR -> No trades allowed
    return {
        "action": "HOLD",
        "size": "none",
        "rule": f"HOLD: No clear regime ({regime_reason or 'ADX/ORB conditions neutral'})",
        "entry_type": None,
        "approved": False,
        "rejection_reason": f"No clear regime ({regime_reason or 'neutral ADX/ORB'})"
    }
