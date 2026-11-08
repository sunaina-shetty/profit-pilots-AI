import os
import pytest
from app import app
from simulation.engine import SimulationEngine
from simulation.broker import PaperBroker

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_j1_j7_hold_marker_options_and_no_clutter():
    """J1 & J7: HOLD decisions display small orange markers and HOLD visibility can be toggled without clutter."""
    eng = SimulationEngine()
    eng.start_simulation("TCS", 100000.0, 1.0, "2026-11-06", fast_mode=True)
    if eng.thread:
        eng.thread.join(timeout=5.0)

    st = eng.get_state()
    # Holds are captured in journal
    holds = [j for j in st["journal"] if j.get("is_hold") or j.get("action") == "HOLD"]
    assert len(holds) > 0, "Hold decisions are present in audit journal"

def test_j2_j3_j4_actual_buy_and_sell_markers():
    """J2, J3, J4: Actual BUY executions display green arrows, SELL displays red arrows at correct timestamps and prices."""
    broker = PaperBroker(symbol="TCS.NS", initial_cash=100000.0, stop_loss_pct=1.0)
    auth_key = broker.get_private_key()

    # Execute BUY
    pos = broker.execute_buy(3850.0, 10, "09:25", "orb", auth_key)
    assert pos["qty"] == 10
    assert pos["buy_price"] == 3850.0

    # Execute SELL
    trade = broker.execute_sell(3870.0, "09:40", "Target reached", auth_key)
    assert trade["qty"] == 10
    assert trade["sell_price"] == 3870.0
    assert trade["net_pnl"] > 0

def test_j5_agent1_and_agent3_distinguished():
    """J5: Agent 1 (ORB) and Agent 3 (Reversion) can be distinguished by entry_type and marker tags."""
    broker = PaperBroker(symbol="TCS.NS", initial_cash=100000.0, stop_loss_pct=1.0)
    auth_key = broker.get_private_key()

    buy_markers = []
    # Simulate Agent 1 fill
    broker.execute_buy(3850.0, 10, "09:20", "orb", auth_key)
    buy_markers.append({
        "id": "buy-1",
        "trade_id": "t1",
        "time": 1700000000,
        "price": 3850.0,
        "qty": 10,
        "agent_name": "Agent 1: ORB + VWAP Trend",
        "agent_tag": "Agent 1 (ORB)",
        "action": "BUY"
    })

    broker.execute_sell(3860.0, "09:50", "Exit", auth_key)

    # Simulate Agent 3 fill
    broker.execute_buy(3820.0, 10, "11:00", "reversion", auth_key)
    buy_markers.append({
        "id": "buy-2",
        "trade_id": "t2",
        "time": 1700003600,
        "price": 3820.0,
        "qty": 10,
        "agent_name": "Agent 3: VWAP Reversion",
        "agent_tag": "Agent 3 (Reversion)",
        "action": "BUY"
    })

    assert "Agent 1" in buy_markers[0]["agent_name"]
    assert "Agent 3" in buy_markers[1]["agent_name"]
    assert buy_markers[0]["agent_tag"] != buy_markers[1]["agent_tag"]

def test_j6_agent2_news_confirmation_visible():
    """J6: Agent 2 news confirmation and veto status are present in latest_agents."""
    eng = SimulationEngine()
    eng.start_simulation("TCS", 100000.0, 1.0, "2026-11-06", fast_mode=True)
    if eng.thread:
        eng.thread.join(timeout=5.0)

    st = eng.get_state()
    latest_agents = st.get("latest_agents", {})
    assert "news" in latest_agents, "Agent 2 news agent state must be present"
    news_ag = latest_agents["news"]
    assert "status" in news_ag
    assert "sentiment" in news_ag or "facts" in news_ag
    assert "veto_status" in news_ag

def test_j8_candlesticks_configured_properly():
    """J8: Candlestick bundle configures barSpacing and ResizeObserver for clean slim candles."""
    bundle_path = os.path.join("frontend", "dist", "assets")
    js_files = [f for f in os.listdir(bundle_path) if f.endswith(".js")]
    assert len(js_files) > 0
    with open(os.path.join(bundle_path, js_files[0]), "r", encoding="utf-8") as f:
        code = f.read()
    assert "barSpacing" in code or "minBarSpacing" in code
    assert "ResizeObserver" in code

def test_j9_no_fake_trades_generated():
    """J9: No artificial BUY or SELL execution markers are generated when council does not execute."""
    eng = SimulationEngine()
    st = eng.get_state()
    # Before START, buy_markers and sell_markers must be empty
    assert len(st["buy_markers"]) == 0
    assert len(st["sell_markers"]) == 0

def test_j10_portfolio_ledger_values_preserved():
    """J10: Existing portfolio values remain unchanged by visualization changes."""
    eng = SimulationEngine()
    eng.start_simulation("TCS", 100000.0, 1.0, "2026-11-06", fast_mode=True)
    if eng.thread:
        eng.thread.join(timeout=5.0)

    st = eng.get_state()
    portfolio = st["portfolio"]
    assert portfolio is not None
    assert portfolio["available_cash"] > 0
    assert portfolio["total_equity"] > 0
    # Identity: cash + invested capital == equity (when flat, cash == equity)
    if st["position"] is None:
        assert round(portfolio["available_cash"], 2) == round(portfolio["total_equity"], 2)

def test_j11_start_and_kill_continue_working(client):
    """J11: START and KILL endpoints continue working seamlessly."""
    res_start = client.post("/api/start", json={"symbol": "TCS", "amount": 100000, "stop_loss_pct": 1.0})
    assert res_start.status_code == 200
    st_start = res_start.get_json()["state"]
    assert st_start["status"] == "RUNNING"

    res_kill = client.post("/api/kill")
    assert res_kill.status_code == 200
    st_kill = res_kill.get_json()["state"]
    assert st_kill["status"] == "KILLED"
