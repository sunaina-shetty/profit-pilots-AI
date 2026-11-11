import pytest
import os
import json
from app import app
from simulation.live_market import live_market_manager, check_nse_market_hours
from simulation.agent_config import agent_config_manager

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_live_market_bot_start_stop():
    # Test starting the bot
    res = live_market_manager.start_trade_bot(amount=50000.0, stop_loss_pct=1.5)
    assert res["status"] == "started"
    assert live_market_manager.bot_status == "RUNNING"
    assert live_market_manager.initial_amount == 50000.0
    assert live_market_manager.stop_loss_pct == 1.5

    # Check state output
    state = live_market_manager.get_state()
    assert state["bot_status"] == "RUNNING"
    assert "latest_agents" in state
    assert "trend" in state["latest_agents"]
    assert "news" in state["latest_agents"]
    assert "contrarian" in state["latest_agents"]
    assert "council" in state["latest_agents"]

    # Test stop bot with mode=flatten
    stop_res = live_market_manager.stop_trade_bot(mode="flatten")
    assert stop_res["status"] == "stopped"
    assert live_market_manager.bot_status == "STOPPED"

def test_live_market_bot_takes_agent_config():
    # Update Agent 1 and Agent 3 strategies in agent_config_manager
    agent_config_manager.update_config({
        "agent1": {"strategy_id": "strat_supertrend_ema200"},
        "agent3": {"strategy_id": "strat_bb_rsi_reversal"},
        "agent2": {"use_moneycontrol": True}
    })

    # Trigger a tick evaluation
    live_market_manager._tick()

    state = live_market_manager.get_state()
    agents = state.get("latest_agents", {})
    
    assert "Supertrend" in agents["trend"].get("agent_name", "") or agents["trend"].get("strategy_id") == "strat_supertrend_ema200" or "Supertrend" in agents["trend"].get("strategy_name", "")
    assert "Bollinger" in agents["contrarian"].get("agent_name", "") or agents["contrarian"].get("strategy_id") == "strat_bb_rsi_reversal" or "Bollinger" in agents["contrarian"].get("strategy_name", "")

def test_live_bot_api_endpoints(client):
    # Test POST /api/live/bot/start
    resp = client.post("/api/live/bot/start", json={
        "symbol": "TCS.NS",
        "amount": 75000,
        "stop_loss_pct": 1.2
    })
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["status"] == "started"
    assert data["bot_status"] == "RUNNING"

    # Test POST /api/live/bot/stop
    resp_stop = client.post("/api/live/bot/stop", json={"mode": "stop_new"})
    assert resp_stop.status_code == 200
    data_stop = json.loads(resp_stop.data)
    assert data_stop["status"] == "paused_new"
    assert data_stop["bot_status"] == "PAUSED_NEW"

    # Stop flatten
    resp_flat = client.post("/api/live/bot/stop", json={"mode": "flatten"})
    assert resp_flat.status_code == 200
    data_flat = json.loads(resp_flat.data)
    assert data_flat["status"] == "stopped"
    assert data_flat["bot_status"] == "STOPPED"

def test_change_agent1_and_agent3_reflects_in_live_market(client):
    # Change Agent 1 to MACD and Agent 3 to Donchian
    resp = client.post("/api/agent-config", json={
        "agent1": {"strategy_id": "strat_macd_rsi_ema200"},
        "agent3": {"strategy_id": "strat_donchian_breakout"}
    })
    assert resp.status_code == 200
    data = json.loads(resp.data)
    assert data["config"]["agent1"]["strategy_id"] == "strat_macd_rsi_ema200"
    assert data["config"]["agent3"]["strategy_id"] == "strat_donchian_breakout"

    # Verify live market state includes agent_config and updated strategies
    resp_live = client.get("/api/live/state")
    assert resp_live.status_code == 200
    live_data = json.loads(resp_live.data)
    assert "agent_config" in live_data
    assert live_data["agent_config"]["agent1"]["strategy_id"] == "strat_macd_rsi_ema200"
    assert live_data["agent_config"]["agent3"]["strategy_id"] == "strat_donchian_breakout"
    
    # Check agent names in latest_agents reflect the new strategies
    trend_agent = live_data["latest_agents"]["trend"]
    contrarian_agent = live_data["latest_agents"]["contrarian"]
    assert "MACD" in trend_agent.get("agent_name", "") or trend_agent.get("strategy_id") == "strat_macd_rsi_ema200"
    assert "Donchian" in contrarian_agent.get("agent_name", "") or contrarian_agent.get("strategy_id") == "strat_donchian_breakout"
