import os
from pathlib import Path
from dotenv import load_dotenv

# Find root directory (where .env lives)
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
dotenv_path = ROOT_DIR / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

# Microservice Ports
PORT_GATEWAY = int(os.getenv("PORT_GATEWAY", "5000"))
PORT_DATA = int(os.getenv("PORT_DATA", "5001"))
PORT_AGENTS = int(os.getenv("PORT_AGENTS", "5002"))
PORT_DECISION = int(os.getenv("PORT_DECISION", "5003"))
PORT_RISK = int(os.getenv("PORT_RISK", "5004"))
PORT_EXCHANGE = int(os.getenv("PORT_EXCHANGE", "5005"))
PORT_JOURNAL = int(os.getenv("PORT_JOURNAL", "5006"))
PORT_BACKTEST = int(os.getenv("PORT_BACKTEST", "5007"))
PORT_CHAOS = int(os.getenv("PORT_CHAOS", "5008"))

# Service Base URLs
URL_GATEWAY = f"http://localhost:{PORT_GATEWAY}"
URL_DATA = f"http://localhost:{PORT_DATA}"
URL_AGENTS = f"http://localhost:{PORT_AGENTS}"
URL_DECISION = f"http://localhost:{PORT_DECISION}"
URL_RISK = f"http://localhost:{PORT_RISK}"
URL_EXCHANGE = f"http://localhost:{PORT_EXCHANGE}"
URL_JOURNAL = f"http://localhost:{PORT_JOURNAL}"
URL_BACKTEST = f"http://localhost:{PORT_BACKTEST}"
URL_CHAOS = f"http://localhost:{PORT_CHAOS}"

# Data & Staleness Limits
DATA_MODE = os.getenv("DATA_MODE", "SIMULATED")
DEFAULT_SYMBOL = os.getenv("DEFAULT_SYMBOL", "RELIANCE.NS")
PRICE_STALENESS_SECONDS = int(os.getenv("PRICE_STALENESS_SECONDS", "60"))
NEWS_STALENESS_SECONDS = int(os.getenv("NEWS_STALENESS_SECONDS", "300"))

# Database Config
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "profitpilot")
MYSQL_DB = os.getenv("MYSQL_DB", "profitpilot")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/profitpilot")

# Security
RISK_TOKEN_SECRET = os.getenv("RISK_TOKEN_SECRET", "profitpilot-risk-secret-key-32bytes-auth")
JWT_SECRET = os.getenv("JWT_SECRET", "profitpilot-jwt-super-secret-key-2026")

# Risk Parameters
STARTING_CASH = float(os.getenv("STARTING_CASH", "100000.0"))
MAX_RISK_PER_TRADE_PCT = float(os.getenv("MAX_RISK_PER_TRADE_PCT", "1.0"))  # 1% equity at risk
DAILY_LOSS_LIMIT_PCT = float(os.getenv("DAILY_LOSS_LIMIT_PCT", "2.0"))      # 2% equity daily halt
DEFAULT_STOP_LOSS_PCT = float(os.getenv("DEFAULT_STOP_LOSS_PCT", "1.5"))    # 1.5% distance
MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "3"))
MAX_POSITION_VALUE_PCT = float(os.getenv("MAX_POSITION_VALUE_PCT", "30.0")) # 30% max exposure

# Market Execution Simulation
MAKER_FEE_PCT = float(os.getenv("MAKER_FEE_PCT", "0.03"))                  # 0.03%
SLIPPAGE_BPS = float(os.getenv("SLIPPAGE_BPS", "5.0"))                      # 5 bps

