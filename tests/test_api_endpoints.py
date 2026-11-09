"""
test_api_endpoints.py — Verifies the new Groww-Inspired Terminal backend API endpoints:
  - GET /api/strategies
  - GET /api/agent-config
  - POST /api/agent-config
  - GET /api/market-indices
  - POST /api/kill (with modes: "stop_new" and "flatten")
"""
import pytest
import json
from app import app
from simulation.agent_config import agent_config_manager

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_get_strategies_endpoint(client):
    res = client.get("/api/strategies")
    assert res.status_code == 200
    data = res.get_json()
    assert "strategies" in data
    assert len(data["strategies"]) == 10
    ids = [s["id"] for s in data["strategies"]]
    assert "strat_ema_rsi_vol" in ids
    assert "strat_supertrend_ema200" in ids
    assert "strat_orb" in ids
    assert "strat_bb_rsi_reversal" in ids

def test_get_and_post_agent_config(client):
    # GET
    res = client.get("/api/agent-config")
    assert res.status_code == 200
    cfg = res.get_json()
    assert "agent1" in cfg
    assert "agent2" in cfg
    assert "agent3" in cfg
    assert "risk" in cfg

    # POST update Agent 1 strategy to EMA RSI Volume
    patch = {
        "agent1": {
            "strategy_id": "strat_ema_rsi_vol",
            "weight": 0.40
        }
    }
    res_post = client.post("/api/agent-config", json=patch)
    assert res_post.status_code == 200
    updated = res_post.get_json()["config"]
    assert updated["agent1"]["strategy_id"] == "strat_ema_rsi_vol"
    assert updated["agent1"]["weight"] == 0.40

    # Reset
    res_reset = client.post("/api/agent-config/reset")
    assert res_reset.status_code == 200
    reset_cfg = res_reset.get_json()["config"]
    assert reset_cfg["agent1"]["strategy_id"] == "strat_orb"

def test_market_indices_endpoint(client):
    res = client.get("/api/market-indices")
    assert res.status_code == 200
    data = res.get_json()
    assert "indices" in data
    names = [i["name"] for i in data["indices"]]
    assert "NIFTY 50" in names
    assert "SENSEX" in names
    assert "BANK NIFTY" in names

def test_kill_endpoint_modes(client):
    # 1. stop_new mode
    res_stop_new = client.post("/api/kill", json={"mode": "stop_new"})
    assert res_stop_new.status_code == 200
    data = res_stop_new.get_json()
    assert data["status"] == "killed"
    assert data["mode"] == "stop_new"

    # 2. flatten mode
    res_flatten = client.post("/api/kill", json={"mode": "flatten"})
    assert res_flatten.status_code == 200
    data_f = res_flatten.get_json()
    assert data_f["status"] == "killed"
    assert data_f["mode"] == "flatten"

