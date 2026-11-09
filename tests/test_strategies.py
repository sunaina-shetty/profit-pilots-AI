"""
test_strategies.py — Comprehensive unit tests for all 10 trading strategies in ProfitPilot AI.
"""
import pytest
from simulation.strategies.registry import STRATEGY_CLASSES, list_all_strategies, get_strategy

SAMPLE_CANDLES = [
    {"time": "09:15", "open": 2500.0, "high": 2510.0, "low": 2495.0, "close": 2505.0, "volume": 10000},
    {"time": "09:20", "open": 2505.0, "high": 2515.0, "low": 2500.0, "close": 2512.0, "volume": 12000},
    {"time": "09:25", "open": 2512.0, "high": 2520.0, "low": 2508.0, "close": 2518.0, "volume": 15000},
    {"time": "09:30", "open": 2518.0, "high": 2525.0, "low": 2515.0, "close": 2522.0, "volume": 18000},
    {"time": "09:35", "open": 2522.0, "high": 2530.0, "low": 2520.0, "close": 2528.0, "volume": 20000},
    {"time": "09:40", "open": 2528.0, "high": 2535.0, "low": 2525.0, "close": 2532.0, "volume": 22000},
    {"time": "09:45", "open": 2532.0, "high": 2540.0, "low": 2530.0, "close": 2538.0, "volume": 25000},
    {"time": "09:50", "open": 2538.0, "high": 2542.0, "low": 2535.0, "close": 2540.0, "volume": 21000},
    {"time": "09:55", "open": 2540.0, "high": 2545.0, "low": 2538.0, "close": 2543.0, "volume": 23000},
    {"time": "10:00", "open": 2543.0, "high": 2548.0, "low": 2540.0, "close": 2545.0, "volume": 24000},
]

SAMPLE_INDICATORS = {
    "price": 2545.0,
    "ema9": 2535.0,
    "ema21": 2520.0,
    "ema50": 2510.0,
    "ema200": 2480.0,
    "rsi": 62.5,
    "atr": 7.5,
    "vwap": 2525.0,
    "pct_b": 0.72,
    "bb_upper": 2555.0,
    "bb_lower": 2495.0,
    "bb_mid": 2525.0,
    "supertrend": 2515.0,
    "supertrend_dir": 1,
    "macd_line": 5.2,
    "macd_signal": 3.8,
    "macd_hist": 1.4,
    "donchian_upper": 2548.0,
    "donchian_lower": 2495.0,
    "donchian_mid": 2521.5,
    "stoch_k": 72.0,
    "stoch_d": 68.0,
    "volume_sma": 18000.0,
    "adx": 28.5,
    "pdi": 32.0,
    "mdi": 14.0,
    "vwap_sigma": 8.5,
}

def test_registry_contains_all_10_strategies():
    strategies = list_all_strategies()
    assert len(strategies) == 10
    expected_ids = {
        "strat_ema_rsi_vol",
        "strat_supertrend_ema200",
        "strat_vwap_pullback",
        "strat_orb",
        "strat_macd_rsi_ema200",
        "strat_bb_rsi_reversal",
        "strat_adx_di_regime",
        "strat_rsi_divergence",
        "strat_donchian_breakout",
        "strat_stochastic_ema",
    }
    registered_ids = {s["id"] for s in strategies}
    assert registered_ids == expected_ids

@pytest.mark.parametrize("strat_id", list(STRATEGY_CLASSES.keys()))
def test_all_10_strategies_evaluate_contract(strat_id):
    strat = get_strategy(strat_id)
    assert strat is not None
    assert strat.id == strat_id

    # 1. Evaluate with empty candles
    res_empty = strat.evaluate([], SAMPLE_INDICATORS)
    assert "score" in res_empty
    assert "confidence" in res_empty
    assert "signal" in res_empty
    assert "reason" in res_empty
    assert "facts" in res_empty
    assert res_empty["signal"] == "HOLD"

    # 2. Evaluate with candles in flat state (is_holding=False)
    res_flat = strat.evaluate(SAMPLE_CANDLES, SAMPLE_INDICATORS, is_holding=False)
    assert -1.0 <= res_flat["score"] <= 1.0
    assert 0.0 <= res_flat["confidence"] <= 100.0
    assert res_flat["signal"] in ("BUY", "SELL", "HOLD", "VETO_TREND")
    assert isinstance(res_flat["reason"], str) and len(res_flat["reason"]) > 0

    # 3. Evaluate with candles in active LONG state (is_holding=True)
    res_holding = strat.evaluate(
        SAMPLE_CANDLES, SAMPLE_INDICATORS, is_holding=True, position_side="LONG", entry_price=2510.0
    )
    assert -1.0 <= res_holding["score"] <= 1.0
    assert 0.0 <= res_holding["confidence"] <= 100.0
    assert res_holding["signal"] in ("BUY", "SELL", "HOLD")

