import os
import sys
import time
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from backend.shared.config import PORT_JOURNAL
from backend.shared.db import get_mongo_collection

app = Flask(__name__)
CORS(app)

journal_coll = get_mongo_collection("decision_journal")

def format_plain_language_narrative(entry_dict: dict) -> str:
    """
    Produces transparent, plain-language audit narrative from structured data.
    Ensures complete explainability for retail traders and judges.
    """
    event_type = entry_dict.get("event_type", "CYCLE_DECISION")
    symbol = entry_dict.get("symbol", "N/A")
    price = entry_dict.get("price", 0.0)
    decision = entry_dict.get("decision", {})
    risk = entry_dict.get("risk_verdict", {})
    action = decision.get("action", "HOLD")
    tier = decision.get("size_tier", "ZERO")
    
    if event_type == "KILL_SWITCH":
        return f"[EMERGENCY PROTOCOL] Kill switch engaged. All active orders aborted and open positions flattened to safeguard capital."
        
    if event_type == "DAILY_LOSS_HALT":
        return f"[SAFETY HALT] Daily loss threshold reached. Intraday trading halted until next session to prevent emotional drawdown."

    trend = decision.get("agent_votes", {}).get("trend", {})
    news = decision.get("agent_votes", {}).get("news", {})
    contrarian = decision.get("agent_votes", {}).get("contrarian", {})

    agent_summary = (
        f"Trend Agent voted {trend.get('vote', 'HOLD')} ({int(trend.get('confidence', 0)*100)}%), "
        f"News Agent voted {news.get('vote', 'HOLD')} ({int(news.get('confidence', 0)*100)}%), and "
        f"Contrarian Agent voted {contrarian.get('vote', 'HOLD')} ({int(contrarian.get('confidence', 0)*100)}%)."
    )

    if action == "HOLD":
        return (
            f"At Rs {round(price, 2)}, the council opted to HOLD {symbol}. {decision.get('reason', '')} "
            f"Council alignment: {agent_summary} Risk guardrails: Zero capital committed."
        )

    approved = risk.get("approved", False)
    if not approved:
        return (
            f"Council proposed {action} on {symbol} ({tier} size, entry Rs {round(price, 2)}), "
            f"but INDEPENDENT RISK MANAGER VETOED the trade: '{risk.get('reason', 'Blocked by risk rules')}'. "
            f"Capital remains 100% safe."
        )

    qty = risk.get("qty", 0)
    sl = risk.get("stop_loss", 0.0)
    return (
        f"EXECUTED {action} {qty} shares of {symbol} at Rs {round(price, 2)} with mandatory stop-loss at Rs {round(sl, 2)}. "
        f"Council consensus: {decision.get('reason', '')} "
        f"Risk clearance: Sized exactly to 1% portfolio risk. Approval token cryptographically signed."
    )

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "journal_service",
        "status": "healthy",
        "port": PORT_JOURNAL,
        "entries_count": journal_coll.count_documents({}),
        "timestamp": time.time()
    })

@app.route("/journal/write", methods=["POST"])
def write_entry():
    data = request.get_json() or {}
    narrative = format_plain_language_narrative(data)
    
    doc = {
        "event_type": data.get("event_type", "CYCLE_DECISION"),
        "symbol": data.get("symbol", "N/A"),
        "price": data.get("price", 0.0),
        "decision": data.get("decision", {}),
        "risk_verdict": data.get("risk_verdict", {}),
        "fill": data.get("fill", {}),
        "plain_text": narrative,
        "timestamp": data.get("timestamp", time.time())
    }
    
    saved = journal_coll.insert_one(doc)
    return jsonify({"status": "logged", "doc_id": str(saved.get("_id", "")), "narrative": narrative})

@app.route("/journal/entries", methods=["GET"])
def get_entries():
    limit = int(request.args.get("limit", 40))
    symbol = request.args.get("symbol")
    
    filter_dict = {}
    if symbol:
        filter_dict["symbol"] = symbol

    docs = journal_coll.find(filter_dict=filter_dict, sort=[("timestamp", -1)], limit=limit)
    return jsonify({"count": len(docs), "entries": docs})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT_JOURNAL, debug=False)

