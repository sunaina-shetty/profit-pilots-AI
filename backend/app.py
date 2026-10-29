"""ProfitPilot AI demo API (Flask). Paper trading only, virtual money."""
import os
import threading

from flask import Flask, jsonify, request
from flask_cors import CORS

from engine.chaos import SCENARIOS
from engine.core import Engine, run_backtest

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "prices.csv")

app = Flask(__name__)
CORS(app)
lock = threading.Lock()
engine = Engine(CSV_PATH)
backtest_cache = None


@app.get("/api/health")
def health():
    return jsonify({"ok": True})


@app.get("/api/state")
def state():
    with lock:
        return jsonify(engine.state())


@app.post("/api/tick")
def tick():
    steps = max(1, min(int((request.get_json(silent=True) or {}).get("steps", 1)), 50))
    with lock:
        for _ in range(steps):
            if not engine.tick():
                break
        return jsonify(engine.state())


@app.post("/api/reset")
def reset():
    global engine
    with lock:
        engine = Engine(CSV_PATH)
        return jsonify(engine.state())


@app.post("/api/kill-switch")
def kill_switch():
    engaged = bool((request.get_json(silent=True) or {}).get("engaged", True))
    with lock:
        engine.set_kill_switch(engaged)
        return jsonify(engine.state())


@app.post("/api/chaos")
def chaos():
    name = (request.get_json(silent=True) or {}).get("scenario")
    if name not in SCENARIOS:
        return jsonify({"error": f"Unknown scenario '{name}'. Use one of: {', '.join(SCENARIOS)}"}), 400
    with lock:
        engine.inject_chaos(name)
        return jsonify(engine.state())


@app.get("/api/backtest")
def backtest():
    global backtest_cache
    if backtest_cache is None:
        backtest_cache = run_backtest(CSV_PATH)
    return jsonify(backtest_cache)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
