import pytest
from backend.services.chaos_service.app import run_single_scenario, SCENARIOS

def test_all_chaos_scenarios_have_valid_metadata():
    assert len(SCENARIOS) >= 10
    ids = [s["id"] for s in SCENARIOS]
    assert "flash_crash" in ids
    assert "daily_loss_limit_breach" in ids
    assert "kill_switch_during_open_order" in ids
    assert "stale_price_feed" in ids
    assert "conflicting_agent_votes" in ids

def test_llm_garbage_resilience():
    res = run_single_scenario("llm_failure_garbage")
    assert res["passed"] is True
    assert res["status"] == "SAFE"

def test_fake_misleading_headline_discounting():
    res = run_single_scenario("fake_misleading_headline")
    assert res["passed"] is True
    assert res["status"] == "SAFE"

