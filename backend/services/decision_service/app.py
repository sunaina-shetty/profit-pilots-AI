import os
import sys
import time
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from backend.shared.config import PORT_DECISION, DEFAULT_STOP_LOSS_PCT

app = Flask(__name__)
CORS(app)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "decision_service",
        "status": "healthy",
        "port": PORT_DECISION,
        "rules": "3/3 -> FULL, 2/3 -> HALF, <2/3 -> HOLD",
        "timestamp": time.time()
    })

@app.route("/decide", methods=["POST"])
def decide():
    """
    Consensus Decision Logic:
    - 3/3 agree BUY -> Action BUY, size FULL (100% allowed risk)
    - 2/3 agree BUY -> Action BUY, size HALF (50% allowed risk)
    - 3/3 agree SELL -> Action SELL, size FULL
    - 2/3 agree SELL -> Action SELL, size HALF
    - Any split or lack of majority -> Action HOLD, size ZERO
    """
    data = request.get_json() or {}
    symbol = data.get("symbol", "RELIANCE.NS")
    price = float(data.get("price", 0.0))
    trend = data.get("trend", {})
    news = data.get("news", {})
    contrarian = data.get("contrarian", {})

    t_vote = trend.get("vote", "HOLD").upper()
    n_vote = news.get("vote", "HOLD").upper()
    c_vote = contrarian.get("vote", "HOLD").upper()

    votes = [t_vote, n_vote, c_vote]
    buy_count = votes.count("BUY")
    sell_count = votes.count("SELL")
    hold_count = votes.count("HOLD")

    action = "HOLD"
    size_tier = "ZERO"
    reason = "No consensus among council agents"
    avg_confidence = (
        trend.get("confidence", 0.5) + news.get("confidence", 0.5) + contrarian.get("confidence", 0.5)
    ) / 3.0

    if buy_count == 3:
        action = "BUY"
        size_tier = "FULL"
        reason = "Unanimous Consensus (3/3): Trend, News, and Contrarian agree on BUY setup."
    elif buy_count == 2:
        action = "BUY"
        size_tier = "HALF"
        dissenting = "Trend" if t_vote != "BUY" else ("News" if n_vote != "BUY" else "Contrarian")
        reason = f"Supermajority (2/3): BUY approved with half size. Dissenting agent: {dissenting}."
    elif sell_count == 3:
        action = "SELL"
        size_tier = "FULL"
        reason = "Unanimous Consensus (3/3): All agents agree on SELL/FLATTEN setup."
    elif sell_count == 2:
        action = "SELL"
        size_tier = "HALF"
        dissenting = "Trend" if t_vote != "SELL" else ("News" if n_vote != "SELL" else "Contrarian")
        reason = f"Supermajority (2/3): SELL approved with half size. Dissenting agent: {dissenting}."
    else:
        action = "HOLD"
        size_tier = "ZERO"
        reason = f"Disagreement detected ({buy_count} BUY, {sell_count} SELL, {hold_count} HOLD). Disagreement is a risk signal -> HOLD."

    # Compute suggested entry, stop loss, and target based on price
    stop_distance = price * (DEFAULT_STOP_LOSS_PCT / 100.0)
    if action == "BUY":
        suggested_stop = round(price - stop_distance, 2)
        suggested_target = round(price + (stop_distance * 2.0), 2)  # 2:1 Reward:Risk
    elif action == "SELL":
        suggested_stop = round(price + stop_distance, 2)
        suggested_target = round(price - (stop_distance * 2.0), 2)
    else:
        suggested_stop = 0.0
        suggested_target = 0.0

    return jsonify({
        "symbol": symbol,
        "action": action,
        "size_tier": size_tier,
        "confidence": round(avg_confidence, 2),
        "reason": reason,
        "suggested_entry": price,
        "suggested_stop": suggested_stop,
        "suggested_target": suggested_target,
        "agent_votes": {
            "trend": trend,
            "news": news,
            "contrarian": contrarian
        },
        "timestamp": time.time()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT_DECISION, debug=False)

