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
from simulation.market_data import fetch_5min_candles, fetch_daily_ohlc, fetch_candles_by_timeframe, normalize_timeframe
from simulation.strategies.registry import list_all_strategies
from simulation.agent_config import agent_config_manager
from simulation.backtest import run_strategy_backtest
from simulation.indicators import enrich_candles_with_all_indicators
from simulation.live_market import live_market_manager

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
    Returns candles with indicators for the requested timeframe (5m, 15m, 1h, 1d, 1w, 1mo).
    """
    symbol = request.args.get("symbol", "TCS").strip().upper()
    target_date = request.args.get("date", "").strip() or None
    timeframe = request.args.get("timeframe", "5m").strip().lower()

    yf_symbol = symbol if "." in symbol else f"{symbol}.NS"
    resolved_date = target_date or datetime.date.today().strftime("%Y-%m-%d")
    norm_tf = normalize_timeframe(timeframe)

    if norm_tf != "5m":
        try:
            candles, is_real, data_banner = fetch_candles_by_timeframe(yf_symbol, norm_tf, resolved_date)
            candles = enrich_candles_with_all_indicators(candles)
            return jsonify({
                "status": "success",
                "symbol": yf_symbol,
                "date": resolved_date,
                "timeframe": norm_tf,
                "is_real_data": is_real,
                "data_banner": data_banner,
                "candle_count": len(candles),
                "first_candle_time": candles[0]["time_str"] if candles else None,
                "last_candle_time": candles[-1]["time_str"] if candles else None,
                "first_timestamp": candles[0]["time"] if candles else None,
                "last_timestamp": candles[-1]["time"] if candles else None,
                "candles": candles
            })
        except Exception as e:
            return jsonify({"error": f"Failed to load {norm_tf} candles: {str(e)}"}), 500

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

        enriched_candles = enrich_candles_with_all_indicators(enriched_candles)

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
        speed = str(data.get("speed", "20x"))
        engine.start_simulation(
            symbol=symbol,
            amount=amount,
            stop_loss_pct=stop_loss_pct,
            target_date_str=target_date,
            speed=speed
        )
        return jsonify({"status": "started", "state": engine.get_state()})
    except Exception as e:
        return jsonify({"error": f"Failed to start simulation: {str(e)}"}), 500

@app.route("/api/speed", methods=["POST"])
def update_simulation_speed():
    """Dynamically updates simulation speed (e.g. 1x, 5x, 10x, 20x, 50x, 100x, MAX)."""
    data = request.get_json(silent=True) or {}
    speed = data.get("speed", "20x")
    sleep_sec = engine.set_speed(speed)
    return jsonify({
        "status": "success",
        "speed": engine.speed,
        "speed_sleep": sleep_sec,
        "state": engine.get_state()
    })

@app.route("/api/state", methods=["GET"])
def get_state():
    return jsonify(engine.get_state())

@app.route("/api/live/state", methods=["GET"])
def get_live_state():
    return jsonify(live_market_manager.get_state())

@app.route("/api/live/start", methods=["POST"])
def start_live_market():
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol")
    if symbol:
        live_market_manager.set_symbol(symbol)
    live_market_manager.start()
    return jsonify({"status": "started", "state": live_market_manager.get_state()})

@app.route("/api/live/stop", methods=["POST"])
def stop_live_market():
    live_market_manager.stop()
    return jsonify({"status": "stopped", "state": live_market_manager.get_state()})

@app.route("/api/live/switch", methods=["POST"])
def switch_live_symbol():
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol", "HDFCBANK")
    live_market_manager.set_symbol(symbol)
    return jsonify({"status": "switched", "symbol": live_market_manager.symbol, "state": live_market_manager.get_state()})

@app.route("/api/live/order", methods=["POST"])
def execute_live_order():
    data = request.get_json(silent=True) or {}
    side = data.get("side", "BUY").upper()
    qty = int(data.get("qty", 1))
    res = live_market_manager.execute_live_order(side=side, qty=qty)
    return jsonify({"result": res, "state": live_market_manager.get_state()})

@app.route("/api/live/bot/start", methods=["POST"])
def start_live_bot():
    """Starts the multi-agent council automated trading bot in the live market."""
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol")
    amount = float(data.get("amount", 100000.0))
    stop_loss_pct = float(data.get("stop_loss_pct", 1.0))
    if symbol:
        live_market_manager.set_symbol(symbol)
    res = live_market_manager.start_trade_bot(amount=amount, stop_loss_pct=stop_loss_pct)
    return jsonify(res)

@app.route("/api/live/bot/stop", methods=["POST"])
def stop_live_bot():
    """Stops the live trade bot and flattens or pauses new entries."""
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "flatten")
    res = live_market_manager.stop_trade_bot(mode=mode)
    return jsonify(res)

@app.route("/api/live/stream", methods=["GET"])
def stream_live_state():
    """SSE real-time stream of live market state."""
    def event_stream():
        while True:
            try:
                state = live_market_manager.get_state()
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

@app.route("/api/stream", methods=["GET"])
def stream_state():
    """Server-Sent Events (SSE) real-time stream of simulation or live market state."""
    mode = request.args.get("mode", "").strip().lower()
    def event_stream():
        while True:
            try:
                if mode == "live" or (live_market_manager.is_running and not engine.is_running):
                    state = live_market_manager.get_state()
                else:
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

@app.route("/api/strategies", methods=["GET"])
def get_strategies():
    """Returns catalog of all 10 technical trading strategies."""
    return jsonify({"strategies": list_all_strategies()})

@app.route("/api/agent-config", methods=["GET"])
def get_agent_config():
    """Returns current persisted agent and strategy configuration."""
    return jsonify(agent_config_manager.get_config())

@app.route("/api/agent-config", methods=["POST"])
def update_agent_config():
    """Updates agent and strategy configuration."""
    patch = request.get_json() or {}
    updated = agent_config_manager.update_config(patch)
    try:
        live_state = live_market_manager.recalculate_strategies()
    except Exception:
        live_state = live_market_manager.get_state()
    return jsonify({
        "status": "updated",
        "config": updated,
        "live_state": live_state
    })

@app.route("/api/agent-config/reset", methods=["POST"])
def reset_agent_config():
    """Resets configuration to factory defaults."""
    resetted = agent_config_manager.reset_defaults()
    try:
        live_state = live_market_manager.recalculate_strategies()
    except Exception:
        live_state = live_market_manager.get_state()
    return jsonify({
        "status": "reset",
        "config": resetted,
        "live_state": live_state
    })

@app.route("/api/news-config", methods=["GET", "POST"])
def news_config_endpoint():
    """Gets or sets the news agent mode (Moneycontrol vs Previous RSS logic)."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        use_mc = bool(data.get("use_moneycontrol", True))
        updated = agent_config_manager.update_config({"agent2": {"use_moneycontrol": use_mc}})
        return jsonify({"status": "updated", "use_moneycontrol": use_mc, "config": updated})
    cfg = agent_config_manager.get_config().get("agent2", {})
    return jsonify({"use_moneycontrol": cfg.get("use_moneycontrol", True)})

