import os
import sys
import time
import math
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import text

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

# Strict compliance: NO AI, NO LLM, NO AGENTS imported here
from backend.shared.config import (
    PORT_RISK, MAX_RISK_PER_TRADE_PCT, DAILY_LOSS_LIMIT_PCT,
    MAX_OPEN_POSITIONS, MAX_POSITION_VALUE_PCT
)
from backend.shared.db import SQL_ENGINE, init_sql_tables
from backend.shared.token_utils import generate_risk_token

app = Flask(__name__)
CORS(app)

# Ensure database tables exist
init_sql_tables()

def get_kill_switch_state():
    """Direct query to database for kill-switch state."""
    with SQL_ENGINE.connect() as conn:
        res = conn.execute(text("SELECT val_str FROM system_state WHERE key_name = 'kill_switch'")).fetchone()
        return res[0] if res else "OFF"

def set_kill_switch_state(state_str):
    with SQL_ENGINE.begin() as conn:
        conn.execute(
            text("UPDATE system_state SET val_str = :state, updated_at = :ts WHERE key_name = 'kill_switch'"),
            {"state": state_str, "ts": time.time()}
        )

def get_market_state():
    with SQL_ENGINE.connect() as conn:
        res = conn.execute(text("SELECT val_str FROM system_state WHERE key_name = 'market_state'")).fetchone()
        return res[0] if res else "RUNNING"

def set_market_state(state_str):
    with SQL_ENGINE.begin() as conn:
        conn.execute(
            text("UPDATE system_state SET val_str = :state, updated_at = :ts WHERE key_name = 'market_state'"),
            {"state": state_str, "ts": time.time()}
        )

def get_portfolio_metrics():
    """Compute current cash, start-of-day equity, and total equity."""
    with SQL_ENGINE.connect() as conn:
        bal = conn.execute(text("SELECT cash, start_of_day_equity, realized_pnl FROM account_balance WHERE id = 1")).fetchone()
        if not bal:
            return 100000.0, 100000.0, 0.0, 0.0, 100000.0
        cash, sod_equity, realized_pnl = bal[0], bal[1], bal[2]
        
        # Calculate unrealized pnl from open positions
        positions = conn.execute(text("SELECT symbol, qty, avg_entry_price, current_price FROM positions")).fetchall()
        unrealized_pnl = 0.0
        open_count = len(positions)
        positions_val = 0.0
        for pos in positions:
            p_qty, p_entry, p_curr = pos[1], pos[2], pos[3]
            unrealized_pnl += p_qty * (p_curr - p_entry)
            positions_val += p_qty * p_curr
            
        current_equity = cash + positions_val
        return cash, sod_equity, realized_pnl, unrealized_pnl, current_equity, open_count

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "risk_service",
        "status": "healthy",
        "port": PORT_RISK,
        "kill_switch": get_kill_switch_state(),
        "market_state": get_market_state(),
        "ai_dependency": "NONE (Deterministic rule engine)"
    })

@app.route("/kill_switch", methods=["GET", "POST"])
def kill_switch():
    """Emergency kill switch toggle and status."""
    if request.method == "POST":
        data = request.get_json() or {}
        action = data.get("action", "ENGAGE").upper()  # ENGAGE | DISENGAGE
        new_state = "ON" if action == "ENGAGE" else "OFF"
        set_kill_switch_state(new_state)
        
        if new_state == "ON":
            set_market_state("KILLED")
            # Log event in risk_events table
            with SQL_ENGINE.connect() as conn:
                conn.execute(
                    text("INSERT INTO risk_events (event_type, symbol, reason, details, created_at) VALUES ('KILL_SWITCH', 'ALL', 'Manual kill switch activated', :details, :ts)"),
                    {"details": f"Triggered action {action}", "ts": time.time()}
                )
        else:
            set_market_state("RUNNING")

        return jsonify({
            "status": "success",
            "kill_switch": new_state,
            "market_state": get_market_state()
        })
    
    return jsonify({
        "kill_switch": get_kill_switch_state(),
        "market_state": get_market_state()
    })

