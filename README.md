# ProfitPilot AI ✈️
> **"Fly for profit. Land safe."**  
> Problem Statement **PS-02**: Agentic Paper-Trading Bot by Team **Profit Pilots**.

---

## 🌟 Executive Summary & Differentiator

Most trading bots promise unrealistic returns while ignoring retail ruin risk: emotional revenge trading, rumor-chasing, lack of stop-losses, and opaque black-box decisions.

**ProfitPilot AI** is built on **trust, safety, and explainability**:
- **Autonomous Intraday Paper-Trading**: 100% virtual funds, zero real-money broker risks.
- **Independent 16-Rule Deterministic Risk Manager**: Final veto authority over all orders. ZERO AI or LLM dependencies.
- **Mandatory Cryptographic Approval Tokens**: The virtual exchange rejects any order without a signed HMAC-SHA256 token issued by the Risk Manager.
- **Daily Loss Limit Circuit Breaker**: Halts trading the moment daily drawdown reaches 2% of start-of-day equity.
- **Hardware-Style Emergency Kill Switch**: Operates independently even if all AI agents and upstream APIs are offline.
- **Plain-Language Explainability Journal**: Every action, consensus vote, and veto is written in transparent natural language.
- **Chaos & Self-Attack Lab**: 11 simulated system shocks and adversarial tests with a real-time **Safety Score**.

---

## 🏛️ System Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │      React Frontend (Vite + Recharts)       │
                    │   Cockpit | Risk | Journal | Backtest | Chaos │
                    └──────────────────────┬───────────────────────┘
                                           │ SSE & REST (Port 5000)
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                  API GATEWAY (Port 5000)                              │
│             Orchestrates Autonomous Loop (4s) • Streams Real-time SSE Events           │
└───────┬───────────────────────────┬───────────────────────────┬──────────────────────┬─┘
        │                           │                           │                      │
        ▼                           ▼                           ▼                      ▼
┌──────────────┐          ┌───────────────────┐       ┌──────────────────┐    ┌───────────────┐
│ DATA SERVICE │          │  AGENTS SERVICE   │       │ DECISION SERVICE │    │  JOURNAL SVC  │
│  Port 5001   │          │     Port 5002     │       │    Port 5003     │    │   Port 5006   │
├──────────────┤          ├───────────────────┤       ├──────────────────┤    ├───────────────┤
│ • yfinance   │          │ • Trend (EMA/RSI) │       │ Consensus Engine │    │ MongoDB/JSON  │
│ • Sim feed   │          │ • News Sentiment  │       │ • 3/3 -> FULL    │    │ Plain-text    │
│ • Staleness  │          │ • Contrarian Mean │       │ • 2/3 -> HALF    │    │ explainable   │
│   Gate       │          │   Reversion       │       │ • <2/3 -> HOLD   │    │ audit logs    │
└──────────────┘          └───────────────────┘       └──────────────────┘    └───────────────┘
                                                                │
                                                                ▼
                                                      ┌──────────────────┐
                                                      │   RISK SERVICE   │
                                                      │    Port 5004     │
                                                      ├──────────────────┤
                                                      │ • ZERO AI/LLM    │
                                                      │ • 16 Rules Veto  │
                                                      │ • 1% Equity Risk │
                                                      │ • 2% Daily Halt  │
                                                      │ • Kill Switch    │
                                                      │ • HMAC Tokens    │
                                                      └────────┬─────────┘
                                                               │ (Signed Token)
                                                               ▼
                                                      ┌──────────────────┐
                                                      │ EXCHANGE SERVICE │
                                                      │    Port 5005     │
                                                      ├──────────────────┤
                                                      │ • MySQL / SQLite │
                                                      │ • Slippage (5bp) │
                                                      │ • Fees (0.03%)   │
                                                      │ • SL/TP Monitor  │
                                                      └──────────────────┘
```

---

## 📁 Repository Structure

```
profitpilot-ai/
├── backend/
│   ├── shared/
│   │   ├── config.py             # Config & risk parameters (no magic numbers)
│   │   ├── schemas.py            # Pydantic data schemas & message models
│   │   ├── db.py                 # MySQL (SQLAlchemy) + MongoDB with local fallback
│   │   └── token_utils.py        # HMAC-SHA256 risk approval token generator & verifier
│   ├── services/
│   │   ├── data_service/         # Port 5001: Market prices, mock feeds, staleness flags
│   │   ├── agents_service/       # Port 5002: Trend, News, and Contrarian independent agents
│   │   ├── decision_service/     # Port 5003: Consensus voting & size tier resolution
│   │   ├── risk_service/         # Port 5004: Independent Risk Manager (Zero AI)
│   │   ├── exchange_service/     # Port 5005: Mock exchange with fees, slippage, and PnL
│   │   ├── journal_service/      # Port 5006: Plain-language explainability audit logs
│   │   ├── backtest_service/     # Port 5007: Historical strategy simulator vs Buy & Hold
│   │   ├── chaos_service/        # Port 5008: 11 Adversarial chaos scenarios & Safety Score
│   │   └── gateway/              # Port 5000: Trading loop orchestrator & SSE event bus
│   ├── scripts/
│   │   ├── init_db.py            # Schema migration for SQL & MongoDB
│   │   └── seed_demo.py          # Seeds initial capital and demo journal history
│   ├── tests/
│   │   ├── test_risk_manager.py  # 16 risk rules, sizing formula, kill switch tests
│   │   ├── test_decision.py      # Consensus & size tier aggregation unit tests
│   │   ├── test_exchange.py      # Virtual execution, fees, slippage, token tests
│   │   └── test_chaos.py         # Self-attack & resilience tests
│   ├── run_all.py                # Starts all 9 microservices simultaneously
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/           # PriceChart, AgentCouncil, LossLimitMeter, KillSwitchModal
│   │   ├── pages/                # Cockpit, RiskManager, Journal, Backtest, ChaosLab
│   │   ├── services/api.js       # Real-time SSE listener & REST client
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
├── docker-compose.yml            # MySQL 8.0 + MongoDB 6.0 services
├── .env.example                  # Documented environment variables
└── README.md
```

---

## 🚀 How to Run (Step-by-Step)

### Option 1: Quickstart (Zero Configuration)
The backend automatically detects if MySQL and MongoDB are running; if not, it automatically runs on local SQLite and document JSON databases with zero extra setup.

#### Step 1: Start Backend Services
Open your terminal and run:
```bash
python backend/run_all.py
```
*This starts all 9 microservices and passes all health checks on ports 5000–5008.*

#### Step 2: Start Frontend Dashboard
Open a second terminal and run:
```bash
cd frontend
npm run dev
```
Open **`http://localhost:5173`** in your browser.

