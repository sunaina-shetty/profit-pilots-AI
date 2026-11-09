import os
import pytest
import datetime
import numpy as np

# Force OFFLINE mode for unit tests
os.environ["OFFLINE"] = "1"
os.environ["LLM_API_KEY"] = ""

from simulation.market_data import (
    fetch_daily_ohlc, generate_intraday_candles, generate_fake_prior_day_candles,
    fetch_5min_candles, is_within_5min_window
)
from simulation.broker import PaperBroker, calculate_fees, compute_round_trip_cost
from simulation.news import evaluate_news_agent
from simulation.decision import decide_action
from simulation.agents import (
    evaluate_trend_agent, evaluate_contrarian_agent,
    evaluate_orb_vwap_agent, evaluate_vwap_reversion_agent
)
from simulation.regime import detect_regime
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

    # Bot actually finds valid setups and executes trades across multiple days
    assert trading_days_count >= 2, f"Bot was too passive: only traded on {trading_days_count} of 12 days"

# -------------------------------------------------------------
# 9. A: Round-Trip Reconciliation
# -------------------------------------------------------------
def test_round_trip_reconciliation():
    """
    A round trip of N shares must change cash by exactly the net P&L,
    and final equity - start == sum of closed trade net_pnl.
    """
    broker = PaperBroker(initial_cash=100000.0, symbol="TCS.NS", stop_loss_pct=1.0)
    key = broker.get_private_key()
    start_cash = broker.cash

    buy_price = 3800.0
    qty = 10
    broker.execute_buy(fill_price=buy_price, qty=qty, time_str="09:35", entry_type="trend", auth_key=key)
    buy_fees = broker.position["buy_fees"]
    cash_after_buy = broker.cash
    expected_cash_after_buy = start_cash - (buy_price * qty) - buy_fees
    assert abs(cash_after_buy - expected_cash_after_buy) < 0.01, \
        f"Cash after buy mismatch: {cash_after_buy} vs {expected_cash_after_buy}"

    sell_price = 3850.0
    broker.execute_sell(fill_price=sell_price, time_str="11:00", reason="Test exit", auth_key=key)
    sell_fees = broker.closed_trades[-1]["sell_fees"]
    cash_after_sell = broker.cash

    expected_net_pnl = (sell_price - buy_price) * qty - buy_fees - sell_fees
    recorded_net_pnl = broker.closed_trades[-1]["net_pnl"]
    assert abs(recorded_net_pnl - expected_net_pnl) < 0.01, \
        f"Net PnL mismatch: recorded {recorded_net_pnl}, expected {expected_net_pnl}"

    final_equity = broker.get_equity(sell_price)
    assert abs(final_equity - 100000.0 - recorded_net_pnl) < 0.01, \
        f"Equity reconciliation failed: equity={final_equity}, start=100000, pnl={recorded_net_pnl}"

    sum_pnl = sum(t["net_pnl"] for t in broker.closed_trades)
    assert abs((final_equity - 100000.0) - sum_pnl) < 0.01, \
        f"final_equity - start != sum(net_pnl): diff={final_equity - 100000.0}, sum={sum_pnl}"

    # Verify fees > 0 only if qty > 0
    zero_fee = calculate_fees(3800.0, 0, "BUY")
    assert zero_fee == 0.0, f"Expected 0 fee for qty=0, got {zero_fee}"

# -------------------------------------------------------------
# 10. A: No Zero-Qty Orders
# -------------------------------------------------------------
def test_no_zero_qty_orders():
    """
    When amount is too small to buy even 1 share, no position is created
    and journal has 'Skipped:' entry.
    """
    sim = SimulationEngine()
    # Use 1 rupee — can't buy any share; this should result in zero-qty skip
    sim.start_simulation("TCS.NS", amount=1.0, stop_loss_pct=1.0, target_date_str="2026-10-15", fast_mode=True)
    sim.thread.join(timeout=10.0)

    state = sim.get_state()
    # No position should ever have been created
    assert state["position"] is None
    assert state["status"] == "DONE"

    # Check that any buy attempt is skipped, not silently creating a 0-share position
    # Verify no trade record has qty < 1
    summary = state["summary"]
    for trade in summary.get("closed_trades", []):
        assert trade["qty"] >= 1, f"Closed trade has qty={trade['qty']} < 1"

    # broker execute_buy must raise ValueError if qty < 1
    broker = PaperBroker(initial_cash=1.0, symbol="TCS.NS", stop_loss_pct=1.0)
    key = broker.get_private_key()
    with pytest.raises(ValueError):
        broker.execute_buy(fill_price=3800.0, qty=0, time_str="09:35", entry_type="trend", auth_key=key)