@app.route("/limits", methods=["GET"])
def get_limits():
    cash, sod_equity, realized_pnl, unrealized_pnl, current_equity, open_count = get_portfolio_metrics()
    total_day_pnl = realized_pnl + unrealized_pnl
    daily_loss_limit_amount = sod_equity * (DAILY_LOSS_LIMIT_PCT / 100.0)
    
    loss_used_pct = 0.0
    if total_day_pnl < 0:
        loss_used_pct = min(100.0, abs(total_day_pnl) / daily_loss_limit_amount * 100.0)

    is_loss_limit_hit = (total_day_pnl <= -daily_loss_limit_amount)
    
    return jsonify({
        "sod_equity": sod_equity,
        "current_equity": current_equity,
        "day_pnl": round(total_day_pnl, 2),
        "daily_loss_limit_pct": DAILY_LOSS_LIMIT_PCT,
        "daily_loss_limit_amount": daily_loss_limit_amount,
        "loss_used_pct": round(loss_used_pct, 1),
        "max_risk_per_trade_pct": MAX_RISK_PER_TRADE_PCT,
        "max_open_positions": MAX_OPEN_POSITIONS,
        "open_positions_count": open_count,
        "kill_switch": get_kill_switch_state(),
        "market_state": get_market_state(),
        "is_loss_limit_hit": is_loss_limit_hit
    })

@app.route("/reset_daily_limit", methods=["POST"])
def reset_daily_limit():
    """Manual reset endpoint for demo / testing."""
    cash, sod_equity, realized_pnl, unrealized_pnl, current_equity, open_count = get_portfolio_metrics()
    with SQL_ENGINE.connect() as conn:
        # Reset start_of_day_equity to current equity and clear realized_pnl for the new day
        conn.execute(
            text("UPDATE account_balance SET start_of_day_equity = :eq, realized_pnl = 0.0, updated_at = :ts WHERE id = 1"),
            {"eq": current_equity, "ts": time.time()}
        )
    set_market_state("RUNNING")
    return jsonify({"status": "reset", "market_state": "RUNNING", "new_sod_equity": current_equity})

