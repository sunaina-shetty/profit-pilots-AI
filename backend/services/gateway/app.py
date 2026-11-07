import os
import sys
import time
import json
import queue
import threading
import requests
from flask import Flask, jsonify, request, Response
from flask_cors import CORS

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from backend.shared.config import (
    PORT_GATEWAY, URL_DATA, URL_AGENTS, URL_DECISION, URL_RISK,
    URL_EXCHANGE, URL_JOURNAL, URL_BACKTEST, URL_CHAOS, DEFAULT_SYMBOL
)

app = Flask(__name__)
CORS(app)

# Event broadcast bus for SSE clients
client_queues = []
clients_lock = threading.Lock()

# Autonomous trading loop controller
loop_running = False
loop_thread = None
active_symbol = DEFAULT_SYMBOL
loop_interval_sec = 4.0

def broadcast_event(event_name: str, payload: dict):
    """Pushes a typed SSE event to all connected frontend streams."""
    message = f"event: {event_name}\ndata: {json.dumps(payload)}\n\n"
    with clients_lock:
        stale_queues = []
        for q in client_queues:
            try:
                q.put_nowait(message)
            except Exception:
                stale_queues.append(q)
        for sq in stale_queues:
            if sq in client_queues:
                client_queues.remove(sq)

def execute_trading_cycle(symbol: str) -> dict:
    """
    Complete end-to-end autonomous trading cycle:
    1. Fetch market data & bars (data_service)
    2. Check freshness / reliability
    3. Evaluate 3 independent agents (agents_service)
    4. Aggregate votes into consensus decision (decision_service)
    5. Evaluate independent risk guardrails (risk_service)
    6. If approved, execute order with token (exchange_service)
    7. Update positions on price tick (exchange_service)
    8. Write explainable narrative to journal (journal_service)
    9. Broadcast all events to live dashboard
    """
    cycle_time = time.time()
    result = {"symbol": symbol, "timestamp": cycle_time}

    # 1. Fetch market data
    try:
        mkt_res = requests.get(f"{URL_DATA}/market/{symbol}", timeout=2).json()
        hist_res = requests.get(f"{URL_DATA}/history/{symbol}?bars=40", timeout=2).json()
        news_res = requests.get(f"{URL_DATA}/news/{symbol}", timeout=2).json()
    except Exception as e:
        broadcast_event("system_state", {"state": "DATA_SERVICE_UNAVAILABLE", "error": str(e), "ts": cycle_time})
        return {"error": f"Data service error: {str(e)}"}

    curr_price = float(mkt_res.get("price", 0.0))
    is_data_stale = bool(mkt_res.get("is_stale", False))
    is_news_stale = bool(news_res.get("is_stale", False))
    bars = hist_res.get("bars", [])
    news_items = news_res.get("news", [])

    # Broadcast price tick
    broadcast_event("price_tick", {
        "symbol": symbol,
        "price": curr_price,
        "is_stale": is_data_stale,
        "ts": cycle_time
    })

    # Evaluate open positions on this price tick
    try:
        requests.post(f"{URL_EXCHANGE}/tick", json={"symbol": symbol, "price": curr_price}, timeout=2)
    except Exception:
        pass

    # 2. Check risk system state
    try:
        risk_limits = requests.get(f"{URL_RISK}/limits", timeout=2).json()
        sys_state = risk_limits.get("market_state", "RUNNING")
        if risk_limits.get("kill_switch") == "ON":
            sys_state = "KILLED"
        elif is_data_stale:
            sys_state = "DATA_STALE"
            
        broadcast_event("system_state", {
            "state": sys_state,
            "kill_switch": risk_limits.get("kill_switch", "OFF"),
            "loss_limit_hit": risk_limits.get("is_loss_limit_hit", False),
            "loss_used_pct": risk_limits.get("loss_used_pct", 0.0),
            "ts": cycle_time
        })
    except Exception:
        sys_state = "RUNNING"

    # 3. Call 3 independent agents
    try:
        agents_res = requests.post(
            f"{URL_AGENTS}/evaluate",
            json={"symbol": symbol, "bars": bars, "news": news_items},
            timeout=2
        ).json()
        
        broadcast_event("agent_votes", {
            "symbol": symbol,
            "trend": agents_res.get("trend"),
            "news": agents_res.get("news"),
            "contrarian": agents_res.get("contrarian"),
            "ts": cycle_time
        })
    except Exception as e:
        agents_res = {"trend": {"vote": "HOLD"}, "news": {"vote": "HOLD"}, "contrarian": {"vote": "HOLD"}}

    # 4. Consensus Decision
    try:
        decision_res = requests.post(
            f"{URL_DECISION}/decide",
            json={
                "symbol": symbol,
                "price": curr_price,
                "trend": agents_res.get("trend"),
                "news": agents_res.get("news"),
                "contrarian": agents_res.get("contrarian")
            },
            timeout=2
        ).json()

        broadcast_event("decision", {
            "symbol": symbol,
            "action": decision_res.get("action"),
            "size_tier": decision_res.get("size_tier"),
            "confidence": decision_res.get("confidence"),
            "reason": decision_res.get("reason"),
            "suggested_stop": decision_res.get("suggested_stop"),
            "suggested_target": decision_res.get("suggested_target"),
            "ts": cycle_time
        })
    except Exception as e:
        decision_res = {"action": "HOLD", "size_tier": "ZERO", "reason": f"Decision error: {str(e)}"}

    action = decision_res.get("action", "HOLD")
    risk_res = {"approved": False, "reason": "No actionable consensus (HOLD)"}
    fill_res = None

    # 5. Risk Evaluation (if actionable)
    if action in ["BUY", "SELL"]:
        try:
            risk_payload = {
                "symbol": symbol,
                "side": action,
                "entry_price": curr_price,
                "stop_loss": decision_res.get("suggested_stop", 0.0),
                "size_tier": decision_res.get("size_tier", "FULL"),
                "data_fresh": not is_data_stale,
                "news_fresh": not is_news_stale
            }
            risk_res = requests.post(f"{URL_RISK}/evaluate", json=risk_payload, timeout=2).json()
            broadcast_event("risk_verdict", risk_res)

            # 6. Execute Order if Approved
            if risk_res.get("approved"):
                order_payload = {
                    "symbol": symbol,
                    "side": action,
                    "qty": risk_res.get("qty"),
                    "entry_price": curr_price,
                    "stop_loss": risk_res.get("stop_loss"),
                    "take_profit": decision_res.get("suggested_target"),
                    "approval_token": risk_res.get("approval_token")
                }
                order_exec = requests.post(f"{URL_EXCHANGE}/order", json=order_payload, timeout=2).json()
                if "order_id" in order_exec:
                    fill_res = order_exec
                    broadcast_event("order_filled", fill_res)
        except Exception as e:
            risk_res = {"approved": False, "reason": f"Execution pipeline error: {str(e)}"}

    # 7. Write to Journal
    try:
        journal_payload = {
            "symbol": symbol,
            "price": curr_price,
            "decision": decision_res,
            "risk_verdict": risk_res,
            "fill": fill_res,
            "timestamp": cycle_time
        }
        j_res = requests.post(f"{URL_JOURNAL}/journal/write", json=journal_payload, timeout=2).json()
        broadcast_event("journal_entry", {
            "text": j_res.get("narrative", ""),
            "symbol": symbol,
            "ts": cycle_time
        })
    except Exception:
        pass

    # 8. Broadcast Updated Portfolio Metrics
    try:
        portfolio_res = requests.get(f"{URL_EXCHANGE}/portfolio", timeout=2).json()
        limits_res = requests.get(f"{URL_RISK}/limits", timeout=2).json()
        broadcast_event("portfolio", {
            "cash": portfolio_res.get("cash", 100000.0),
            "equity": portfolio_res.get("equity", 100000.0),
            "day_pnl": portfolio_res.get("day_pnl", 0.0),
            "realized_pnl": portfolio_res.get("realized_pnl", 0.0),
            "unrealized_pnl": portfolio_res.get("unrealized_pnl", 0.0),
            "positions": portfolio_res.get("positions", []),
            "loss_limit_used_pct": limits_res.get("loss_used_pct", 0.0),
            "loss_limit_amount": limits_res.get("daily_loss_limit_amount", 2000.0),
            "ts": cycle_time
        })
    except Exception:
        pass

    return {
        "status": "success",
        "symbol": symbol,
        "price": curr_price,
        "action": action,
        "risk_approved": risk_res.get("approved", False),
        "fill": fill_res
    }

