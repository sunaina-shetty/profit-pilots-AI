"""All tunable numbers for the demo live here, so judges' questions like
"what's your stop-loss?" have one place to point to."""

SYMBOL = "DEMO"
STARTING_CASH = 100_000.0          # virtual money only

# Risk manager (rules only, no AI)
RISK_PER_TRADE = 0.01              # risk 1% of equity per trade
STOP_LOSS_PCT = 0.04               # stop placed 4% below entry
MAX_POSITION_PCT = 0.30            # never hold more than 30% of equity in one position
DAILY_LOSS_LIMIT_PCT = 0.03        # halt new entries after a 3% drawdown in the session
CIRCUIT_BREAKER_MOVE = 0.05        # a single-tick move bigger than 5% = abnormal market
COOLDOWN_TICKS = 5                 # no new entries for this many ticks after an abnormal move

# Mock exchange
FEE_PCT = 0.0005                   # 0.05% brokerage per fill
SLIPPAGE_PCT = 0.0005              # 0.05% slippage per fill

# Data validation
STALE_AFTER_SECONDS = 60           # price older than this = no trade
TRUSTED_SOURCES = {"Reuters", "Bloomberg", "Mint", "Economic Times", "Business Standard"}

# Engine
WARMUP_TICKS = 35                  # history needed before agents can compute indicators
NEWS_WINDOW_TICKS = 15             # how far back the news agent looks
