import pytest
from backend.services.exchange_service.app import app
from backend.shared.token_utils import generate_risk_token
from backend.shared.db import init_sql_tables

@pytest.fixture(autouse=True)
def setup_db():
    init_sql_tables()

def test_missing_token_rejected():
    client = app.test_client()
    res = client.post("/order", json={
        "symbol": "RELIANCE.NS",
        "side": "BUY",
        "qty": 10,
        "entry_price": 2850.0,
        "stop_loss": 2800.0
    })
    assert res.status_code == 403
    assert "Missing signed risk approval token" in res.get_json()["error"]

def test_valid_order_execution():
    client = app.test_client()
    # Reset balance
    client.post("/reset")
    
    payload = {"symbol": "RELIANCE.NS", "side": "BUY", "qty": 10, "entry_price": 2850.0, "stop_loss": 2800.0}
    token = generate_risk_token(payload)

    order_req = dict(payload)
    order_req["approval_token"] = token
    
    res = client.post("/order", json=order_req)
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "FILLED"
    assert data["qty"] == 10
    assert data["fees"] > 0
    assert "order_id" in data

