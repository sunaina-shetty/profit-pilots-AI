import datetime as dt
from simulation.live_market import check_nse_market_hours, LiveMarketManager
import os

def test_nse_market_hours_open():
    # Tuesday at 11:30 AM IST -> Should be OPEN
    dt_open = dt.datetime(2026, 11, 10, 11, 30, 0)
    res = check_nse_market_hours(dt_open)
    assert res["is_open"] is True
    assert res["status"] == "OPEN"

def test_nse_market_hours_pre_market():
    # Wednesday at 09:05 AM IST -> PRE_MARKET (is_open: False)
    dt_pre = dt.datetime(2026, 11, 11, 9, 5, 0)
    res = check_nse_market_hours(dt_pre)
    assert res["is_open"] is False
    assert res["status"] == "PRE_MARKET"

def test_nse_market_hours_closed_morning():
    # Wednesday at 08:30 AM IST -> CLOSED
    dt_early = dt.datetime(2026, 11, 11, 8, 30, 0)
    res = check_nse_market_hours(dt_early)
    assert res["is_open"] is False
    assert res["status"] == "CLOSED"

def test_nse_market_hours_closed_evening():
    # Wednesday at 16:00 (4:00 PM) IST -> CLOSED
    dt_late = dt.datetime(2026, 11, 11, 16, 0, 0)
    res = check_nse_market_hours(dt_late)
    assert res["is_open"] is False
    assert res["status"] == "CLOSED"

def test_nse_market_hours_weekend():
    # Saturday at 11:30 AM IST -> CLOSED (WEEKEND)
    dt_sat = dt.datetime(2026, 11, 14, 11, 30, 0) # Saturday
    res = check_nse_market_hours(dt_sat)
    assert res["is_open"] is False
    assert res["status"] == "CLOSED"
    assert "weekend" in res["reason"].lower()

def test_live_order_rejected_when_market_closed():
    # Ensure env var is not forcing open
    os.environ.pop("FORCE_LIVE_MARKET_OPEN", None)
    manager = LiveMarketManager()
    manager.symbol = "HDFCBANK.NS"
    res = check_nse_market_hours()
    if not res["is_open"]:
        trade = manager.execute_live_order("BUY", 10)
        assert trade is not None
        assert trade.get("status") == "rejected"
        assert "Market Closed" in trade.get("reason", "")


