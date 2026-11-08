import os
import pytest
import datetime
import numpy as np

# Force OFFLINE mode for unit tests
os.environ["OFFLINE"] = "1"
os.environ["LLM_API_KEY"] = ""

from simulation.market_data import (
    fetch_daily_ohlc, generate_intraday_candles, generate_fake_prior_day_candles
)
from simulation.broker import PaperBroker, calculate_fees
from simulation.news import evaluate_news_agent
from simulation.decision import decide_action
from simulation.agents import evaluate_trend_agent, evaluate_contrarian_agent
from simulation.engine import SimulationEngine
from simulation.indicators import compute_indicators

# -------------------------------------------------------------
# 1. Intraday Generator Tests
# -------------------------------------------------------------
def test_intraday_generator_exact_properties():
    ohlc = {
        "open": 3800.0,
        "high": 3920.0,
        "low": 3750.0,
        "close": 3890.0,
        "volume": 2500000
    }
    candles = generate_intraday_candles("TCS.NS", "2026-11-06", ohlc)
    
    assert len(candles) == 375
    # Starts at Open, ends at Close
    assert candles[0]["open"] == ohlc["open"]
    assert candles[-1]["close"] == ohlc["close"]
    
    # Touches High and Low exactly
    all_highs = [c["high"] for c in candles]
    all_lows = [c["low"] for c in candles]
    assert max(all_highs) == ohlc["high"]
    assert min(all_lows) == ohlc["low"]
    
    # Volume sums exactly
    total_vol = sum(c["volume"] for c in candles)
    assert total_vol == ohlc["volume"]

    # Reproducibility test
    candles_again = generate_intraday_candles("TCS.NS", "2026-11-06", ohlc)
    assert [c["close"] for c in candles] == [c["close"] for c in candles_again]

# -------------------------------------------------------------
# 2. Broker Private Key Security
# -------------------------------------------------------------
def test_broker_rejects_unauthorized_key():
    broker = PaperBroker(initial_cash=100000.0, symbol="TCS.NS", stop_loss_pct=1.0)
    with pytest.raises(PermissionError):
        broker.execute_buy(fill_price=3800.0, qty=10, time_str="09:35", entry_type="trend", auth_key="WRONG_KEY")

    with pytest.raises(PermissionError):
        broker.execute_sell(fill_price=3820.0, time_str="10:00", reason="Test", auth_key="WRONG_KEY")

# -------------------------------------------------------------
# 3. Stop-Loss & Gap-Down Execution
# -------------------------------------------------------------
def test_stop_loss_normal_and_gap_down():
    broker = PaperBroker(initial_cash=100000.0, symbol="TCS.NS", stop_loss_pct=1.0)
    key = broker.get_private_key()
    
    # Buy at 3800. 1% SL = 38.0. Stop price = 3762.0
    broker.execute_buy(fill_price=3800.0, qty=10, time_str="09:35", entry_type="trend", auth_key=key)
    assert broker.position["stop_loss"] == 3762.0

    # Candle dips to 3760, but opens at 3780 -> executes at stop (3762.0)
    candle_normal = {"open": 3780.0, "high": 3785.0, "low": 3760.0, "close": 3765.0, "time": "09:40"}
    trade = broker.check_stop_loss_on_candle(candle_normal, current_index=25)
    assert trade is not None
    assert trade["sell_price"] == 3762.0
    assert broker.position is None

    # Buy again for gap-down test
    broker.last_stop_hit_index = -100 # Reset cooldown
    broker.execute_buy(fill_price=3800.0, qty=10, time_str="10:00", entry_type="trend", auth_key=key)
    
    # Candle gaps down at open to 3750 (below stop 3762) -> must execute at candle OPEN (3750.0)
    candle_gap_down = {"open": 3750.0, "high": 3755.0, "low": 3740.0, "close": 3745.0, "time": "10:05"}
    trade_gap = broker.check_stop_loss_on_candle(candle_gap_down, current_index=35)
    assert trade_gap is not None
    assert trade_gap["sell_price"] == 3750.0

