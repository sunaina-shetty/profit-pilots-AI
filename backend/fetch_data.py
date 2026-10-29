"""Optional: replace the synthetic replay with real prices.

    pip install yfinance
    python fetch_data.py INFY.NS

Writes data/prices.csv; restart app.py and the bot replays it instead.
"""
import os
import sys

import yfinance as yf

symbol = sys.argv[1] if len(sys.argv) > 1 else "INFY.NS"
df = yf.download(symbol, period="5d", interval="5m", progress=False)
if df.empty:
    sys.exit(f"No data returned for {symbol}")
os.makedirs("data", exist_ok=True)
df[["Close"]].droplevel(1, axis=1).to_csv("data/prices.csv") if hasattr(df.columns, "levels") else df[["Close"]].to_csv("data/prices.csv")
print(f"Saved {len(df)} rows for {symbol} to data/prices.csv")
