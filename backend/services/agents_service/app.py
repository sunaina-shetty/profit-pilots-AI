import os
import sys
import time
import re
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from flask_cors import CORS

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from backend.shared.config import PORT_AGENTS

app = Flask(__name__)
CORS(app)

# ----------------- Financial Sentiment Lexicon ----------------- #
POSITIVE_KEYWORDS = {
    "record": 0.8, "profit": 0.7, "expand": 0.6, "buyback": 0.8, "partnership": 0.6,
    "growth": 0.7, "guidance": 0.5, "upgrade": 0.8, "beat": 0.75, "surge": 0.7,
    "bullish": 0.8, "outperform": 0.7, "dividend": 0.6, "gain": 0.5
}
NEGATIVE_KEYWORDS = {
    "scrutiny": -0.6, "bottleneck": -0.65, "rumor": -0.5, "loss": -0.8, "delay": -0.6,
    "downgrade": -0.8, "miss": -0.75, "crash": -0.9, "investigation": -0.85,
    "departure": -0.7, "bearish": -0.8, "drop": -0.6, "fall": -0.5, "fine": -0.75
}

def analyze_sentiment_llm_or_stub(text: str) -> float:
    """
    Analyzes sentiment using LLM or deterministic financial domain analyzer.
    Always constrained between -1.0 and +1.0.
    """
    text_lower = text.lower()
    score = 0.0
    matched_count = 0
    
    for word, weight in POSITIVE_KEYWORDS.items():
        if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
            score += weight
            matched_count += 1
            
    for word, weight in NEGATIVE_KEYWORDS.items():
        if re.search(r'\b' + re.escape(word) + r'\b', text_lower):
            score += weight
            matched_count += 1
            
    if matched_count > 0:
        return max(-1.0, min(1.0, score / matched_count))
    return 0.0

def compute_rsi(prices: pd.Series, period: int = 14) -> float:
    if len(prices) < period + 1:
        return 50.0
    deltas = prices.diff().dropna()
    gains = deltas.clip(lower=0)
    losses = -deltas.clip(upper=0)
    avg_gain = gains.rolling(window=period, min_periods=period).mean().iloc[-1]
    avg_loss = losses.rolling(window=period, min_periods=period).mean().iloc[-1]
    if pd.isna(avg_loss) or avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))

# ----------------- 1. Trend Agent ----------------- #
def run_trend_agent(symbol: str, bars: list) -> dict:
    if not bars or len(bars) < 15:
        return {
            "agent_name": "Trend Agent",
            "vote": "HOLD",
            "confidence": 0.3,
            "reasons": ["Insufficient historical bars for EMA and RSI calculation"],
            "timestamp": time.time()
        }

    df = pd.DataFrame(bars)
    closes = df["close"].astype(float)
    
    ema9 = closes.ewm(span=9, adjust=False).mean().iloc[-1]
    ema21 = closes.ewm(span=21, adjust=False).mean().iloc[-1]
    rsi = compute_rsi(closes, period=14)
    momentum = (closes.iloc[-1] - closes.iloc[-5]) / closes.iloc[-5] * 100.0
    
    reasons = [
        f"EMA9 ({round(ema9, 2)}) vs EMA21 ({round(ema21, 2)})",
        f"RSI-14 at {round(rsi, 1)}",
        f"5-bar Momentum: {round(momentum, 2)}%"
    ]
    
    if ema9 > ema21 and 48 <= rsi <= 68 and momentum > 0.05:
        confidence = min(0.92, 0.65 + abs(ema9 - ema21) / ema21 * 10.0)
        reasons.append("Bullish moving average crossover confirmed by healthy momentum")
        return {"agent_name": "Trend Agent", "vote": "BUY", "confidence": round(confidence, 2), "reasons": reasons, "timestamp": time.time()}
    elif ema9 < ema21 and 32 <= rsi <= 52 and momentum < -0.05:
        confidence = min(0.92, 0.65 + abs(ema21 - ema9) / ema21 * 10.0)
        reasons.append("Bearish moving average crossover confirmed by negative momentum")
        return {"agent_name": "Trend Agent", "vote": "SELL", "confidence": round(confidence, 2), "reasons": reasons, "timestamp": time.time()}
    else:
        reasons.append("Indecisive trend structure / neutral technical zone")
        return {"agent_name": "Trend Agent", "vote": "HOLD", "confidence": 0.50, "reasons": reasons, "timestamp": time.time()}