@app.route("/api/market-indices", methods=["GET"])
def get_market_indices():
    """Returns live or realistic top indices for the Groww-inspired top market bar."""
    indices = [
        {"name": "NIFTY 50", "value": 24997.30, "change": 10.90, "change_pct": 0.04, "is_up": True},
        {"name": "SENSEX", "value": 81059.38, "change": 59.98, "change_pct": 0.07, "is_up": True},
        {"name": "BANK NIFTY", "value": 59490.60, "change": 639.95, "change_pct": 1.09, "is_up": True},
        {"name": "Crude Oil", "value": 8446.00, "change": -108.00, "change_pct": -1.26, "is_up": False, "currency": "₹"},
        {"name": "Natural Gas", "value": 286.40, "change": 1.40, "change_pct": 0.49, "is_up": True, "currency": "₹"},
    ]
    return jsonify({"indices": indices})

@app.route("/api/stock-quote", methods=["GET"])
def get_stock_quote():
    """Returns detailed market metrics for the selected stock for the Groww top market bar."""
    symbol = request.args.get("symbol", "TCS").strip().upper()
    yf_symbol = symbol if "." in symbol else f"{symbol}.NS"
    try:
        ohlc, source, _ = fetch_daily_ohlc(yf_symbol)
        curr = ohlc.get("close", 0.0)
        prev = ohlc.get("prev_close", curr)
        diff = round(curr - prev, 2)
        diff_pct = round((diff / prev) * 100.0, 2) if prev > 0 else 0.0
        
        # Match stock name from catalog
        name = symbol
        for s in POPULAR_NSE_STOCKS:
            if s["symbol"].replace(".NS", "") == symbol or s["symbol"] == symbol:
                name = s.get("name", symbol)
                break

        return jsonify({
            "symbol": symbol,
            "name": name,
            "current_price": curr,
            "change": diff,
            "change_pct": diff_pct,
            "day_high": ohlc.get("high", curr),
            "day_low": ohlc.get("low", curr),
            "prev_close": prev,
            "volume": int(ohlc.get("volume", 0)),
            "data_source": source,
            "is_available": curr > 0
        })
    except Exception as e:
        return jsonify({
            "symbol": symbol,
            "name": symbol,
            "is_available": False,
            "error": str(e)
        }), 200

@app.route("/api/backtest", methods=["POST"])
def backtest_strategy():
    """Executes multi-day chronological strategy backtest with fee modeling and no lookahead bias."""
    data = request.get_json() or {}
    symbol = data.get("symbol", "TCS").strip().upper()
    strategy_id = data.get("strategy_id", "strat_orb")
    days = int(data.get("days", 5))
    initial_capital = float(data.get("initial_capital", 100000.0))
    risk_per_trade_pct = float(data.get("risk_per_trade_pct", 0.5))
    stop_loss_pct = float(data.get("stop_loss_pct", 1.0))
    target_rr = float(data.get("target_rr", 1.5))
    params = data.get("params")

    try:
        results = run_strategy_backtest(
            symbol=symbol,
            strategy_id=strategy_id,
            strategy_params=params,
            days=days,
            initial_capital=initial_capital,
            risk_per_trade_pct=risk_per_trade_pct,
            stop_loss_pct=stop_loss_pct,
            target_rr=target_rr
        )
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": f"Backtest execution failed: {str(e)}"}), 500

@app.route("/api/kill", methods=["POST"])
def kill_simulation():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "flatten")
    try:
        engine.kill_simulation(mode=mode)
        return jsonify({"status": "killed", "mode": mode, "state": engine.get_state()})
    except Exception as e:
        return jsonify({"error": f"Failed to kill simulation: {str(e)}"}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Starting ProfitPilot AI Paper-Trading Simulator on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)

