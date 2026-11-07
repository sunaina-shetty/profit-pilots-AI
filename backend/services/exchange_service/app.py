import os
import sys
import time
import uuid
from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy import text

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from backend.shared.config import (
    PORT_EXCHANGE, MAKER_FEE_PCT, SLIPPAGE_BPS, STARTING_CASH
)
from backend.shared.db import SQL_ENGINE, init_sql_tables
from backend.shared.token_utils import verify_risk_token

app = Flask(__name__)
CORS(app)

init_sql_tables()

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "exchange_service",
        "status": "healthy",
        "port": PORT_EXCHANGE,
        "timestamp": time.time()
    })

@app.route("/portfolio", methods=["GET"])
def get_portfolio():
    with SQL_ENGINE.connect() as conn:
        bal = conn.execute(text("SELECT cash, start_of_day_equity, realized_pnl, unrealized_pnl FROM account_balance WHERE id = 1")).fetchone()
        if not bal:
            return jsonify({"error": "No balance record"}), 500
        cash, sod_equity, realized_pnl, _ = bal[0], bal[1], bal[2], bal[3]
        
        positions = conn.execute(text("SELECT symbol, qty, avg_entry_price, current_price, unrealized_pnl, stop_loss, take_profit FROM positions")).fetchall()
        pos_list = []
        tot_unrealized = 0.0
        tot_pos_val = 0.0
        for p in positions:
            p_val = p[1] * p[3]
            tot_pos_val += p_val
            tot_unrealized += p[4]
            pos_list.append({
                "symbol": p[0],
                "qty": p[1],
                "avg_entry_price": round(p[2], 2),
                "current_price": round(p[3], 2),
                "unrealized_pnl": round(p[4], 2),
                "stop_loss": round(p[5], 2),
                "take_profit": round(p[6], 2) if p[6] else None,
                "market_value": round(p_val, 2)
            })
            
        equity = cash + tot_pos_val
        day_pnl = realized_pnl + tot_unrealized
        
        return jsonify({
            "cash": round(cash, 2),
            "start_of_day_equity": round(sod_equity, 2),
            "equity": round(equity, 2),
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(tot_unrealized, 2),
            "day_pnl": round(day_pnl, 2),
            "positions": pos_list
        })

