"""Replays prices one tick at a time.

By default it generates a deterministic synthetic price path with clear market
phases (rally, chop, sell-off...) so the demo tells the same story every time.
If backend/data/prices.csv exists (see fetch_data.py), real yfinance prices are
replayed instead.
"""
import csv
import math
import os
import random

from .config import NEWS_WINDOW_TICKS, WARMUP_TICKS

# (ticks, drift per tick, volatility per tick)
PHASES = [
    (80, 0.0015, 0.004),    # rally
    (60, 0.0000, 0.004),    # sideways chop
    (90, -0.0018, 0.005),   # sell-off
    (70, 0.0000, 0.003),    # quiet
    (100, 0.0016, 0.004),   # recovery rally
    (80, -0.0010, 0.005),   # slow decline
]

# Scripted headlines line up with the phases above.
SCRIPTED_NEWS = [
    (20, "DEMO Corp beats quarterly earnings estimates", "Reuters"),
    (60, "Analysts upgrade DEMO Corp after strong guidance", "Bloomberg"),
    (110, "DEMO Corp holds investor day with no major updates", "Mint"),
    (150, "DEMO Corp faces regulatory probe over pricing", "Reuters"),
    (190, "DEMO Corp misses revenue targets as shares slide", "Economic Times"),
    (260, "DEMO Corp board names interim CEO, markets steady", "Mint"),
    (310, "DEMO Corp wins large government contract", "Bloomberg"),
    (350, "DEMO Corp raises full-year growth outlook", "Reuters"),
    (420, "DEMO Corp recalls product line after defect reports", "Economic Times"),
    (450, "Brokerages cut DEMO Corp price targets", "Bloomberg"),
]


def synthetic_prices(seed=42):
    rng = random.Random(seed)
    price, closes = 100.0, []
    for ticks, drift, vol in PHASES:
        for _ in range(ticks):
            price *= math.exp(rng.gauss(drift, vol))
            closes.append(round(price, 2))
    return closes


def csv_prices(path):
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))
    key = "Close" if "Close" in rows[0] else "close"
    return [round(float(r[key]), 2) for r in rows if r.get(key)]


class DataFeed:
    def __init__(self, csv_path=None, seed=42):
        if csv_path and os.path.exists(csv_path):
            self.closes = csv_prices(csv_path)
            self.source = "yfinance CSV"
        else:
            self.closes = synthetic_prices(seed)
            self.source = "synthetic replay"
        self.news = [
            {"tick": t, "headline": h, "source": s} for t, h, s in SCRIPTED_NEWS
            if t < len(self.closes)
        ]
        self.i = WARMUP_TICKS
        self.stale_ticks = 0        # >0 means the feed is frozen (chaos: stale data)
        self.frozen_i = None
        self.stale_age = 0

    # ---- replay control -------------------------------------------------
    def done(self):
        return self.i >= len(self.closes) - 1

    def advance(self):
        if self.done():
            return False
        self.i += 1
        if self.stale_ticks > 0:
            self.stale_ticks -= 1
            self.stale_age += 60
            if self.stale_ticks == 0:
                self.frozen_i = None
                self.stale_age = 0
        return True

    # ---- chaos hooks ----------------------------------------------------
    def shock(self, pct):
        """Flash crash: every future price is permanently shifted by pct."""
        for k in range(self.i + 1, len(self.closes)):
            self.closes[k] = round(self.closes[k] * (1 + pct), 2)

    def freeze(self, ticks):
        """Stale data: the bot keeps seeing the last price while the market moves on."""
        self.frozen_i = self.i
        self.stale_ticks = ticks
        self.stale_age = 300

    def inject_headline(self, headline, source):
        self.news.append({"tick": self.i + 1, "headline": headline, "source": source})

    # ---- what the bot sees ---------------------------------------------
    def true_price(self):
        return self.closes[self.i]

    def snapshot(self):
        seen = self.frozen_i if self.frozen_i is not None else self.i
        headlines = [
            n for n in self.news if seen - NEWS_WINDOW_TICKS < n["tick"] <= self.i
        ]
        return {
            "tick": self.i,
            "price": self.closes[seen],
            "prev_price": self.closes[seen - 1],
            "history": self.closes[: seen + 1],
            "age_seconds": self.stale_age if self.frozen_i is not None else 5,
            "headlines": sorted(headlines, key=lambda n: n["tick"], reverse=True),
        }