# ----------------- 2. News Agent ----------------- #
def run_news_agent(symbol: str, news_items: list) -> dict:
    if not news_items:
        return {
            "agent_name": "News Agent",
            "vote": "HOLD",
            "confidence": 0.20,
            "reasons": ["No fresh headlines available for sentiment evaluation"],
            "timestamp": time.time()
        }

    total_weighted_sentiment = 0.0
    total_weight = 0.0
    reasons = []

    for item in news_items:
        headline = item.get("headline", "")
        source = item.get("source", "Unknown")
        cred = float(item.get("credibility", 0.5))
        
        # Calculate sentiment
        sentiment = analyze_sentiment_llm_or_stub(headline)
        weighted_score = sentiment * cred
        total_weighted_sentiment += weighted_score
        total_weight += cred
        
        tag = "POSITIVE" if sentiment > 0.1 else ("NEGATIVE" if sentiment < -0.1 else "NEUTRAL")
        reasons.append(f"[{source}] '{headline[:48]}...' -> {tag} ({round(sentiment, 2)}) [Cred: {int(cred*100)}%]")

    avg_sentiment = total_weighted_sentiment / max(0.001, total_weight)
    reasons.insert(0, f"Aggregate credibility-weighted sentiment: {round(avg_sentiment, 2)}")

    if avg_sentiment > 0.25:
        conf = min(0.90, 0.55 + avg_sentiment * 0.4)
        return {"agent_name": "News Agent", "vote": "BUY", "confidence": round(conf, 2), "reasons": reasons, "timestamp": time.time()}
    elif avg_sentiment < -0.25:
        conf = min(0.90, 0.55 + abs(avg_sentiment) * 0.4)
        return {"agent_name": "News Agent", "vote": "SELL", "confidence": round(conf, 2), "reasons": reasons, "timestamp": time.time()}
    else:
        return {"agent_name": "News Agent", "vote": "HOLD", "confidence": 0.45, "reasons": reasons, "timestamp": time.time()}

# ----------------- 3. Contrarian Agent ----------------- #
def run_contrarian_agent(symbol: str, bars: list, news_items: list) -> dict:
    if not bars or len(bars) < 15:
        return {
            "agent_name": "Contrarian Agent",
            "vote": "HOLD",
            "confidence": 0.30,
            "reasons": ["Insufficient data for crowd over-extension detection"],
            "timestamp": time.time()
        }

    df = pd.DataFrame(bars)
    closes = df["close"].astype(float)
    rsi = compute_rsi(closes, period=14)
    pct_from_low = (closes.iloc[-1] - closes.min()) / closes.min() * 100.0
    pct_from_high = (closes.max() - closes.iloc[-1]) / closes.max() * 100.0

    reasons = [
        f"RSI extreme check: {round(rsi, 1)}",
        f"Distance from recent range low: +{round(pct_from_low, 2)}%",
        f"Distance from recent range high: -{round(pct_from_high, 2)}%"
    ]

    # Extreme overbought condition -> Contrarian SELL
    if rsi >= 70.0:
        reasons.append(f"Overbought extreme (RSI {round(rsi, 1)} >= 70). Crowd euphoria prone to mean-reversion pullbacks.")
        return {"agent_name": "Contrarian Agent", "vote": "SELL", "confidence": 0.85, "reasons": reasons, "timestamp": time.time()}
    
    # Extreme oversold condition -> Contrarian BUY
    elif rsi <= 30.0:
        reasons.append(f"Oversold extreme (RSI {round(rsi, 1)} <= 30). Panic selling likely exhausted; mean-reversion bounce expected.")
        return {"agent_name": "Contrarian Agent", "vote": "BUY", "confidence": 0.85, "reasons": reasons, "timestamp": time.time()}
    
    # Mild range
    else:
        reasons.append("No crowd extremes detected; respecting prevailing technical range.")
        return {"agent_name": "Contrarian Agent", "vote": "HOLD", "confidence": 0.40, "reasons": reasons, "timestamp": time.time()}

# ----------------- Endpoints ----------------- #
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "service": "agents_service",
        "status": "healthy",
        "port": PORT_AGENTS,
        "agents": ["Trend Agent", "News Agent", "Contrarian Agent"],
        "timestamp": time.time()
    })

@app.route("/evaluate", methods=["POST"])
def evaluate():
    """Runs all 3 agents in parallel and returns their votes."""
    data = request.get_json() or {}
    symbol = data.get("symbol", "RELIANCE.NS")
    bars = data.get("bars", [])
    news = data.get("news", [])

    trend_res = run_trend_agent(symbol, bars)
    news_res = run_news_agent(symbol, news)
    contrarian_res = run_contrarian_agent(symbol, bars, news)

    return jsonify({
        "symbol": symbol,
        "trend": trend_res,
        "news": news_res,
        "contrarian": contrarian_res,
        "timestamp": time.time()
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT_AGENTS, debug=False)

