import os
import sys
import datetime
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import json
import time

# Add workspace root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from simulation.config import POPULAR_NSE_STOCKS
from simulation.engine import engine
from simulation.market_data import fetch_5min_candles

app = Flask(__name__, static_folder="frontend/dist", static_url_path="")
CORS(app)

@app.route("/", methods=["GET"])
def index():
    if app.static_folder and os.path.exists(os.path.join(app.static_folder, "index.html")):
        return app.send_static_file("index.html")
    return jsonify({"message": "ProfitPilot AI API running. Start frontend on :5173 or run npm run build in frontend/."})

@app.route("/api/stocks", methods=["GET"])
def get_stocks():
    return jsonify({"stocks": POPULAR_NSE_STOCKS})

@app.route("/api/candles", methods=["GET"])
def get_candles():
    """
    Returns full 5-minute candles with indicators (VWAP, ORB High/Low, Volume)
    for previewing the trading session before START is clicked.
    """
    symbol = request.args.get("symbol", "TCS").strip().upper()
    target_date = request.args.get("date", "").strip() or None

    yf_symbol = symbol if "." in symbol else f"{symbol}.NS"
    resolved_date = target_date or datetime.date.today().strftime("%Y-%m-%d")

    try:
        candles_5m, warmup_5m, is_real, data_banner, avg_opening_vol = fetch_5min_candles(
            yf_symbol, resolved_date
        )
        if not candles_5m:
            return jsonify({"error": f"No candles available for {symbol} on {resolved_date}"}), 404

        orb_h = float(candles_5m[0]["high"]) if candles_5m else 0.0
        orb_l = float(candles_5m[0]["low"]) if candles_5m else 0.0

        cum_vp = 0.0
        cum_vol = 0.0
        enriched_candles = []
        ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))

        for i, c in enumerate(candles_5m):
            v = int(c.get("volume", 0))
            typ_p = (float(c["high"]) + float(c["low"]) + float(c["close"])) / 3.0
            cum_vp += typ_p * v
            cum_vol += v
            vwap = round(cum_vp / max(1.0, cum_vol), 2)

            ts = c.get("timestamp")
            time_label = c.get("time_str") or (c.get("time") if isinstance(c.get("time"), str) else "09:15")
            if not isinstance(ts, int):
                try:
                    dt = datetime.datetime.strptime(f"{resolved_date} {time_label}", "%Y-%m-%d %H:%M").replace(tzinfo=ist_tz)
                    ts = int(dt.timestamp())
                except Exception:
                    ts = 1700000000 + i * 300

            enriched_candles.append({
                "time": ts,
                "timestamp": ts,
                "time_str": time_label,
                "open": round(float(c["open"]), 2),
                "high": round(float(c["high"]), 2),
                "low": round(float(c["low"]), 2),
                "close": round(float(c["close"]), 2),
                "volume": v,
                "vwap": vwap,
                "orb_high": round(orb_h, 2),
                "orb_low": round(orb_l, 2)
            })

        return jsonify({
            "status": "success",
            "symbol": yf_symbol,
            "date": resolved_date,
            "is_real_data": is_real,
            "data_banner": data_banner,
            "candle_count": len(enriched_candles),
            "first_candle_time": enriched_candles[0]["time_str"] if enriched_candles else None,
            "last_candle_time": enriched_candles[-1]["time_str"] if enriched_candles else None,
            "first_timestamp": enriched_candles[0]["time"] if enriched_candles else None,
            "last_timestamp": enriched_candles[-1]["time"] if enriched_candles else None,
            "orb_high": round(orb_h, 2),
            "orb_low": round(orb_l, 2),
            "candles": enriched_candles
        })
    except Exception as e:
        return jsonify({"error": f"Failed to load candles: {str(e)}"}), 500

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

@app.route("/api/stream", methods=["GET"])
def stream_state():
    """Server-Sent Events (SSE) real-time stream of simulation state."""
    def event_stream():
        while True:
            try:
                state = engine.get_state()
                yield f"data: {json.dumps(state)}\n\n"
            except Exception:
                pass
            time.sleep(0.5)
    return Response(
        event_stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )

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

