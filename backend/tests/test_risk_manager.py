import pytest
import time
from backend.shared.token_utils import generate_risk_token, verify_risk_token
from backend.services.risk_service.app import app, set_kill_switch_state, set_market_state
from sqlalchemy import text
from backend.shared.db import init_sql_tables, SQL_ENGINE

@pytest.fixture(autouse=True)
def setup_db():
    init_sql_tables()
    set_kill_switch_state("OFF")
    set_market_state("RUNNING")
    with SQL_ENGINE.begin() as conn:
        conn.execute(text("DELETE FROM positions"))
        conn.execute(text("UPDATE account_balance SET cash = 100000.0, start_of_day_equity = 100000.0, realized_pnl = 0.0, unrealized_pnl = 0.0 WHERE id = 1"))

def test_token_generation_and_verification():
    payload = {"symbol": "RELIANCE.NS", "side": "BUY", "qty": 10, "entry_price": 2850.0, "stop_loss": 2800.0}
    token = generate_risk_token(payload, expires_in_seconds=5)
    
    # Valid check
    valid, msg = verify_risk_token(token, {"symbol": "RELIANCE.NS", "side": "BUY", "qty": 10})
    assert valid is True
    assert msg == "Valid"

    # Mismatch check
    invalid, msg = verify_risk_token(token, {"symbol": "RELIANCE.NS", "side": "BUY", "qty": 999})
    assert invalid is False
    assert "Token mismatch" in msg

def test_kill_switch_blocks_evaluation():
    client = app.test_client()
    set_kill_switch_state("ON")
    
    res = client.post("/evaluate", json={
        "symbol": "RELIANCE.NS",
        "side": "BUY",
        "entry_price": 2850.0,
        "stop_loss": 2800.0,
        "size_tier": "FULL"
    })
    data = res.get_json()
    assert data["approved"] is False
    assert "KILL SWITCH" in data["reason"]

def test_mandatory_stop_loss():
    client = app.test_client()
    # Missing stop loss
    res = client.post("/evaluate", json={
        "symbol": "RELIANCE.NS",
        "side": "BUY",
        "entry_price": 2850.0,
        "stop_loss": 0.0,
        "size_tier": "FULL"
    })
    data = res.get_json()
    assert data["approved"] is False
    assert "MANDATORY STOP-LOSS" in data["reason"]

def test_stop_loss_orientation_rule():
    client = app.test_client()
    # BUY with stop loss higher than entry (illogical)
    res = client.post("/evaluate", json={
        "symbol": "RELIANCE.NS",
        "side": "BUY",
        "entry_price": 2850.0,
        "stop_loss": 2900.0,
        "size_tier": "FULL"
    })
    data = res.get_json()
    assert data["approved"] is False
    assert "strictly below" in data["reason"]

def test_stale_data_blocks_orders():
    client = app.test_client()
    res = client.post("/evaluate", json={
        "symbol": "RELIANCE.NS",
        "side": "BUY",
        "entry_price": 2850.0,
        "stop_loss": 2800.0,
        "size_tier": "FULL",
        "data_fresh": False
    })
    data = res.get_json()
    assert data["approved"] is False
    assert "STALE" in data["reason"]

def test_one_percent_risk_sizing():
    client = app.test_client()
    # 100,000 equity -> 1% risk = 1,000. Entry = 1000, SL = 950 (diff = 50).
    # Qty = 1000 / 50 = 20 shares. Position cost = 20,000 <= 30,000 max exposure limit.
    res = client.post("/evaluate", json={
        "symbol": "TCS.NS",
        "side": "BUY",
        "entry_price": 1000.0,
        "stop_loss": 950.0,
        "size_tier": "FULL",
        "data_fresh": True
    })
    data = res.get_json()
    assert data["approved"] is True
    assert data["qty"] == 20
    assert data["approval_token"] is not None

def test_max_position_exposure_capping():
    client = app.test_client()
    # Entry = 2850, SL = 2800 (diff = 50). Raw Qty = 20 shares.
    # Cost = 20 * 2850 = 57,000 > 30,000 (30% max position limit).
    # Capped at 30,000 / 2850 = 10 shares.
    res = client.post("/evaluate", json={
        "symbol": "RELIANCE.NS",
        "side": "BUY",
        "entry_price": 2850.0,
        "stop_loss": 2800.0,
        "size_tier": "FULL",
        "data_fresh": True
    })
    data = res.get_json()
    assert data["approved"] is True
    assert data["qty"] == 10
