import os
import pytest

# Ensure offline deterministic test execution
os.environ["OFFLINE"] = "1"

from simulation.backtest import run_strategy_backtest
from app import app


def test_backtest_engine_execution():
    """Verify backtesting engine executes chronological multi-day test with full metrics."""
    res = run_strategy_backtest(
        symbol="TCS",
        strategy_id="strat_ema_rsi_vol",
        days=3,
        initial_capital=100000.0,
        risk_per_trade_pct=0.5,
        stop_loss_pct=1.0,
        target_rr=1.5
    )

    assert res["status"] == "success"
    assert res["symbol"] == "TCS"
    assert res["strategy_id"] == "strat_ema_rsi_vol"
    assert "metrics" in res

    metrics = res["metrics"]
    assert "net_profit" in metrics
    assert "win_rate" in metrics
    assert "profit_factor" in metrics
    assert "max_drawdown" in metrics
    assert "sharpe_ratio" in metrics
    assert "total_fees" in metrics
    assert isinstance(res["equity_curve"], list)
    assert isinstance(res["trades"], list)


def test_backtest_unknown_strategy():
    """Verify error raised for invalid strategy ID."""
    with pytest.raises(ValueError, match="Unknown strategy ID"):
        run_strategy_backtest(symbol="TCS", strategy_id="non_existent_strat")


def test_api_stock_quote():
    """Verify GET /api/stock-quote returns stock details."""
    client = app.test_client()
    resp = client.get("/api/stock-quote?symbol=TCS")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["symbol"] == "TCS"
    assert "current_price" in data
    assert "day_high" in data
    assert "day_low" in data
    assert "volume" in data


def test_api_backtest_endpoint():
    """Verify POST /api/backtest API returns complete backtest report."""
    client = app.test_client()
    resp = client.post("/api/backtest", json={
        "symbol": "INFY",
        "strategy_id": "strat_orb",
        "days": 2,
        "initial_capital": 50000.0,
        "risk_per_trade_pct": 0.5
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["symbol"] == "INFY"
    assert "metrics" in data