def trading_loop_worker():
    global loop_running
    while loop_running:
        try:
            execute_trading_cycle(active_symbol)
        except Exception as e:
            print(f"Error in trading cycle: {e}")
        time.sleep(loop_interval_sec)

# ----------------- HTTP Routes ----------------- #
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "gateway",
        "status": "healthy",
        "port": PORT_GATEWAY,
        "loop_running": loop_running,
        "active_symbol": active_symbol,
        "connected_clients": len(client_queues),
        "timestamp": time.time()
    })

@app.route("/stream", methods=["GET"])
def sse_stream():
    """Real-time SSE event stream for React frontend."""
    client_q = queue.Queue(maxsize=100)
    with clients_lock:
        client_queues.append(client_q)

    def event_generator():
        # Send initial handshake
        yield f"event: connected\ndata: {json.dumps({'message': 'ProfitPilot SSE stream active'})}\n\n"
        while True:
            try:
                msg = client_q.get(timeout=20.0)
                yield msg
            except queue.Empty:
                # Keepalive ping
                yield f": ping\n\n"
            except GeneratorExit:
                break

    return Response(event_generator(), mimetype="text/event-stream")

@app.route("/loop/start", methods=["POST"])
def start_loop():
    global loop_running, loop_thread, active_symbol, loop_interval_sec
    data = request.get_json() or {}
    active_symbol = data.get("symbol", active_symbol)
    loop_interval_sec = float(data.get("interval_sec", 4.0))

    if not loop_running:
        loop_running = True
        loop_thread = threading.Thread(target=trading_loop_worker, daemon=True)
        loop_thread.start()

    return jsonify({"status": "running", "symbol": active_symbol, "interval_sec": loop_interval_sec})