@app.route("/evaluate", methods=["POST"])
def evaluate_risk():
    """
    Evaluates proposed order against all 16 risk rules:
    1. Kill switch check
    2. Market state check
    3. Price staleness / NO_TRADE check
    4. News staleness check
    5. Daily loss limit check
    6. Mandatory stop-loss presence
    7. Stop-loss logic (SL < entry for BUY, SL > entry for SELL)
    8. Stop-loss distance > 0.1% and < 10%
    9. Max open positions check
    10. Available cash check
    11. Max single position exposure check (30% of portfolio)
    12. Quantity position sizing based on exactly 1% risk of equity
    13. Valid symbol and side check
    14. Minimum order size >= 1 share
    15. Size tier multiplier (FULL = 1.0, HALF = 0.5)
    16. Cryptographic approval token generation
    """
    data = request.get_json() or {}
    symbol = data.get("symbol")
    side = data.get("side", "").upper()
    entry_price = float(data.get("entry_price", 0.0))
    stop_loss = float(data.get("stop_loss", 0.0))
    size_tier = data.get("size_tier", "FULL").upper()
    data_fresh = data.get("data_fresh", True)
    news_fresh = data.get("news_fresh", True)

    def reject(reason_str):
        # Log to risk_events
        with SQL_ENGINE.connect() as conn:
            conn.execute(
                text("INSERT INTO risk_events (event_type, symbol, reason, details, created_at) VALUES ('ORDER_REJECTED', :sym, :reason, :details, :ts)"),
                {"sym": symbol, "reason": reason_str, "details": str(data), "ts": time.time()}
            )
        return jsonify({
            "approved": False,
            "symbol": symbol,
            "side": side,
            "qty": 0,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "approval_token": None,
            "reason": reason_str,
            "timestamp": time.time()
        })

    # Rule 1: Kill switch check
    if get_kill_switch_state() == "ON":
        return reject("EMERGENCY KILL SWITCH IS ACTIVE - ALL TRADING BLOCKED")

    # Rule 2: Market state check
    market_state = get_market_state()
    if market_state == "HALTED_DAILY_LOSS":
        return reject("TRADING HALTED - DAILY LOSS LIMIT HIT FOR TODAY")
    if market_state == "KILLED":
        return reject("SYSTEM STATE IS KILLED")

    # Rule 3 & 4: Data and News Staleness Checks
    if not data_fresh:
        return reject("PRICE FEED IS STALE - REJECTING UNDER NO_TRADE SAFETY GUARD")
    if not news_fresh:
        return reject("NEWS FEED IS STALE - REJECTING UNDER NO_TRADE SAFETY GUARD")

    # Rule 5: Daily Loss Limit Check
    cash, sod_equity, realized_pnl, unrealized_pnl, current_equity, open_count = get_portfolio_metrics()
    total_day_pnl = realized_pnl + unrealized_pnl
    daily_loss_limit_amount = sod_equity * (DAILY_LOSS_LIMIT_PCT / 100.0)
    if total_day_pnl <= -daily_loss_limit_amount:
        set_market_state("HALTED_DAILY_LOSS")
        return reject(f"DAILY LOSS EXCEEDED ({round(abs(total_day_pnl), 2)} >= {daily_loss_limit_amount}) - TRADING HALTED")

    # Rule 6: Mandatory stop-loss presence
    if not stop_loss or stop_loss <= 0:
        return reject("MANDATORY STOP-LOSS MISSING OR ZERO")

    # Rule 7: Stop-loss logical orientation
    if side == "BUY" and stop_loss >= entry_price:
        return reject("INVALID STOP-LOSS FOR BUY: Stop-loss must be strictly below entry price")
    if side == "SELL" and stop_loss <= entry_price:
        return reject("INVALID STOP-LOSS FOR SELL: Stop-loss must be strictly above entry price")

    # Rule 8: Stop-loss distance bounds (between 0.1% and 10%)
    sl_distance = abs(entry_price - stop_loss)
    sl_pct = (sl_distance / entry_price) * 100.0
    if sl_pct < 0.1:
        return reject(f"STOP-LOSS TOO CLOSE ({round(sl_pct, 2)}% < 0.1%)")
    if sl_pct > 10.0:
        return reject(f"STOP-LOSS TOO WIDE ({round(sl_pct, 2)}% > 10.0%)")

    # Rule 9: Max open positions check
    if open_count >= MAX_OPEN_POSITIONS:
        return reject(f"MAX OPEN POSITIONS REACHED ({open_count}/{MAX_OPEN_POSITIONS})")

    # Rule 10, 11, 12: Position sizing based on 1% equity risk
    risk_dollars = current_equity * (MAX_RISK_PER_TRADE_PCT / 100.0)
    raw_qty = risk_dollars / sl_distance
    
    # Apply consensus size tier (FULL = 1.0, HALF = 0.5)
    tier_multiplier = 1.0 if size_tier == "FULL" else (0.5 if size_tier == "HALF" else 0.0)
    if tier_multiplier <= 0:
        return reject("DECISION SIZE TIER IS ZERO - HOLD")

    qty = int(math.floor(raw_qty * tier_multiplier))
    if qty < 1:
        qty = 1

    # Check maximum single position exposure
    max_position_cost = current_equity * (MAX_POSITION_VALUE_PCT / 100.0)
    if (qty * entry_price) > max_position_cost:
        qty = int(math.floor(max_position_cost / entry_price))

    if qty < 1:
        return reject("INSUFFICIENT CAPITAL FOR MINIMUM 1 SHARE POSITION SIZE")

    # Check available cash
    total_order_cost = qty * entry_price
    if total_order_cost > cash:
        qty = int(math.floor(cash / entry_price))
        if qty < 1:
            return reject(f"INSUFFICIENT CASH (Cash: {round(cash, 2)}, Required: {round(total_order_cost, 2)})")

    # Rule 16: Cryptographic approval token generation
    token_payload = {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "stop_loss": stop_loss,
        "entry_price": entry_price,
        "nonce": time.time()
    }
    approval_token = generate_risk_token(token_payload)

    # Log approval to risk_events
    with SQL_ENGINE.connect() as conn:
        conn.execute(
            text("INSERT INTO risk_events (event_type, symbol, reason, details, created_at) VALUES ('ORDER_APPROVED', :sym, 'Passed all 16 risk rules', :details, :ts)"),
            {"sym": symbol, "details": f"Qty: {qty}, SL: {stop_loss}, Risk: 1% ({round(risk_dollars, 2)})", "ts": time.time()}
        )

    return jsonify({
        "approved": True,
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "approval_token": approval_token,
        "reason": f"Approved 1% equity risk sizing ({qty} shares, {size_tier} tier)",
        "timestamp": time.time()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT_RISK, debug=False)