# -------------------------------------------------------------
# 4. Position Sizing
# -------------------------------------------------------------
def test_position_sizing_calculation():
    # 1,00,000 cash, 1% SL. Price = 3800.
    # Risk budget = 1,000. Risk/share = 38. Qty_risk = 1000 / 38 = 26 shares.
    # 50% cap = 50,000 / 3800 = 13.15 -> min(26, 13) = 13 shares for full size.
    broker = PaperBroker(initial_cash=100000.0, symbol="TCS.NS", stop_loss_pct=1.0)
    qty_full, msg = broker.calculate_position_size(3800.0, "full")
    assert qty_full == 13
    
    # Half size -> 13 * 0.5 = 6.5 -> 6 shares
    qty_half, _ = broker.calculate_position_size(3800.0, "half")
    assert qty_half == 6

    # Test case where 1% risk is the tighter constraint:
    # Amount = 1,00,000. Stop-loss = 3.0%. Price = 1000.
    # Risk budget = 1000. Risk/share = 30. Qty_risk = 1000 / 30 = 33.3 -> 33 shares.
    # 50% cap = 50,000 / 1000 = 50 shares.
    # Min(33, 50) = 33 shares.
    broker_tight_risk = PaperBroker(initial_cash=100000.0, symbol="INFY.NS", stop_loss_pct=3.0)
    qty_risk_tight, _ = broker_tight_risk.calculate_position_size(1000.0, "full")
    assert qty_risk_tight == 33

# -------------------------------------------------------------
# 5. Kill Switch & 2% Daily Loss Stop
# -------------------------------------------------------------
def test_kill_and_daily_loss_halt():
    broker = PaperBroker(initial_cash=100000.0, symbol="TCS.NS", stop_loss_pct=1.0)
    broker.is_killed = True
    can_b, reason = broker.can_buy(current_index=50)
    assert can_b is False
    assert "kill switch" in reason.lower()

    # Daily loss halt (2% of 100k = 2000 loss -> equity <= 98000)
    broker2 = PaperBroker(initial_cash=100000.0, symbol="TCS.NS", stop_loss_pct=1.0)
    key = broker2.get_private_key()
    broker2.execute_buy(fill_price=3800.0, qty=25, time_str="09:35", entry_type="trend", auth_key=key)
    
    # If price drops to 3700, loss is 25 * 100 = 2500 (> 2000)
    halted = broker2.evaluate_daily_loss_limit(3700.0)
    assert halted is True
    assert broker2.is_halted_loss_limit is True

# -------------------------------------------------------------
# 6. News Agent Rules
# -------------------------------------------------------------
def test_news_agent_rules():
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    sim_time = datetime.datetime(2026, 11, 6, 10, 0, tzinfo=ist_tz)
    
    # None -> HOLD
    res_none = evaluate_news_agent([], sim_time)
    assert res_none["signal"] == "HOLD"
    assert "no fresh news" in res_none["reason"].lower()

    # One headline (< 2 headlines capped at 0.3) -> cannot reach 0.35 threshold -> HOLD
    one_h = [{
        "title": "TCS reports record profit surge and revenue growth",
        "published_ist": sim_time - datetime.timedelta(minutes=15)
    }]
    res_one = evaluate_news_agent(one_h, sim_time)
    assert res_one["signal"] == "HOLD"

    # Three positive headlines -> BUY
    three_h = [
        {"title": "TCS reports record profit surge and beats earnings", "published_ist": sim_time - datetime.timedelta(minutes=10)},
        {"title": "TCS board approves major share buyback and growth plan", "published_ist": sim_time - datetime.timedelta(minutes=20)},
        {"title": "Analysts upgrade TCS to strong buy citing huge order win", "published_ist": sim_time - datetime.timedelta(minutes=30)}
    ]
    res_three = evaluate_news_agent(three_h, sim_time)
    assert res_three["signal"] == "BUY"

    # Future headlines are ignored (NO LOOKAHEAD)
    future_h = [
        {"title": "TCS surges 10% after massive earnings beat", "published_ist": sim_time + datetime.timedelta(hours=2)}
    ]
    res_future = evaluate_news_agent(future_h, sim_time)
    assert res_future["signal"] == "HOLD"
    assert "no fresh news" in res_future["reason"].lower()

