import os
import sys
import time
import random
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from backend.shared.config import (
    PORT_DATA, DATA_MODE, DEFAULT_SYMBOL, PRICE_STALENESS_SECONDS, NEWS_STALENESS_SECONDS
)

app = Flask(__name__)
CORS(app)

# In-memory simulator state
current_mode = DATA_MODE
simulated_prices = {
    "RELIANCE.NS": 2870.50,
    "TCS.NS": 4120.00,
    "INFY.NS": 1840.25,
    "AAPL": 225.50,
    "MSFT": 420.75,
    "TSLA": 250.00
}
last_tick_times = {}
injected_delays = {}
injected_shocks = {}

# Simulated news pool
MOCK_HEADLINES = [
    {"headline": "Company reports record Q3 quarterly profits, margins expand 180 bps", "source": "Bloomberg", "credibility": 0.95, "bias": 0.8},
    {"headline": "Board approves substantial share buyback at 15% premium to market", "source": "Reuters", "credibility": 0.90, "bias": 0.75},
    {"headline": "Strategic partnership signed for enterprise AI cloud expansion", "source": "CNBC", "credibility": 0.85, "bias": 0.6},
    {"headline": "Management reiterates solid annual guidance amidst steady client demand", "source": "Mint", "credibility": 0.80, "bias": 0.4},
    {"headline": "Sector regulatory scrutiny raises compliance review concerns", "source": "Economic Times", "credibility": 0.75, "bias": -0.5},
    {"headline": "Supply chain bottlenecks may impact delivery timelines this quarter", "source": "Financial Express", "credibility": 0.70, "bias": -0.65},
    {"headline": "Unverified rumor on social media suggests potential executive departures", "source": "ForumBuzz", "credibility": 0.30, "bias": -0.85},
    {"headline": "Analysts maintain neutral rating citing current fair valuation levels", "source": "Kotak Research", "credibility": 0.85, "bias": 0.05}
]

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "data_service",
        "status": "healthy",
        "mode": current_mode,
        "port": PORT_DATA,
        "timestamp": time.time()
    })

@app.route("/mode", methods=["GET", "POST"])
def manage_mode():
    global current_mode
    if request.method == "POST":
        data = request.get_json() or {}
        new_mode = data.get("mode", "SIMULATED").upper()
        if new_mode in ["SIMULATED", "REAL"]:
            current_mode = new_mode
            return jsonify({"status": "updated", "mode": current_mode})
        return jsonify({"error": "Invalid mode. Choose SIMULATED or REAL"}), 400
    return jsonify({"mode": current_mode})

@app.route("/inject_shock", methods=["POST"])
def inject_shock():
    """Chaos endpoint: inject price drop, spike, or stale timestamps."""
    data = request.get_json() or {}
    symbol = data.get("symbol", DEFAULT_SYMBOL)
    shock_type = data.get("type", "none")  # flash_crash | spike | stale | clear
    
    if shock_type == "flash_crash":
        pct = float(data.get("pct", 0.08))  # 8% drop
        curr = simulated_prices.get(symbol, 2870.0)
        simulated_prices[symbol] = round(curr * (1.0 - pct), 2)
        injected_shocks[symbol] = f"FLASH_CRASH_{pct*100}%"
    elif shock_type == "spike":
        pct = float(data.get("pct", 0.06))  # 6% spike
        curr = simulated_prices.get(symbol, 2870.0)
        simulated_prices[symbol] = round(curr * (1.0 + pct), 2)
        injected_shocks[symbol] = f"PRICE_SPIKE_{pct*100}%"
    elif shock_type == "stale":
        delay_sec = int(data.get("delay_seconds", PRICE_STALENESS_SECONDS + 30))
        injected_delays[symbol] = delay_sec
    elif shock_type == "clear":
        injected_delays.pop(symbol, None)
        injected_shocks.pop(symbol, None)
        
    return jsonify({
        "status": "applied",
        "symbol": symbol,
        "shock_type": shock_type,
        "current_price": simulated_prices.get(symbol)
    })