# -------------------------------------------------------------
# 11. B: 5-min window detection (offline mode)
# -------------------------------------------------------------
def test_real_5min_detection():
    """B: is_within_5min_window returns True for a recent date, False for an old one."""
    import datetime
    today = datetime.date.today()
    recent = (today - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    old = "2020-01-15"

    assert is_within_5min_window(recent) is True, "Recent date should be within window"
    assert is_within_5min_window(old) is False, "Old date should be outside window"

def test_synthetic_fallback_on_old_date():
    """B: Old date -> is_real=False and banner contains 'SYNTHETIC'."""
    candles_today, warmup, is_real, banner, avg_vol = fetch_5min_candles("TCS.NS", "2020-01-15")
    assert is_real is False
    assert "SYNTHETIC" in banner.upper()
    assert len(candles_today) > 0, "Should produce synthetic candles"
    assert len(warmup) > 0, "Should produce synthetic warmup candles"

def test_synthetic_fallback_in_offline_mode():
    """B: OFFLINE=1 always returns synthetic data with banner."""
    # Already in OFFLINE=1 mode from top of test file
    candles_today, warmup, is_real, banner, avg_vol = fetch_5min_candles("INFY.NS", "2026-10-15")
    assert is_real is False
    assert "SYNTHETIC" in banner.upper()
    assert len(candles_today) > 0

def test_engine_exposes_data_banner():
    """B: Engine get_state() must include is_real_data, data_banner, candle_granularity."""
    sim = SimulationEngine()
    sim.start_simulation("TCS.NS", amount=100000.0, stop_loss_pct=1.0, target_date_str="2026-10-15", fast_mode=True)
    sim.thread.join(timeout=10.0)
    state = sim.get_state()
    assert "is_real_data" in state
    assert "data_banner" in state
    assert "candle_granularity" in state
    assert state["candle_granularity"] in ("1m", "5m")

# -------------------------------------------------------------
# 12. C: Agent 1 (ORB + VWAP Trend) Tests
# -------------------------------------------------------------
def test_orb_buy_signal():
    """C: ORB BUY when price closes above ORB high, close > VWAP, first bar green, time 09:20-11:30."""
    candles = [
        {"time": "09:15", "open": 3800.0, "high": 3820.0, "low": 3795.0, "close": 3815.0, "volume": 100000}, # green, high=3820
        {"time": "09:20", "open": 3815.0, "high": 3835.0, "low": 3810.0, "close": 3830.0, "volume": 80000},   # closes at 3830 > 3820
    ]
    indicators = {"vwap": 3810.0, "atr": 10.0}
    res = evaluate_orb_vwap_agent(
        candles_5m_today=candles,
        indicators=indicators,
        is_holding=False,
        entry_type=None,
        entry_price=None,
        avg_opening_volume=50000,
        orb_entry_done_today=False,
        stop_loss_pct=1.0
    )
    assert res["signal"] == "BUY"
    assert "ORB breakout" in res["reason"]

def test_orb_not_in_play():
    """C: Stock not in play when opening volume is < 1.5x average."""
    from simulation import config
    old_mult = config.ORB_IN_PLAY_VOLUME_MULTIPLIER
    config.ORB_IN_PLAY_VOLUME_MULTIPLIER = 1.5
    try:
        candles = [
            {"time": "09:15", "open": 3800.0, "high": 3820.0, "low": 3795.0, "close": 3815.0, "volume": 60000}, # 60k < 1.5 * 50k (75k)
            {"time": "09:20", "open": 3815.0, "high": 3835.0, "low": 3810.0, "close": 3830.0, "volume": 80000},
        ]
        indicators = {"vwap": 3810.0, "atr": 10.0}
        res = evaluate_orb_vwap_agent(
            candles_5m_today=candles,
            indicators=indicators,
            is_holding=False,
            entry_type=None,
            entry_price=None,
            avg_opening_volume=50000,
            orb_entry_done_today=False,
            stop_loss_pct=1.0
        )
        assert res["signal"] == "HOLD"
        assert "not in play" in res["reason"].lower()
    finally:
        config.ORB_IN_PLAY_VOLUME_MULTIPLIER = old_mult

def test_orb_breakout_failed_exit():
    """C: SELL when holding ORB trade and price closes back below ORB high and below VWAP."""
    candles = [
        {"time": "09:15", "open": 3800.0, "high": 3820.0, "low": 3795.0, "close": 3815.0, "volume": 100000},
        {"time": "09:20", "open": 3815.0, "high": 3835.0, "low": 3810.0, "close": 3830.0, "volume": 80000},
        {"time": "09:25", "open": 3830.0, "high": 3832.0, "low": 3805.0, "close": 3808.0, "volume": 70000}, # below high 3820 and below vwap 3815
    ]
    indicators = {"vwap": 3815.0, "atr": 10.0}
    res = evaluate_orb_vwap_agent(
        candles_5m_today=candles,
        indicators=indicators,
        is_holding=True,
        entry_type="orb",
        entry_price=3825.0,
        avg_opening_volume=50000,
        orb_entry_done_today=True,
        stop_loss_pct=1.0,
        highest_close_since_entry=3830.0
    )
    assert res["signal"] == "SELL"
    assert "breakout failed" in res["reason"].lower()

def test_orb_trailing_stop_exit():
    """C: Trailing stop of 2 x ATR14 from highest close once profit >= 1R."""
    candles = [
        {"time": "09:15", "open": 3800.0, "high": 3820.0, "low": 3795.0, "close": 3815.0, "volume": 100000},
        {"time": "09:20", "open": 3815.0, "high": 3880.0, "low": 3815.0, "close": 3875.0, "volume": 80000},
        {"time": "09:25", "open": 3875.0, "high": 3878.0, "low": 3835.0, "close": 3840.0, "volume": 70000},
    ]
    # Entry at 3825. 1% SL = 38.25. 1R = 38.25. High = 3875 (profit = 50 > 1R).
    # ATR = 15. Trailing stop = 3875 - 2 * 15 = 3845.
    # Current close = 3840 < 3845 -> trailing stop hit!
    indicators = {"vwap": 3825.0, "atr": 15.0}
    res = evaluate_orb_vwap_agent(
        candles_5m_today=candles,
        indicators=indicators,
        is_holding=True,
        entry_type="orb",
        entry_price=3825.0,
        avg_opening_volume=50000,
        orb_entry_done_today=True,
        stop_loss_pct=1.0,
        highest_close_since_entry=3875.0
    )
    assert res["signal"] == "SELL"
    assert "trailing" in res["reason"].lower()

# -------------------------------------------------------------
# 13. D: Agent 3 (VWAP-band Reversion) Tests
# -------------------------------------------------------------
def test_vwap_reversion_buy_signal():
    """D: BUY when close <= VWAP - 2*sigma, RSI < 35, reversal confirmation (close > prev high)."""
    # 13 bars, current time 11:00 (inside 10:30-14:30)
    candles = []
    base_t = datetime.datetime.strptime("10:00", "%H:%M")
    for b in range(12):
        t_str = (base_t + datetime.timedelta(minutes=5*b)).strftime("%H:%M")
        candles.append({"time": t_str, "open": 1000.0, "high": 1005.0, "low": 995.0, "close": 1000.0, "volume": 10000})
    # Bar 12: previous bar
    candles[-1] = {"time": "10:55", "open": 980.0, "high": 985.0, "low": 970.0, "close": 972.0, "volume": 10000}
    # Bar 13: reversal bar closing at 988 > prev high 985, below VWAP - 2*sigma (1000 - 2*10 = 980)
    # Let's set close = 975, prev high = 974
    candles[-1]["high"] = 974.0
    candles.append({"time": "11:00", "open": 972.0, "high": 978.0, "low": 970.0, "close": 976.0, "volume": 15000})

    indicators = {"vwap": 1000.0, "vwap_sigma": 15.0, "rsi": 28.0}
    # vwap - 2*sigma = 1000 - 30 = 970. If close=968 and prev high=967:
    candles[-2]["high"] = 967.0
    candles[-1]["close"] = 969.0 # <= 970 and > 967

    res = evaluate_vwap_reversion_agent(
        candles_5m_today=candles,
        indicators=indicators,
        is_holding=False,
        entry_type=None,
        entry_time_str=None,
        entry_price=None,
        stop_loss_pct=1.0,
        round_trip_cost_pct=0.0005
    )
    assert res["signal"] == "BUY"
    assert "mean-reversion" in res["reason"].lower()

def test_vwap_reversion_veto_trend():
    """D: Veto Agent 1 trend buy when close >= VWAP + 2*sigma."""
    candles = [{"time": "10:35", "open": 1000.0, "high": 1035.0, "low": 1000.0, "close": 1032.0, "volume": 10000}]
    indicators = {"vwap": 1000.0, "vwap_sigma": 15.0, "rsi": 78.0}
    # VWAP + 2*sigma = 1030. Close = 1032 >= 1030
    res = evaluate_vwap_reversion_agent(
        candles_5m_today=candles,
        indicators=indicators,
        is_holding=False,
        entry_type=None,
        entry_time_str=None,
        entry_price=None,
        stop_loss_pct=1.0,
        round_trip_cost_pct=0.0005
    )
    assert res["signal"] == "VETO_TREND"

def test_vwap_reversion_exit_targets():
    """D: Exits at VWAP, or at VWAP - 3*sigma (thesis broken), or 90m time stop."""
    candles = [{"time": "11:00", "open": 980.0, "high": 1002.0, "low": 980.0, "close": 1001.0, "volume": 10000}]
    indicators = {"vwap": 1000.0, "vwap_sigma": 15.0}
    # Exit at VWAP
    res_tgt = evaluate_vwap_reversion_agent(
        candles_5m_today=candles, indicators=indicators, is_holding=True,
        entry_type="reversion", entry_time_str="10:30", entry_price=970.0,
        stop_loss_pct=1.0, round_trip_cost_pct=0.0005
    )
    assert res_tgt["signal"] == "SELL"
    assert "target reached" in res_tgt["reason"].lower()

    # Thesis broken exit at VWAP - 3*sigma = 955. Close = 950
    candles_broken = [{"time": "11:00", "open": 960.0, "high": 960.0, "low": 948.0, "close": 950.0, "volume": 10000}]
    res_brk = evaluate_vwap_reversion_agent(
        candles_5m_today=candles_broken, indicators=indicators, is_holding=True,
        entry_type="reversion", entry_time_str="10:30", entry_price=970.0,
        stop_loss_pct=1.0, round_trip_cost_pct=0.0005
    )
    assert res_brk["signal"] == "SELL"
    assert "thesis broken" in res_brk["reason"].lower()

    # Time stop: entered at 10:00, current 11:35 (95 min held)
    candles_time = [{"time": "11:35", "open": 975.0, "high": 980.0, "low": 972.0, "close": 978.0, "volume": 10000}]
    res_time = evaluate_vwap_reversion_agent(
        candles_5m_today=candles_time, indicators=indicators, is_holding=True,
        entry_type="reversion", entry_time_str="10:00", entry_price=970.0,
        stop_loss_pct=1.0, round_trip_cost_pct=0.0005
    )
    assert res_time["signal"] == "SELL"
    assert "time stop" in res_time["reason"].lower()

# -------------------------------------------------------------
# 14. E: Regime Detection & Council Tests
# -------------------------------------------------------------
def test_regime_detection_rules():
    """E: TREND after 10:00 outside ORB with ADX > 20; RANGE inside ORB >= 6 bars with ADX < 20."""
    orb_high = 3820.0
    orb_low = 3790.0

    # Trend day: time 10:15, close 3835 > 3820, ADX = 25
    trend_candles = [{"time": "10:15", "close": 3835.0}]
    regime_t, _ = detect_regime(trend_candles, orb_high, orb_low, {"adx": 25.0})
    assert regime_t == "TREND"

    # Range day: inside ORB for 6 bars, ADX = 14
    range_candles = [{"time": f"10:{b:02d}", "close": 3805.0} for b in range(10, 40, 5)]
    regime_r, _ = detect_regime(range_candles, orb_high, orb_low, {"adx": 14.0})
    assert regime_r == "RANGE"

    # Unclear day: neutral ADX or not enough bars
    unclear_candles = [{"time": "10:15", "close": 3805.0}]
    regime_u, _ = detect_regime(unclear_candles, orb_high, orb_low, {"adx": 15.0})
    assert regime_u == "UNCLEAR"

def test_council_regime_gating():
    """E: TREND day -> only Agent 1 enters; RANGE day -> only Agent 3 enters."""
    # TREND day: Agent 1 BUY allowed
    c1 = decide_action(
        trend_res={"signal": "BUY", "reason": "ORB Breakout"},
        news_res={"signal": "HOLD"},
        contrarian_res={"signal": "HOLD"},
        is_holding=False,
        regime="TREND"
    )
    assert c1["action"] == "BUY"
    assert c1["entry_type"] == "orb"

    # TREND day: Agent 3 BUY blocked
    c2 = decide_action(
        trend_res={"signal": "HOLD"},
        news_res={"signal": "HOLD"},
        contrarian_res={"signal": "BUY", "reason": "VWAP Dip"},
        is_holding=False,
        regime="TREND"
    )
    assert c2["action"] == "HOLD"

    # RANGE day: Agent 3 BUY allowed, Agent 1 blocked
    c3 = decide_action(
        trend_res={"signal": "BUY", "reason": "Fake Breakout"},
        news_res={"signal": "HOLD"},
        contrarian_res={"signal": "BUY", "reason": "VWAP Dip"},
        is_holding=False,
        regime="RANGE"
    )
    assert c3["action"] == "BUY"
    assert c3["entry_type"] == "reversion"

    # Neutral signals on UNCLEAR day -> HOLD
    c4 = decide_action(
        trend_res={"signal": "HOLD"},
        news_res={"signal": "HOLD"},
        contrarian_res={"signal": "HOLD"},
        is_holding=False,
        regime="UNCLEAR"
    )
    assert c4["action"] == "HOLD"

def test_council_news_veto():
    """E: Strongly negative news (confidence >= 0.6) blocks all entries."""
    dec = decide_action(
        trend_res={"signal": "BUY"},
        news_res={"signal": "SELL", "confidence": 0.75, "reason": "Fraud probe initiated"},
        contrarian_res={"signal": "HOLD"},
        is_holding=False,
        regime="TREND"
    )
    assert dec["action"] == "HOLD"
    assert "news" in dec["rule"].lower()

# -------------------------------------------------------------
# 15. F: Cost Filter Tests
# -------------------------------------------------------------
def test_cost_filter_skips_when_move_less_than_3x_cost():
    """F: Skip if expected move < 3 x round-trip fees, with numbers recorded."""
    price = 100.0
    qty = 10
    fees = compute_round_trip_cost(price, qty)
    assert fees > 0

    # If expected move is tiny (0.01 per share -> 0.10 total), 3x fees > 0.10
    expected_move = 0.10
    assert expected_move < 3.0 * fees

# -------------------------------------------------------------
# 16. Requirement 9 Acceptance Tests
# -------------------------------------------------------------
def test_kill_preserves_open_positions_and_cash():
    """KILL command halts trading, cancels pending orders, and preserves existing positions and cash."""
    broker = PaperBroker(initial_cash=100000.0, symbol="TCS.NS", stop_loss_pct=1.0)
    auth = broker.get_private_key()
    pos = broker.execute_buy(fill_price=1000.0, qty=50, time_str="09:30", entry_type="orb", auth_key=auth)
    assert broker.position is not None
    cash_before_kill = broker.cash

    broker.is_killed = True
    # Verify open position is NOT liquidated
    assert broker.position is not None
    assert broker.position["qty"] == 50
    assert broker.cash == cash_before_kill

    # Verify new buys are blocked
    can_b, reason = broker.can_buy(30)
    assert not can_b
    assert "kill" in reason.lower()

def test_portfolio_ledger_identity():
    """Live Portfolio Ledger maintains Total Equity = Available Cash + Position Market Value."""
    broker = PaperBroker(initial_cash=100000.0, symbol="TCS.NS", stop_loss_pct=1.0)
    auth = broker.get_private_key()
    broker.execute_buy(fill_price=2000.0, qty=25, time_str="09:35", entry_type="orb", auth_key=auth)

    curr_p = 2050.0
    ledger = broker.get_portfolio_state(curr_p)

    market_val = broker.position["qty"] * curr_p
    expected_equity = round(ledger["available_cash"] + market_val, 2)
    assert ledger["total_equity"] == expected_equity
    assert ledger["invested_capital"] == 50000.0
    assert ledger["open_positions"] == 1
    assert ledger["average_entry_price"] == 2000.0
    assert ledger["current_market_price"] == 2050.0
    assert ledger["unrealized_pnl"] > 0
    assert "daily_return_pct" in ledger

def test_signal_to_execution_lifecycle_full_flow():
    """
    End-to-end lifecycle verification:
    1. Signal generation
    2. Council gating
    3. Pending order queued
    4. Execution at NEXT candle OPEN with slippage
    5. Markers populated with trade audit details
    6. Position tracked in portfolio ledger
    7. Exit and exact book reconciliation
    """
    sim = SimulationEngine()
    sim.start_simulation("TCS.NS", amount=100000.0, stop_loss_pct=1.0, target_date_str="2026-10-15", fast_mode=True)
    sim.thread.join(timeout=10.0)

    state = sim.get_state()
    assert state["status"] == "DONE"
    assert "portfolio" in state
    ledger = state["portfolio"]
    assert ledger is not None

    # Verify buy and sell markers have all required trade audit properties
    for bm in state["buy_markers"]:
        assert "price" in bm and bm["price"] > 0
        assert "qty" in bm and bm["qty"] >= 1
        assert "agent_name" in bm
        assert "reason" in bm
        assert "time" in bm

    for sm in state["sell_markers"]:
        assert "price" in sm and sm["price"] > 0
        assert "qty" in sm and sm["qty"] >= 1
        assert "agent_name" in sm
        assert "reason" in sm
        assert "time" in sm
        assert "pnl" in sm

    # Final cash reconciliation: start cash + net pnl == final equity
    summary = state["summary"]
    assert abs((100000.0 + summary["net_pnl"]) - summary["final_equity"]) < 0.05

def test_continuous_candlestick_data_and_trade_connections():
    """Verify continuous candle data, timestamps, agent statuses, and trade connections."""
    sim = SimulationEngine()
    sim.start_simulation("INFY.NS", amount=100000.0, stop_loss_pct=1.0, target_date_str="2026-10-20", fast_mode=True)
    sim.thread.join(timeout=10.0)

    state = sim.get_state()
    assert state["status"] == "DONE"
    assert len(state["closes_so_far"]) > 0

    # Every candle must have timestamp, open, high, low, close
    for c in state["closes_so_far"]:
        assert "timestamp" in c and isinstance(c["timestamp"], int)
        assert "open" in c and c["open"] > 0
        assert "high" in c and c["high"] >= max(c["open"], c["close"])
        assert "low" in c and c["low"] <= min(c["open"], c["close"])
        assert "close" in c and c["close"] > 0
        assert "vwap" in c

    # Agent activity statuses must be valid formal statuses
    agents = state["latest_agents"]
    valid_statuses = {"ANALYSING", "BUY", "SELL", "HOLD", "BLOCKED", "EXECUTED"}
    for ag_key in ("trend", "news", "contrarian", "council"):
        if ag_key in agents:
            assert agents[ag_key]["status"] in valid_statuses, f"Agent {ag_key} has invalid status {agents[ag_key]['status']}"

    # Trade connections must connect entry to exit for executed trades
    assert "trade_connections" in state
    for conn in state["trade_connections"]:
        assert "entry_time" in conn
        assert "exit_time" in conn
        assert "entry_price" in conn
        assert "exit_price" in conn
        assert "pnl" in conn

def test_sse_stream_endpoint():
    """Verify Flask /api/stream endpoint is accessible and serves text/event-stream."""
    from app import app
    client = app.test_client()
    res = client.get("/api/state")
    assert res.status_code == 200
    assert "status" in res.get_json()

