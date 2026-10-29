"""Validation, the three voting agents, and the decision agent.

Agents are rule-based on purpose: deterministic, explainable, and they never
time out during a live demo. Swap news_agent for an LLM sentiment call later
if you want; the vote format stays the same.
"""
from .config import STALE_AFTER_SECONDS, TRUSTED_SOURCES

BUY, SELL, HOLD = "BUY", "SELL", "HOLD"

POSITIVE = ["beats", "upgrade", "strong", "wins", "raises", "growth", "record", "acquired", "premium"]
NEGATIVE = ["probe", "misses", "slide", "recall", "cut", "defect", "fraud", "downgrade", "loss"]


# ---------------------------------------------------------------- validation
def validate(snapshot):
    issues = []
    fresh = snapshot["age_seconds"] <= STALE_AFTER_SECONDS
    if not fresh:
        issues.append(f"Price data is {snapshot['age_seconds']}s old (limit {STALE_AFTER_SECONDS}s)")

    trusted, quarantined = [], []
    for h in snapshot["headlines"]:
        (trusted if h["source"] in TRUSTED_SOURCES else quarantined).append(h)
    for q in quarantined:
        issues.append(f"Quarantined headline from unverified source \"{q['source']}\"")

    return {
        "fresh": fresh,
        "age_seconds": snapshot["age_seconds"],
        "issues": issues,
        "headlines": trusted,
        "quarantined": quarantined,
    }


# ---------------------------------------------------------------- indicators
def sma(xs, n):
    return sum(xs[-n:]) / n


def rsi(xs, n=14):
    diffs = [b - a for a, b in zip(xs[-n - 1:-1], xs[-n:])]
    gains = sum(d for d in diffs if d > 0)
    losses = -sum(d for d in diffs if d < 0)
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100 - 100 / (1 + rs)


def vote(agent, action, reason, confidence):
    return {"agent": agent, "vote": action, "reason": reason, "confidence": round(confidence, 2)}


# ---------------------------------------------------------------- agents
def trend_agent(history):
    short, long_ = sma(history, 10), sma(history, 30)
    gap = (short - long_) / long_
    if gap > 0.002:
        return vote("Trend", BUY, f"10-tick average ({short:.2f}) is above 30-tick average ({long_:.2f}), so the trend is up.", min(1, abs(gap) * 50))
    if gap < -0.002:
        return vote("Trend", SELL, f"10-tick average ({short:.2f}) is below 30-tick average ({long_:.2f}), so the trend is down.", min(1, abs(gap) * 50))
    return vote("Trend", HOLD, "Averages are within 0.2% of each other; no clear trend.", 0.3)


def news_agent(headlines):
    if not headlines:
        return vote("News", HOLD, "No recent headlines from trusted sources.", 0.2)
    score = 0
    for h in headlines:
        text = h["headline"].lower()
        score += sum(w in text for w in POSITIVE) - sum(w in text for w in NEGATIVE)
    latest = headlines[0]
    cite = f"\"{latest['headline']}\" ({latest['source']})"
    if score > 0:
        return vote("News", BUY, f"Recent news is positive: {cite}.", min(1, 0.4 + 0.2 * score))
    if score < 0:
        return vote("News", SELL, f"Recent news is negative: {cite}.", min(1, 0.4 + 0.2 * -score))
    return vote("News", HOLD, f"Recent news is neutral: {cite}.", 0.3)


def contrarian_agent(history):
    r = rsi(history)
    price, long_ = history[-1], sma(history, 30)
    if r > 70:
        return vote("Contrarian", SELL, f"RSI is {r:.0f}: overbought, the move looks stretched.", 0.7)
    if r < 30:
        return vote("Contrarian", BUY, f"RSI is {r:.0f}: oversold, a bounce is likely.", 0.6)
    if price > long_ and r < 65:
        return vote("Contrarian", BUY, f"Uptrend is healthy and not overextended (RSI {r:.0f}).", 0.5)
    if price < long_ and r > 35:
        return vote("Contrarian", SELL, f"Downtrend has room to run, not yet oversold (RSI {r:.0f}).", 0.5)
    return vote("Contrarian", HOLD, f"RSI {r:.0f} gives no edge either way.", 0.3)


# ---------------------------------------------------------------- decision
def decide(votes, holding):
    """3 of 3 agree: full size. 2 of 3: half size. Otherwise HOLD."""
    counts = {BUY: 0, SELL: 0, HOLD: 0}
    for v in votes:
        counts[v["vote"]] += 1

    action, size, reason = HOLD, 0.0, "Agents disagree, so the bot waits. Disagreement is a risk signal."
    for a in (BUY, SELL):
        if counts[a] == 3:
            action, size, reason = a, 1.0, f"All 3 agents say {a}: full size."
        elif counts[a] == 2:
            action, size, reason = a, 0.5, f"2 of 3 agents say {a}: half size."

    if action == BUY and holding:
        return {"action": HOLD, "size": 0, "signal": BUY, "reason": "Agents still bullish; already holding, so no extra buying."}
    if action == SELL and not holding:
        return {"action": HOLD, "size": 0, "signal": SELL, "reason": "Agents bearish, but there is nothing to sell (long-only paper account)."}
    return {"action": action, "size": size, "signal": action, "reason": reason}
