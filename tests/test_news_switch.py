import datetime
import pytest
from app import app
from simulation.agent_config import agent_config_manager
from simulation.news import evaluate_news_agent

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

def test_news_agent_toggle_logic():
    now = datetime.datetime(2026, 11, 10, 10, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
    headlines = [
        {"title": "Tata Consultancy Services reports quarterly update", "published_ist": now, "time_str": "09:30"}
    ]

    # 1. Switch ON (Moneycontrol logic) -> Default YES
    res_on = evaluate_news_agent(headlines, now, default_yes=True)
    assert res_on["status"] == "YES"
    assert res_on["signal"] == "BUY"
    assert "Moneycontrol" in res_on["reason"]

    # 2. Switch OFF (Previous logic before moneycontrolpy) -> Standard Neutral / HOLD
    res_off = evaluate_news_agent(headlines, now, default_yes=False)
    assert res_off["status"] == "HOLD"
    assert res_off["signal"] == "HOLD"
    assert "Neutral" in res_off["reason"] or "sentiment" in res_off["reason"].lower()

def test_news_agent_endpoint(client):
    # Set to False (OFF)
    res = client.post("/api/news-config", json={"use_moneycontrol": False})
    assert res.status_code == 200
    data = res.get_json()
    assert data["use_moneycontrol"] is False
    assert agent_config_manager.get_config()["agent2"]["use_moneycontrol"] is False

    # Get status
    res_get = client.get("/api/news-config")
    assert res_get.status_code == 200
    assert res_get.get_json()["use_moneycontrol"] is False

    # Set back to True (ON)
    res_on = client.post("/api/news-config", json={"use_moneycontrol": True})
    assert res_on.status_code == 200
    assert res_on.get_json()["use_moneycontrol"] is True
    assert agent_config_manager.get_config()["agent2"]["use_moneycontrol"] is True