@app.route("/loop/stop", methods=["POST"])
def stop_loop():
    global loop_running
    loop_running = False
    return jsonify({"status": "stopped"})

@app.route("/loop/status", methods=["GET"])
def loop_status():
    return jsonify({
        "loop_running": loop_running,
        "active_symbol": active_symbol,
        "interval_sec": loop_interval_sec
    })

@app.route("/trade/step", methods=["POST"])
def trade_step():
    data = request.get_json() or {}
    sym = data.get("symbol", active_symbol)
    res = execute_trading_cycle(sym)
    return jsonify(res)

@app.route("/kill_switch", methods=["POST"])
def trigger_kill_switch():
    """Direct route for UI Emergency Kill Switch button."""
    data = request.get_json() or {}
    action = data.get("action", "ENGAGE")
    # 1. Update risk service
    r_res = requests.post(f"{URL_RISK}/kill_switch", json={"action": action}, timeout=2).json()
    
    # 2. If engaged, close all open positions
    if action == "ENGAGE":
        requests.post(f"{URL_EXCHANGE}/close_all", timeout=2)
        # Log emergency event to journal
        requests.post(f"{URL_JOURNAL}/journal/write", json={"event_type": "KILL_SWITCH", "timestamp": time.time()}, timeout=2)

    broadcast_event("system_state", {
        "state": "KILLED" if action == "ENGAGE" else "RUNNING",
        "kill_switch": "ON" if action == "ENGAGE" else "OFF",
        "ts": time.time()
    })
    return jsonify(r_res)

@app.route("/reset_all", methods=["POST"])
def reset_all():
    """Resets exchange balance and risk limits for a clean demo."""
    requests.post(f"{URL_EXCHANGE}/reset", timeout=2)
    requests.post(f"{URL_RISK}/reset_daily_limit", timeout=2)
    broadcast_event("system_state", {"state": "RUNNING", "kill_switch": "OFF", "ts": time.time()})
    return jsonify({"status": "all_reset_complete"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT_GATEWAY, debug=False, threaded=True)

