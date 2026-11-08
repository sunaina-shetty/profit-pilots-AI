import os

# Ensure tests run deterministically and fast without waiting for yfinance DNS timeouts in sandbox
os.environ["OFFLINE"] = "1"

