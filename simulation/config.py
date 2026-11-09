import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Top ~15 Popular NSE Stocks with company search queries
POPULAR_NSE_STOCKS = [
    {"symbol": "TCS.NS", "name": "Tata Consultancy Services", "display": "TCS (Tata Consultancy Services)"},
    {"symbol": "RELIANCE.NS", "name": "Reliance Industries", "display": "RELIANCE (Reliance Industries)"},
    {"symbol": "INFY.NS", "name": "Infosys", "display": "INFY (Infosys)"},
    {"symbol": "HDFCBANK.NS", "name": "HDFC Bank", "display": "HDFCBANK (HDFC Bank)"},
    {"symbol": "ICICIBANK.NS", "name": "ICICI Bank", "display": "ICICIBANK (ICICI Bank)"},
    {"symbol": "SBIN.NS", "name": "State Bank of India", "display": "SBIN (State Bank of India)"},
    {"symbol": "BHARTIARTL.NS", "name": "Bharti Airtel", "display": "BHARTIARTL (Bharti Airtel)"},
    {"symbol": "ITC.NS", "name": "ITC Limited", "display": "ITC (ITC Limited)"},
    {"symbol": "KOTAKBANK.NS", "name": "Kotak Mahindra Bank", "display": "KOTAKBANK (Kotak Mahindra Bank)"},
    {"symbol": "LT.NS", "name": "Larsen & Toubro", "display": "LT (Larsen & Toubro)"},
    {"symbol": "HINDUNILVR.NS", "name": "Hindustan Unilever", "display": "HINDUNILVR (Hindustan Unilever)"},
    {"symbol": "AXISBANK.NS", "name": "Axis Bank", "display": "AXISBANK (Axis Bank)"},
    {"symbol": "TATAMOTORS.NS", "name": "Tata Motors", "display": "TATAMOTORS (Tata Motors)"},
    {"symbol": "MARUTI.NS", "name": "Maruti Suzuki", "display": "MARUTI (Maruti Suzuki)"},
    {"symbol": "SUNPHARMA.NS", "name": "Sun Pharma", "display": "SUNPHARMA (Sun Pharma)"}
]

# ─────────────────────────────────────────────────────────────────────────────
# UNIFIED TRADING CONFIGURATION
# All tunables in ONE config object with optional per-symbol overrides.
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TradingConfig:
    # --- Agent 1: ORB Settings ---
    orb_bars_count: int = 3                # First 3 five-minute bars (first 15 mins: 09:15-09:30)
    orb_min_range_pct: float = 0.001       # Minimum range guardrail (0.1% of price)
    orb_entry_window_start: str = "09:30"  # ORB evaluation starts after range forms
    orb_entry_window_end: str = "14:45"

    # --- Agent 2: News Settings ---
    news_buy_veto_threshold: float = -0.50   # Veto BUY if news sentiment < -0.50
    news_short_veto_threshold: float = 0.50  # Veto SHORT if news sentiment > +0.50

    # --- Agent 3: VWAP Reversion Settings ---
    vwap_min_bars: int = 14                # Skip if fewer than 14 bars exist
    vwap_sigma_multiplier: float = 2.0     # Normalization factor (z / 2)
    vwap_act_sigma_threshold: float = 1.0  # Act from ~1 sigma
    vwap_rsi_period: int = 14
    vwap_rsi_oversold: float = 35.0        # RSI < 35 -> +0.2 boost
    vwap_rsi_overbought: float = 65.0      # RSI > 65 -> -0.2 drag

    # --- Council Consensus Gate Settings ---
    # Regime-aware weights:
    weights_trend: Dict[str, float] = field(default_factory=lambda: {"orb": 0.50, "news": 0.30, "vwap": 0.20})
    weights_range: Dict[str, float] = field(default_factory=lambda: {"orb": 0.20, "news": 0.30, "vwap": 0.50})
    weights_unclear: Dict[str, float] = field(default_factory=lambda: {"orb": 0.35, "news": 0.30, "vwap": 0.35})

    buy_trigger_score: float = 0.15        # BUY if S >= 0.15 and confidence >= 40
    sell_trigger_score: float = -0.15      # SELL if S <= -0.15 and confidence >= 40
    min_confidence: float = 40.0           # Minimum confidence % to trigger entry
    exit_flip_min_confidence: float = 50.0 # Exit open position if council flips with conf >= 50

    # --- Risk & Position Sizing ---
    risk_per_trade_pct: float = 0.005      # 0.5% of current capital per trade
    max_capital_per_position_pct: float = 0.50 # Capped at 50% capital per position
    atr_stop_multiplier: float = 1.5       # Volatility-adaptive stop: 1.5x ATR(14)
    min_stop_pct: float = 0.003            # Minimum stop distance (0.3%)
    max_stop_pct: float = 0.010            # 1% stop-loss guardrail cap
    fallback_stop_pct: float = 0.007       # Fallback 0.7% if ATR unavailable
    take_profit_r_multiple: float = 1.5    # Take-profit at 1.5R
    breakeven_r_multiple: float = 1.0      # Stop moved to breakeven after +1R
    cooldown_bars: int = 3                 # 3-bar cooldown between trades / stops
    max_trades_per_day: int = 6            # Max 6 trades per day
    daily_loss_limit_pct: float = 0.02     # Hard circuit breaker at -2% starting capital
    cost_filter_multiplier: float = 1.5    # Expected gain >= 1.5x round-trip fees (reduced from 3x)

    # --- Timings ---
    min_start_time: str = "09:15"
    max_end_time: str = "15:30"
    entry_start_time: str = "09:30"
    entry_end_time: str = "14:45"
    square_off_time: str = "15:15"
    candle_interval_real_sec: float = 1.2
    total_day_candles: int = 375

    # --- Default Per-Symbol / Per-Exchange Market Properties ---
    currency: str = "INR"
    tick_size: float = 0.05
    lot_size: int = 1
    slippage_bps: float = 0.0002           # 2 bps slippage on market fills

    # --- Fee Model ---
    brokerage_pct: float = 0.0003          # 0.03%
    brokerage_max: float = 20.0            # ₹20 cap
    stt_sell_pct: float = 0.00025          # 0.025% on sell turnover
    exchange_txn_pct: float = 0.00003      # 0.003% of turnover
    gst_pct: float = 0.18                  # 18% on (brokerage + exchange)
    stamp_duty_buy_pct: float = 0.00003    # 0.003% on buy turnover

    # --- Optional Per-Symbol Overrides ---
    per_symbol_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def get_symbol_param(self, symbol: str, param_name: str) -> Any:
        sym_clean = symbol.upper().replace(".NS", "")
        for sym_key in (symbol, f"{sym_clean}.NS", sym_clean):
            if sym_key in self.per_symbol_overrides:
                if param_name in self.per_symbol_overrides[sym_key]:
                    return self.per_symbol_overrides[sym_key][param_name]
        return getattr(self, param_name)