@app.route("/market/<symbol>", methods=["GET"])
def get_market_data(symbol):
    now = time.time()
    
    # Check for injected staleness
    if symbol in injected_delays:
        tick_time = now - injected_delays[symbol]
    else:
        tick_time = now
        
    age_seconds = now - tick_time
    is_stale = age_seconds > PRICE_STALENESS_SECONDS

    price = simulated_prices.get(symbol, 2850.0)

    if current_mode == "REAL":
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            fast_info = getattr(ticker, "fast_info", None)
            if fast_info and getattr(fast_info, "last_price", None):
                price = float(fast_info.last_price)
            else:
                hist = ticker.history(period="1d", interval="1m")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
        except Exception:
            # Fall back to simulation if external network/market is unreachable
            pass

    # Random walk simulation if in simulated mode
    if current_mode == "SIMULATED":
        # Random normal move with slight drift
        drift = 0.0001
        vol = 0.0015
        change_pct = np.random.normal(drift, vol)
        price = round(price * (1.0 + change_pct), 2)
        simulated_prices[symbol] = price

    last_tick_times[symbol] = tick_time

    # NO_TRADE flag if data is stale or corrupted
    trade_allowed = not is_stale

    return jsonify({
        "symbol": symbol,
        "price": price,
        "timestamp": tick_time,
        "age_seconds": round(age_seconds, 2),
        "is_stale": is_stale,
        "trade_allowed": trade_allowed,
        "flag": "TRADE_ALLOWED" if trade_allowed else "NO_TRADE_STALE_DATA",
        "mode": current_mode,
        "shock_state": injected_shocks.get(symbol, "NORMAL")
    })

@app.route("/history/<symbol>", methods=["GET"])
def get_history(symbol):
    """Returns series of bars for technical indicators."""
    bars_count = int(request.args.get("bars", 60))
    curr_price = simulated_prices.get(symbol, 2850.0)
    
    # Generate realistic geometric brownian series leading up to current price
    np.random.seed(42)
    returns = np.random.normal(0.0002, 0.003, bars_count)
    prices = [curr_price]
    for r in returns[::-1]:
        prices.append(prices[-1] / (1 + r))
    prices = prices[::-1]
    
    bars = []
    now = time.time()
    for i, p in enumerate(prices):
        bar_time = now - (bars_count - i) * 60
        bar_open = round(p * (1 - 0.0005), 2)
        bar_close = round(p, 2)
        bar_high = round(max(bar_open, bar_close) * 1.001, 2)
        bar_low = round(min(bar_open, bar_close) * 0.999, 2)
        bars.append({
            "timestamp": bar_time,
            "open": bar_open,
            "high": bar_high,
            "low": bar_low,
            "close": bar_close,
            "volume": int(random.uniform(5000, 25000))
        })
    return jsonify({"symbol": symbol, "bars": bars})

@app.route("/news/<symbol>", methods=["GET"])
def get_news(symbol):
    now = time.time()
    # Check if news staleness injected
    is_news_stale = request.args.get("stale", "false").lower() == "true"
    base_time = now - (NEWS_STALENESS_SECONDS + 100 if is_news_stale else random.randint(10, 120))
    
    # Pick 2 to 4 headlines
    selected = random.sample(MOCK_HEADLINES, k=3)
    news_items = []
    for item in selected:
        news_items.append({
            "symbol": symbol,
            "headline": f"[{symbol}] {item['headline']}",
            "source": item["source"],
            "credibility": item["credibility"],
            "bias": item["bias"],
            "timestamp": base_time,
            "age_seconds": round(now - base_time, 1),
            "is_stale": is_news_stale
        })
        
    return jsonify({
        "symbol": symbol,
        "count": len(news_items),
        "is_stale": is_news_stale,
        "trade_allowed": not is_news_stale,
        "news": news_items
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT_DATA, debug=False)