@app.route("/order", methods=["POST"])
def place_order():
    """Places virtual order strictly guarded by signed approval token."""
    data = request.get_json() or {}
    symbol = data.get("symbol")
    side = data.get("side", "").upper()
    qty = int(data.get("qty", 0))
    entry_price = float(data.get("entry_price", 0.0))
    stop_loss = float(data.get("stop_loss", 0.0))
    take_profit = float(data.get("take_profit", 0.0)) if data.get("take_profit") else None
    token = data.get("approval_token")

    if not token:
        return jsonify({"error": "REJECTED_BY_EXCHANGE: Missing signed risk approval token"}), 403

    # Cryptographic verification against order payload
    expected = {"symbol": symbol, "side": side, "qty": qty}
    is_valid, msg = verify_risk_token(token, expected)
    if not is_valid:
        return jsonify({"error": f"REJECTED_BY_EXCHANGE: {msg}"}), 403

    # Calculate realistic execution slippage and broker fees
    # Slippage: adds for BUY, subtracts for SELL
    slippage_fraction = (SLIPPAGE_BPS / 10000.0)
    if side == "BUY":
        fill_price = round(entry_price * (1.0 + slippage_fraction), 2)
    else:
        fill_price = round(entry_price * (1.0 - slippage_fraction), 2)
    
    order_val = fill_price * qty
    fees = round(order_val * (MAKER_FEE_PCT / 100.0), 2)

    order_id = f"ord_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}"

    with SQL_ENGINE.connect() as conn:
        trans = conn.begin()
        try:
            # Check balance
            bal = conn.execute(text("SELECT cash FROM account_balance WHERE id = 1")).fetchone()
            current_cash = bal[0]
            
            if side == "BUY":
                total_deduction = order_val + fees
                if current_cash < total_deduction:
                    trans.rollback()
                    return jsonify({"error": "Insufficient funds at execution time"}), 400
                
                # Update cash
                conn.execute(
                    text("UPDATE account_balance SET cash = cash - :cost, updated_at = :ts WHERE id = 1"),
                    {"cost": total_deduction, "ts": time.time()}
                )
                
                # Insert or update position
                existing = conn.execute(text("SELECT qty, avg_entry_price FROM positions WHERE symbol = :sym"), {"sym": symbol}).fetchone()
                if existing:
                    old_qty, old_entry = existing[0], existing[1]
                    new_qty = old_qty + qty
                    new_entry = ((old_qty * old_entry) + (qty * fill_price)) / new_qty
                    conn.execute(
                        text("UPDATE positions SET qty = :q, avg_entry_price = :e, current_price = :cp, stop_loss = :sl, take_profit = :tp, updated_at = :ts WHERE symbol = :sym"),
                        {"q": new_qty, "e": new_entry, "cp": fill_price, "sl": stop_loss, "tp": take_profit, "ts": time.time(), "sym": symbol}
                    )
                else:
                    conn.execute(
                        text("INSERT INTO positions (symbol, qty, avg_entry_price, current_price, unrealized_pnl, stop_loss, take_profit, updated_at) VALUES (:sym, :q, :e, :cp, 0.0, :sl, :tp, :ts)"),
                        {"sym": symbol, "q": qty, "e": fill_price, "cp": fill_price, "sl": stop_loss, "tp": take_profit, "ts": time.time()}
                    )
            
            elif side == "SELL":
                # Sell/Flatten position
                existing = conn.execute(text("SELECT qty, avg_entry_price FROM positions WHERE symbol = :sym"), {"sym": symbol}).fetchone()
                if not existing or existing[0] < qty:
                    trans.rollback()
                    return jsonify({"error": "Cannot sell shares not owned"}), 400
                
                old_qty, old_entry = existing[0], existing[1]
                pnl = (fill_price - old_entry) * qty - fees
                net_proceeds = (fill_price * qty) - fees
                
                # Update cash & realized PnL
                conn.execute(
                    text("UPDATE account_balance SET cash = cash + :proceeds, realized_pnl = realized_pnl + :pnl, updated_at = :ts WHERE id = 1"),
                    {"proceeds": net_proceeds, "pnl": pnl, "ts": time.time()}
                )
                
                rem_qty = old_qty - qty
                if rem_qty <= 0:
                    conn.execute(text("DELETE FROM positions WHERE symbol = :sym"), {"sym": symbol})
                else:
                    conn.execute(
                        text("UPDATE positions SET qty = :q, updated_at = :ts WHERE symbol = :sym"),
                        {"q": rem_qty, "ts": time.time(), "sym": symbol}
                    )

            # Record order
            conn.execute(
                text("""
                    INSERT INTO orders (order_id, symbol, side, qty, price, stop_loss, take_profit, status, fees, slippage, approval_token, created_at)
                    VALUES (:oid, :sym, :side, :qty, :p, :sl, :tp, 'FILLED', :fees, :slip, :tok, :ts)
                """),
                {
                    "oid": order_id, "sym": symbol, "side": side, "qty": qty, "p": fill_price,
                    "sl": stop_loss, "tp": take_profit, "fees": fees, "slip": abs(fill_price - entry_price),
                    "tok": token, "ts": time.time()
                }
            )

            trans.commit()
        except Exception as e:
            trans.rollback()
            return jsonify({"error": f"Execution error: {str(e)}"}), 500

    return jsonify({
        "order_id": order_id,
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "fill_price": fill_price,
        "fees": fees,
        "slippage": round(abs(fill_price - entry_price), 2),
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "status": "FILLED",
        "timestamp": time.time()
    })

