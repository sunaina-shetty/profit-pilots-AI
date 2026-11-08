import os
import sys
import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from simulation.config import POPULAR_NSE_STOCKS
from simulation.engine import engine

app = Flask(__name__)
CORS(app)

@app.route("/api/stocks", methods=["GET"])
def get_stocks():
    return jsonify({"stocks": POPULAR_NSE_STOCKS})

@app.route("/api/start", methods=["POST"])
def start_simulation():
    data = request.get_json() or {}
    symbol = data.get("symbol", "TCS").strip().upper()
    
    # Input validation: amount between ₹10,000 and ₹10,00,00,000 (10 crore)
    try:
        amount = float(data.get("amount", 100000.0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid amount: must be a valid number"}), 400

    if amount < 10000.0 or amount > 100000000.0:
        return jsonify({"error": "Amount must be between ₹10,000 and ₹10,00,00,000 (10 Crore)"}), 400

    # Input validation: stop loss % between 0.3% and 5.0%
    try:
        stop_loss_pct = float(data.get("stop_loss_pct", 1.0))
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid stop-loss percentage: must be a number"}), 400

    if stop_loss_pct < 0.3 or stop_loss_pct > 5.0:
        return jsonify({"error": "Stop-loss percentage must be between 0.3% and 5.0%"}), 400

    # Optional date validation (cannot be in the future or on weekend)
    target_date = data.get("date")
    if target_date:
        try:
            dt = datetime.datetime.strptime(target_date, "%Y-%m-%d").date()
            if dt > datetime.date.today():
                return jsonify({"error": "Date cannot be in the future"}), 400
            if dt.weekday() >= 5: # Saturday = 5, Sunday = 6
                return jsonify({"error": "NSE is closed on weekends; select a weekday"}), 400
        except ValueError:
            return jsonify({"error": "Invalid date format. Expected YYYY-MM-DD"}), 400

    try:
        engine.start_simulation(
            symbol=symbol,
            amount=amount,
            stop_loss_pct=stop_loss_pct,
            target_date_str=target_date
        )
        return jsonify({"status": "started", "state": engine.get_state()})
    except Exception as e:
        return jsonify({"error": f"Failed to start simulation: {str(e)}"}), 500

@app.route("/api/state", methods=["GET"])
def get_state():
    return jsonify(engine.get_state())

@app.route("/api/kill", methods=["POST"])
def kill_simulation():
    try:
        engine.kill_simulation()
        return jsonify({"status": "killed", "state": engine.get_state()})
    except Exception as e:
        return jsonify({"error": f"Failed to kill simulation: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting ProfitPilot AI Paper-Trading Simulator on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)