# -------------------------------------------------------------
# 7. Decision Rules
# -------------------------------------------------------------
def test_decision_rules():
    # Flat, Trend=BUY, News=BUY, Contrarian=HOLD -> BUY full size
    d1 = decide_action(
        trend_res={"signal": "BUY"},
        news_res={"signal": "BUY", "confidence": 0.8},
        contrarian_res={"signal": "HOLD"},
        is_holding=False
    )
    assert d1["action"] == "BUY"
    assert d1["size"] == "full"

    # Flat, Trend=BUY, Contrarian=SELL -> HOLD (veto)
    d2 = decide_action(
        trend_res={"signal": "BUY"},
        news_res={"signal": "HOLD", "confidence": 0.5},
        contrarian_res={"signal": "SELL"},
        is_holding=False
    )
    assert d2["action"] == "HOLD"
    assert "veto" in d2["rule"].lower()

    # Flat, Trend=HOLD, Contrarian=BUY (dip-buy), News=HOLD -> BUY half size
    d3 = decide_action(
        trend_res={"signal": "HOLD"},
        news_res={"signal": "HOLD", "confidence": 0.5},
        contrarian_res={"signal": "BUY"},
        is_holding=False
    )
    assert d3["action"] == "BUY"
    assert d3["size"] == "half"

    # Holding trend trade, Trend=SELL -> SELL
    d4 = decide_action(
        trend_res={"signal": "SELL"},
        news_res={"signal": "HOLD"},
        contrarian_res={"signal": "HOLD"},
        is_holding=True,
        entry_type="trend"
    )
    assert d4["action"] == "SELL"

# -------------------------------------------------------------
# 8. 12 Full Simulated Days
# -------------------------------------------------------------
def test_twelve_full_simulated_days():
    """
    Replays 12 full simulated days across various stocks and dates.
    Asserts:
    - No crash
    - Flat at the end (no open position left)
    - Books reconcile (final equity - starting cash == sum of closed trade PnL)
    - Every journal entry has text
    - Bot trades on at least half the days (>= 6 days)
    """
    symbols = ["TCS.NS", "RELIANCE.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"]
    dates = [
        "2026-10-15", "2026-10-16", "2026-10-19", "2026-10-20",
        "2026-10-21", "2026-10-22", "2026-10-23", "2026-10-26",
        "2026-10-27", "2026-10-28", "2026-10-29", "2026-10-30"
    ]
    
    trading_days_count = 0

    for idx in range(12):
        sym = symbols[idx % len(symbols)]
        dt_str = dates[idx]
        
        sim = SimulationEngine()
        # Fast mode: run without sleeping
        sim.start_simulation(sym, amount=100000.0, stop_loss_pct=1.0, target_date_str=dt_str, fast_mode=True)
        sim.thread.join(timeout=10.0)

        state = sim.get_state()
        summary = state["summary"]
        
        assert state["status"] == "DONE"
        # Flat at end
        assert state["position"] is None
        # Books reconcile
        assert summary["reconciled"] is True
        # Journal has text
        assert len(state["journal"]) > 0
        for entry in state["journal"]:
            assert entry["reason"] is not None and len(entry["reason"].strip()) > 0

        if summary["total_trades"] > 0:
            trading_days_count += 1

    # Bot actually trades on at least half the days (>= 6 of 12)
    assert trading_days_count >= 6, f"Bot was too passive: only traded on {trading_days_count} of 12 days"