@app.route("/tick", methods=["POST"])
def on_price_tick():
    """Evaluates stop-loss and take-profit on open positions."""
    data = request.get_json() or {}
    symbol = data.get("symbol")
    current_price = float(data.get("price", 0.0))

    triggered_exits = []

    with SQL_ENGINE.connect() as conn:
        pos = conn.execute(
            text("SELECT qty, avg_entry_price, stop_loss, take_profit FROM positions WHERE symbol = :sym"),
            {"sym": symbol}
        ).fetchone()

        if pos:
            qty, avg_entry, stop_loss, take_profit = pos[0], pos[1], pos[2], pos[3]
            unrealized = qty * (current_price - avg_entry)
            
            # Check stop loss hit
            if current_price <= stop_loss:
                # Trigger emergency stop-loss exit
                pnl = (stop_loss - avg_entry) * qty
                proceeds = (stop_loss * qty)
                conn.execute(
                    text("UPDATE account_balance SET cash = cash + :p, realized_pnl = realized_pnl + :pnl, updated_at = :ts WHERE id = 1"),
                    {"p": proceeds, "pnl": pnl, "ts": time.time()}
                )
                conn.execute(text("DELETE FROM positions WHERE symbol = :sym"), {"sym": symbol})
                triggered_exits.append({"symbol": symbol, "type": "STOP_LOSS_HIT", "price": stop_loss, "pnl": round(pnl, 2)})
            
            # Check take profit hit
            elif take_profit and current_price >= take_profit:
                pnl = (take_profit - avg_entry) * qty
                proceeds = (take_profit * qty)
                conn.execute(
                    text("UPDATE account_balance SET cash = cash + :p, realized_pnl = realized_pnl + :pnl, updated_at = :ts WHERE id = 1"),
                    {"p": proceeds, "pnl": pnl, "ts": time.time()}
                )
                conn.execute(text("DELETE FROM positions WHERE symbol = :sym"), {"sym": symbol})
                triggered_exits.append({"symbol": symbol, "type": "TAKE_PROFIT_HIT", "price": take_profit, "pnl": round(pnl, 2)})
            
            else:
                # Update current price & mark-to-market
                conn.execute(
                    text("UPDATE positions SET current_price = :cp, unrealized_pnl = :up, updated_at = :ts WHERE symbol = :sym"),
                    {"cp": current_price, "up": unrealized, "ts": time.time(), "sym": symbol}
                )

    return jsonify({"symbol": symbol, "triggered_exits": triggered_exits})

@app.route("/close_all", methods=["POST"])
def close_all_positions():
    """Flattens all positions immediately (used when KILL SWITCH is engaged)."""
    closed = []
    with SQL_ENGINE.connect() as conn:
        trans = conn.begin()
        try:
            positions = conn.execute(text("SELECT symbol, qty, avg_entry_price, current_price FROM positions")).fetchall()
            for p in positions:
                sym, q, entry, curr = p[0], p[1], p[2], p[3]
                pnl = (curr - entry) * q
                proceeds = curr * q
                conn.execute(
                    text("UPDATE account_balance SET cash = cash + :p, realized_pnl = realized_pnl + :pnl, updated_at = :ts WHERE id = 1"),
                    {"p": proceeds, "pnl": pnl, "ts": time.time()}
                )
                closed.append({"symbol": sym, "qty": q, "exit_price": curr, "realized_pnl": round(pnl, 2)})
            
            conn.execute(text("DELETE FROM positions"))
            trans.commit()
        except Exception as e:
            trans.rollback()
            return jsonify({"error": str(e)}), 500

    return jsonify({"status": "flattened", "closed_positions": closed})

@app.route("/reset", methods=["POST"])
def reset_portfolio():
    """Resets database account balance & positions to initial starting capital."""
    with SQL_ENGINE.connect() as conn:
        trans = conn.begin()
        conn.execute(text("DELETE FROM positions"))
        conn.execute(text("DELETE FROM orders"))
        conn.execute(
            text("UPDATE account_balance SET cash = :c, start_of_day_equity = :c, realized_pnl = 0.0, unrealized_pnl = 0.0, updated_at = :ts WHERE id = 1"),
            {"c": STARTING_CASH, "ts": time.time()}
        )
        conn.execute(text("UPDATE system_state SET val_str = 'RUNNING', updated_at = :ts WHERE key_name = 'market_state'"), {"ts": time.time()})
        conn.execute(text("UPDATE system_state SET val_str = 'OFF', updated_at = :ts WHERE key_name = 'kill_switch'"), {"ts": time.time()})
        trans.commit()
    return jsonify({"status": "reset", "cash": STARTING_CASH})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT_EXCHANGE, debug=False)
