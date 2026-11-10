"""
agent_config.py — Persistent Agent & Strategy Configuration Manager for ProfitPilot AI.
Persists manual strategy selections, custom parameters, weights, and risk settings to JSON.
"""
import os
import json
import threading
from pathlib import Path
from typing import Dict, Any, Optional
from simulation.strategies.registry import STRATEGY_CLASSES, list_all_strategies

CONFIG_FILE_PATH = Path(__file__).resolve().parent / "agent_config.json"
_CONFIG_LOCK = threading.Lock()

DEFAULT_AGENT_CONFIG: Dict[str, Any] = {
    "agent1": {
        "id": "agent1",
        "name": "Agent 1 — Trend & Breakout",
        "strategy_id": "strat_orb",
        "strategy_name": "Opening Range Breakout (ORB)",
        "enabled": True,
        "weight": 0.35,
        "params": {
            "range_bars": 3,
            "entry_window_end": "14:45",
            "trailing_atr_multiplier": 1.5
        }
    },
    "agent2": {
        "id": "agent2",
        "name": "Agent 2 — News Intelligence",
        "enabled": True,
        "use_moneycontrol": True,
        "weight": 0.30,
        "negative_veto_threshold": -0.50,
        "short_veto_threshold": 0.50,
        "sentiment_sensitivity": 1.0,
        "veto_on_critical_event": True
    },
    "agent3": {
        "id": "agent3",
        "name": "Agent 3 — Mean Reversion & Reversal",
        "strategy_id": "strat_bb_rsi_reversal",
        "strategy_name": "Bollinger Bands (20,2) + RSI Reversal",
        "enabled": True,
        "weight": 0.35,
        "params": {
            "rsi_oversold": 35.0,
            "rsi_overbought": 65.0,
            "pct_b_threshold": 0.15,
            "min_bars": 8
        }
    },
    "council": {
        "buy_trigger_score": 0.15,
        "sell_trigger_score": -0.15,
        "min_confidence": 40.0,
        "regime_adaptive_weights": True
    },
    "risk": {
        "risk_per_trade_pct": 0.5,
        "atr_stop_multiplier": 1.5,
        "target_r_multiple": 1.5,
        "daily_loss_limit_pct": 2.0,
        "max_trades_per_day": 6,
        "paper_trading_capital": 100000.0,
        "cooldown_bars": 3
    }
}

class AgentConfigManager:
    def __init__(self, filepath: Path = CONFIG_FILE_PATH):
        self.filepath = filepath
        self.config: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        with _CONFIG_LOCK:
            if self.filepath.exists():
                try:
                    with open(self.filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Deep merge with defaults to ensure missing keys are populated
                        merged = {**DEFAULT_AGENT_CONFIG}
                        for k, v in data.items():
                            if isinstance(v, dict) and k in merged:
                                merged[k] = {**merged[k], **v}
                            else:
                                merged[k] = v
                        return merged
                except Exception:
                    pass
            # Write defaults
            self._save_raw(DEFAULT_AGENT_CONFIG)
            return {**DEFAULT_AGENT_CONFIG}

    def _save_raw(self, data: Dict[str, Any]) -> None:
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[AgentConfigManager] Failed to write config: {e}")

    def get_config(self) -> Dict[str, Any]:
        with _CONFIG_LOCK:
            return json.loads(json.dumps(self.config))

    def update_config(self, patch: Dict[str, Any]) -> Dict[str, Any]:
        with _CONFIG_LOCK:
            for section, values in patch.items():
                if section in self.config and isinstance(values, dict):
                    self.config[section].update(values)
                else:
                    self.config[section] = values

            # Keep strategy_name in sync with strategy_id
            strat_catalog = {s["id"]: s["name"] for s in list_all_strategies()}
            if "strategy_id" in self.config.get("agent1", {}):
                sid = self.config["agent1"]["strategy_id"]
                self.config["agent1"]["strategy_name"] = strat_catalog.get(sid, sid)
            if "strategy_id" in self.config.get("agent3", {}):
                sid = self.config["agent3"]["strategy_id"]
                self.config["agent3"]["strategy_name"] = strat_catalog.get(sid, sid)

            self._save_raw(self.config)
            return json.loads(json.dumps(self.config))

    def reset_defaults(self) -> Dict[str, Any]:
        with _CONFIG_LOCK:
            self.config = {**DEFAULT_AGENT_CONFIG}
            self._save_raw(self.config)
            return json.loads(json.dumps(self.config))

# Global manager instance
agent_config_manager = AgentConfigManager()

