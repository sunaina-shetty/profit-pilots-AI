from typing import Dict, Any, Tuple

def decide_action(
    trend_res: Dict[str, Any],
    news_res: Dict[str, Any],
    contrarian_res: Dict[str, Any],
    is_holding: bool,
    entry_type: str = "trend"
) -> Dict[str, Any]:
    """
    Decision Rule (Plain Python, No AI):
    - Holding:
        SELL if Trend=SELL (trend trade) or Contrarian=SELL or News=SELL with confidence>=0.6; else HOLD.
    - Flat and Trend=BUY:
        Contrarian=SELL -> HOLD (veto, overheated);
        News=SELL -> HOLD (veto);
        News=BUY -> BUY full size;
        otherwise BUY half size.
    - Flat, Trend not BUY, Contrarian=BUY, News not SELL:
        BUY half size (dip-buy).
    - Otherwise HOLD.
    """
    t_sig = trend_res.get("signal", "HOLD")
    n_sig = news_res.get("signal", "HOLD")
    c_sig = contrarian_res.get("signal", "HOLD")

    n_conf = news_res.get("confidence", 0.0)

    if is_holding:
        if t_sig == "SELL" and entry_type == "trend":
            return {
                "action": "SELL",
                "size": "full",
                "rule": "Trend breakdown exit (EMA9 crossed below EMA21 or closed below VWAP twice)",
                "entry_type": None
            }
        elif c_sig == "SELL":
            return {
                "action": "SELL",
                "size": "full",
                "rule": f"Contrarian exit ({contrarian_res.get('reason', '')})",
                "entry_type": None
            }
        elif n_sig == "SELL" and n_conf >= 0.6:
            return {
                "action": "SELL",
                "size": "full",
                "rule": f"News risk exit (News sentiment negative with confidence {int(n_conf*100)}%)",
                "entry_type": None
            }
        else:
            return {
                "action": "HOLD",
                "size": "none",
                "rule": "Holding current position: all exit guardrails intact",
                "entry_type": entry_type
            }

    # When flat (no open position)
    if t_sig == "BUY":
        if c_sig == "SELL":
            return {
                "action": "HOLD",
                "size": "none",
                "rule": "Vetoed by Contrarian Agent (Overheated conditions; do not chase top)",
                "entry_type": None
            }
        elif n_sig == "SELL":
            return {
                "action": "HOLD",
                "size": "none",
                "rule": "Vetoed by News Agent (Negative headlines outweigh technical setup)",
                "entry_type": None
            }
        elif n_sig == "BUY":
            return {
                "action": "BUY",
                "size": "full",
                "rule": "Trend confirmed by Positive News (Full Size)",
                "entry_type": "trend"
            }
        else:
            return {
                "action": "BUY",
                "size": "half",
                "rule": "Trend confirmed without conflicting news (Half Size)",
                "entry_type": "trend"
            }

    if t_sig != "BUY" and c_sig == "BUY" and n_sig != "SELL":
        return {
            "action": "BUY",
            "size": "half",
            "rule": "Contrarian Oversold Dip-Buy (Half Size)",
            "entry_type": "dip"
        }

    return {
        "action": "HOLD",
        "size": "none",
        "rule": "Neutral council state (No consensus setup; waiting for clear signal)",
        "entry_type": None
    }