# Global default config instance
DEFAULT_CONFIG = TradingConfig(
    per_symbol_overrides={
        # Example overrides for specific instruments
        "MRF.NS": {"tick_size": 0.05, "lot_size": 1},
        "RELIANCE.NS": {"tick_size": 0.05},
    }
)

# ─────────────────────────────────────────────────────────────────────────────
# BACKWARD COMPATIBILITY EXPORTS (used across existing engine/broker imports)
# ─────────────────────────────────────────────────────────────────────────────
BROKERAGE_PCT = DEFAULT_CONFIG.brokerage_pct
BROKERAGE_MAX = DEFAULT_CONFIG.brokerage_max
STT_SELL_PCT = DEFAULT_CONFIG.stt_sell_pct
EXCHANGE_TXN_PCT = DEFAULT_CONFIG.exchange_txn_pct
GST_PCT = DEFAULT_CONFIG.gst_pct
STAMP_DUTY_BUY_PCT = DEFAULT_CONFIG.stamp_duty_buy_pct
TICK_SIZE = DEFAULT_CONFIG.tick_size
SLIPPAGE_BPS = DEFAULT_CONFIG.slippage_bps

CANDLE_INTERVAL_REAL_SEC = DEFAULT_CONFIG.candle_interval_real_sec
MIN_START_TIME = DEFAULT_CONFIG.min_start_time
MAX_END_TIME = DEFAULT_CONFIG.max_end_time
ENTRY_START_TIME = DEFAULT_CONFIG.entry_start_time
ENTRY_END_TIME = DEFAULT_CONFIG.entry_end_time
SQUARE_OFF_TIME = DEFAULT_CONFIG.square_off_time
TOTAL_DAY_CANDLES = DEFAULT_CONFIG.total_day_candles

MAX_BUYS_PER_DAY = DEFAULT_CONFIG.max_trades_per_day
DAILY_LOSS_LIMIT_PCT = DEFAULT_CONFIG.daily_loss_limit_pct
STOP_LOSS_COOLDOWN_MINUTES = DEFAULT_CONFIG.cooldown_bars * 5  # in minutes for 5m bars

ORB_IN_PLAY_VOLUME_MULTIPLIER = float(os.getenv("ORB_IN_PLAY_VOLUME_MULTIPLIER", "1.0" if os.getenv("OFFLINE", "0") == "1" else "1.5"))
ORB_ENTRY_WINDOW_END = DEFAULT_CONFIG.orb_entry_window_end
ORB_TRAILING_ATR_MULTIPLIER = DEFAULT_CONFIG.atr_stop_multiplier

# LLM Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_TIMEOUT = 20.0
