import pytest
from backend.services.decision_service.app import app

def test_unanimous_buy_consensus():
    client = app.test_client()
    res = client.post("/decide", json={
        "symbol": "RELIANCE.NS",
        "price": 2850.0,
        "trend": {"vote": "BUY", "confidence": 0.8},
        "news": {"vote": "BUY", "confidence": 0.85},
        "contrarian": {"vote": "BUY", "confidence": 0.75}
    })
    data = res.get_json()
    assert data["action"] == "BUY"
    assert data["size_tier"] == "FULL"
    assert data["suggested_stop"] < 2850.0
    assert data["suggested_target"] > 2850.0

def test_two_thirds_supermajority_half_size():
    client = app.test_client()
    res = client.post("/decide", json={
        "symbol": "RELIANCE.NS",
        "price": 2850.0,
        "trend": {"vote": "BUY", "confidence": 0.8},
        "news": {"vote": "BUY", "confidence": 0.85},
        "contrarian": {"vote": "HOLD", "confidence": 0.5}
    })
    data = res.get_json()
    assert data["action"] == "BUY"
    assert data["size_tier"] == "HALF"

def test_disagreement_forces_hold():
    client = app.test_client()
    res = client.post("/decide", json={
        "symbol": "RELIANCE.NS",
        "price": 2850.0,
        "trend": {"vote": "BUY", "confidence": 0.8},
        "news": {"vote": "SELL", "confidence": 0.8},
        "contrarian": {"vote": "HOLD", "confidence": 0.5}
    })
    data = res.get_json()
    assert data["action"] == "HOLD"
    assert data["size_tier"] == "ZERO"
    assert "Disagreement" in data["reason"]

