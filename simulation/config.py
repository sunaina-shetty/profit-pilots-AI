import os
from pathlib import Path
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

# Brokerage & Regulatory Transaction Fees (Note: verify current rates)
BROKERAGE_PCT = 0.0003          # 0.03%
BROKERAGE_MAX = 20.0            # min(₹20, 0.03%)
STT_SELL_PCT = 0.00025          # 0.025% on sell turnover
EXCHANGE_TXN_PCT = 0.00003      # ~0.003% of turnover
GST_PCT = 0.18                  # 18% on (brokerage + exchange)
STAMP_DUTY_BUY_PCT = 0.00003    # 0.003% on buy turnover
TICK_SIZE = 0.05                # ₹0.05 tick size
SLIPPAGE_BPS = 0.0002           # 2 bps slippage on market fills

# Simulation Timings & Safety Rules
CANDLE_INTERVAL_REAL_SEC = 1.2  # 50x speed (60s / 50 = 1.2s per 1m candle)
MIN_START_TIME = "09:15"
MAX_END_TIME = "15:30"
ENTRY_START_TIME = "09:30"
ENTRY_END_TIME = "14:45"
SQUARE_OFF_TIME = "15:15"
TOTAL_DAY_CANDLES = 375         # 375 1-minute bars from 09:15 to 15:30 inclusive of bar starts

MAX_BUYS_PER_DAY = 5
DAILY_LOSS_LIMIT_PCT = 0.02     # 2% of initial amount
STOP_LOSS_COOLDOWN_MINUTES = 30 # 30 min cooldown after stop loss hit

# LLM Configuration
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_TIMEOUT = 20.0