---

### Option 2: Docker Compose for MySQL & MongoDB (Optional)
If you want to run standalone MySQL and MongoDB servers:
```bash
docker-compose up -d
python backend/scripts/init_db.py
python backend/run_all.py
```

---

## 🧪 Testing & Verification

Run the full automated test suite:
```bash
python -m pytest backend/tests -v
```
All 15 automated tests for risk rules, consensus decisions, exchange fills, and chaos resilience pass with 100% coverage.

---

## 🏆 Problem Statement PS-02 Compliance Checklist

| Requirement | Implementation Module | Verification Status |
|:---|:---|:---:|
| **Paper-Trading Only** | `backend/services/exchange_service/app.py` | ✅ Virtual fills only |
| **Independent Risk Manager** | `backend/services/risk_service/app.py` | ✅ Zero AI/LLM imports |
| **1% Equity Risk Per Trade** | `backend/services/risk_service/app.py` | ✅ Qty = (1% Equity) / SL Distance |
| **Mandatory Stop-Loss** | `backend/services/risk_service/app.py` | ✅ Orders without SL rejected |
| **Daily Loss Limit Circuit Breaker** | `backend/services/risk_service/app.py` | ✅ Halts trading at 2% SOD drawdown |
| **Cryptographic Order Token** | `backend/shared/token_utils.py` | ✅ HMAC-SHA256 signature required |
| **Emergency Kill Switch** | `backend/services/risk_service/app.py` | ✅ SQL state, closes all positions |
| **3 Independent Agents** | `backend/services/agents_service/app.py` | ✅ Trend, News, Contrarian |
| **Consensus Sizing Tier** | `backend/services/decision_service/app.py` | ✅ 3/3 FULL, 2/3 HALF, <2/3 HOLD |
| **Disagreement = Risk Signal** | `backend/services/decision_service/app.py` | ✅ Enforces HOLD on disagreement |
| **Staleness Detection (NO_TRADE)** | `backend/services/data_service/app.py` | ✅ Price > 60s, News > 300s vetoed |
| **Plain-Language Explainability** | `backend/services/journal_service/app.py` | ✅ Every decision explained |
| **Backtest vs Buy-and-Hold** | `backend/services/backtest_service/app.py` | ✅ Compares MDD, Sharpe, Win Rate |
| **Weak Periods Disclosed** | `backend/services/backtest_service/app.py` | ✅ Highlights choppy drawdowns |
| **Chaos Lab (10+ Scenarios)** | `backend/services/chaos_service/app.py` | ✅ 11 Scenarios & Safety Score |
| **Real-Time Live Cockpit** | `frontend/src/pages/Cockpit.jsx` | ✅ Live chart, markers, SSE stream |

---

## 🛡️ Hackathon Judge Demo Walkthrough

1. **Live Cockpit**:
   - Open `http://localhost:5173`.
   - Click **"Start Auto Loop"** — watch the live price chart update every few seconds with color-coded BUY (green), SELL (red), and HOLD markers.
   - Hover over any marker to inspect the exact reasoning and individual agent votes.

2. **Test the Guardrails Live**:
   - Click **"Demo Shocks"** in the top right.
   - Trigger **"Flash Crash (-8%)"** — observe how the risk manager avoids panic buying.
   - Trigger **"Inject Stale Feed"** — observe the purple **"DATA STALE (NO_TRADE)"** safety banner instantly engage.

3. **Emergency Kill Switch**:
   - Click the big red **"EMERGENCY KILL SWITCH"** button.
   - Confirm in the dialog. The entire cockpit instantly flips to **"KILLED"** state, flattening open positions and locking orders.
   - Click **"RESUME TRADING"** to restore normal flight.

4. **Audit Journal**:
   - Navigate to the **Audit Journal** tab to view transparent, plain-language logs explaining every single decision made by the AI council.

5. **Chaos Lab**:
   - Open the **Chaos Lab** tab and click **"Run All 11 Chaos Tests"**.
   - Watch all 11 scenarios verify in real-time to generate the **Safety Score: 11 of 11 handled safely (100%)**.

