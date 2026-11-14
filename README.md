# ProfitPilot AI ✈️
> **Groww-Inspired Multi-Agent Algorithmic Trading Terminal**  
> Problem Statement Institutional Multi-Agent Intraday Algorithmic Trading Terminal.

---

## 🌟 Overview & Key Features

**ProfitPilot AI** transforms intraday equity trading into an institutional-grade, Groww-inspired multi-agent trading terminal. It pairs **10 configurable quantitative technical trading strategies**, **dynamic multi-agent coordination**, **real-time news intelligence with tail-risk vetoes**, **deterministic volatility-adaptive risk management**, and a **TradingView Lightweight Candlestick Chart**.

---

### Core Architectural Pillars

```
                               ┌──────────────────────────────────────────────┐
                               │       NSE 5-Minute Candle Stream & News      │
                               └──────────────────────┬───────────────────────┘
                                                      │
                     ┌────────────────────────────────┼───────────────────────────────┐
                     ▼                                ▼                               ▼
       ┌───────────────────────────┐    ┌───────────────────────────┐   ┌───────────────────────────┐
       │   AGENT 1 (Trend/Break)   │    │  AGENT 2 (News Intel)     │   │ AGENT 3 (Mean Reversion)  │
       │ Configurable (10 Strats)  │    │ 6 Sentiment Classes, Veto │   │ Configurable (10 Strats)  │
       └─────────────┬─────────────┘    └─────────────┬─────────────┘   └─────────────┬─────────────┘
                     │                                │                               │
                     └────────────────────────────────┼───────────────────────────────┘
                                                      │
                                                      ▼
                                       ┌─────────────────────────────┐
                                       │   COUNCIL CONSENSUS GATE    │
                                       │ Weighted Scoring + Regimes  │
                                       └──────────────┬──────────────┘
                                                      │
                                                      ▼
                                       ┌─────────────────────────────┐
                                       │    RISK MANAGER & BROKER    │
                                       │ 0.5% Risk Sizing, ATR Stops │
                                       └──────────────┬──────────────┘
                                                      │
                                                      ▼
                                       ┌─────────────────────────────┐
                                       │  GROWW TRADING TERMINAL UI  │
                                       │ Charts, Ledger, Backtesting │
                                       └─────────────────────────────┘
```

#### 1. Groww-Inspired Terminal UI & Navigation
- **Top Market Information Bar**: Live tracking for **NIFTY 50**, **SENSEX**, **BANK NIFTY**, **Crude Oil**, and **Natural Gas** with real-time percentage badges.
- **Stock Quote HUD**: Displays Stock Name, NSE Symbol, Current LTP, Daily Change %, Day High, Day Low, Previous Close, Volume, and Market Session Status. Shows `DATA UNAVAILABLE` badge when offline.
- **Global Search**: Typeahead search over popular NSE stocks (TCS, RELIANCE, INFY, HDFCBANK, ICICIBANK, TATAMOTORS, etc.).
- **TradingView Candlestick Chart**: Slim 5-minute green/red candles, thin wicks, floating quick Buy/Sell badges (`[₹... SELL] 1.70 [₹... BUY]`), VWAP line, Today's High/Low (ORB lines), active stop-loss line, and interactive BUY/SELL arrows.
- **Navigation Tabs**:
  1. `Dashboard`: High-level executive overview with metrics, agent matrix, and quick launch buttons.
  2. `Markets`: Major Indian indices, sector heatmaps, and tradable NSE universe.
  3. `Trading Terminal`: Interactive candlestick chart, replay controls, agent consensus cards, and right dock.
  4. `Strategy Library`: Deep-dive catalog into all 10 quantitative strategies.
  5. `Agent Configuration`: Dynamic strategy assignment for Agent 1 and Agent 3 with JSON persistence.
  6. `Portfolio`: Complete ledger breakdown, cash vs equity, charges, and open positions.
  7. `Trade History`: Detailed execution logs with fill prices, timestamps, and fees.
  8. `Signal Inspector`: Click-to-inspect trade decisions, agent rationale, and facts.
  9. `Risk Management`: Stop-loss limits, ATR multiplier, maximum daily loss circuit breaker.
  10. `News Intelligence`: Real-time financial headlines, sentiment scoring, and tail-risk vetoes.
  11. `Backtesting`: Out-of-sample chronological multi-day backtesting lab with fee modeling.
  12. `Settings`: Terminal preferences, execution modes (Paper vs Live Broker), and credential management.

---

### 2. Ten Quantitative Technical Trading Strategies

Every strategy implements a unified object-oriented contract (`BaseStrategy`) with zero look-ahead bias:

| # | Strategy Name | Category | Indicators Used | Core Long Entry Condition |
|---|---------------|----------|-----------------|---------------------------|
| 1 | **EMA 9/21 + RSI + Volume** | Trend Following | EMA 9, EMA 21, RSI 14, Vol SMA 20 | EMA 9 crosses above EMA 21, RSI > 50, Volume > 1.2x SMA |
| 2 | **Supertrend + EMA 200** | Trend Following | Supertrend (10,3), EMA 200 | Supertrend turns bullish and Price > EMA 200 |
| 3 | **VWAP + EMA Pullback** | Trend / Pullback | VWAP, EMA 9, EMA 21 | Price > VWAP, EMA 9 > EMA 21, price tests EMA zone with bullish close |
| 4 | **Opening Range Breakout (ORB)** | Breakout | 15-min High/Low (09:15-09:30), VWAP | 5m candle closes above 15m ORB High after 09:30 IST with Price > VWAP |
| 5 | **MACD + RSI + EMA 200** | Momentum | MACD (12,26,9), RSI 14, EMA 200 | MACD line crosses above Signal, RSI > 50, Price > EMA 200 |
| 6 | **Bollinger Bands + RSI Reversal** | Mean Reversion | Bollinger Bands (20,2), RSI 14 | Price touches lower band, RSI < 30, followed by green reversal bar |
| 7 | **ADX + DI + EMA 200** | Trend Strength / Regime | ADX 14, +DI, -DI, EMA 200 | ADX > 22, +DI > -DI, Price > EMA 200 (also acts as market regime classifier) |
| 8 | **RSI Divergence + EMA Cross** | Reversal | Swing Lows/Highs, RSI 14, EMA 9/21 | Price makes lower swing low while RSI makes higher swing low |
| 9 | **Donchian Breakout + EMA 200** | Breakout | 20-bar Donchian Channel, EMA 200 | Candle closes above 20-bar Donchian High with Price > EMA 200 |
| 10 | **Stochastic + EMA 50/200** | Momentum Pullback | Stochastic (14,3,3), EMA 50, EMA 200 | EMA 50 > EMA 200, %K crosses above %D from oversold territory (< 20) |

---

### 3. Agent Architecture & Council Consensus Gate

- **Agent 1 (Trend / Breakout)**: Evaluates user-assigned trend/breakout strategy from registry.
- **Agent 2 (News Intelligence)**: Ingests financial headlines across 6 event classifications:
  `POSITIVE` | `NEUTRAL` | `NEGATIVE` | `HIGH VOLATILITY` | `CRITICAL EVENT` | `INSUFFICIENT DATA`
  *Maintains independent veto authority over new long entries during high volatility or negative news.*
- **Agent 3 (Mean Reversion / Reversal)**: Evaluates user-assigned mean reversion strategy.
- **Council Consensus Gate**:
  Continuous graded scoring: $S = w_1 S_{A1} + w_2 S_{News} + w_3 S_{A3}$.
  Adapts dynamically to market regime (`TRENDING`, `RANGING`, `HIGH_VOLATILITY`, `UNCLEAR`).
  Enforces cost filters, consecutive loss limits, cooldown periods, and execution hurdles.

---

### 4. Institutional Risk Management & Dual-Mode Kill Switch

- **Position Sizing**: Volatility-adaptive risk model:
  $$\text{Quantity} = \left\lfloor \frac{\text{Capital} \times 0.5\%}{\max(0.5, \text{Stop Distance})} \right\rfloor$$
- **Stop-Loss & Take-Profit**: Dynamic $1.5 \times \text{ATR}(14)$ stop distance, fixed $1.5R$ take-profit target, and automatic breakeven stop adjustment at $+1.0R$.
- **Circuit Breakers**: Hard daily stop at $-2.0\%$ of starting capital and mandatory $15:15$ IST intraday square-off.
- **Emergency Kill Switch**:
  - **Mode A (Stop New Trades)**: Suspends all new signal evaluations while continuing to manage active open positions to stop-loss or take-profit.
  - **Mode B (Emergency Flatten)**: Instantly liquidates all open positions at market, cancels pending orders, and completely halts simulation.

---

### 5. Quantitative Backtesting Lab

Run chronological out-of-sample backtests for any of the 10 strategies:
- **Inputs**: Stock Symbol, Strategy ID, Historical Period (2 to 20 days), Capital, Risk %, Stop-Loss %, Target R.
- **Outputs**:
  - Net Profit & ROI %
  - Win Rate % (Winning vs Losing Trades)
  - Profit Factor (Gross Gains / Gross Losses)
  - Maximum Drawdown % (Peak to Trough)
  - Annualized Sharpe Ratio
  - Total Regulatory Fees (STT, GST, Exchange charges, Stamp Duty, Brokerage)
  - Interactive Equity Curve Chart & Completed Trade Execution Ledger

---

## 🚀 How to Run the Application

### Option 1: Unified Production Mode (Recommended — 1 Command)
The Flask backend directly serves the pre-compiled Groww terminal assets and API together on port `5000`:

```bash
# Terminal 1
python app.py
```
Open **`http://localhost:5000`** in your browser.

---

### Option 2: Development Mode (Vite Live Reload)

```bash
# Terminal 1: Backend API
python app.py

# Terminal 2: Vite Dev Server
cd frontend
npm run dev
```
Open **`http://localhost:5173`** in your browser.  
*(Press `Ctrl + F5` to clear browser caches if needed).*

---

## 🧪 Automated Test Suite

All 65 tests are automated across 6 test suites:

```bash
python -m pytest tests/
```

- `tests/test_strategies.py`: 11 tests verifying all 10 quantitative strategy modules.
- `tests/test_backtest.py`: 4 tests for the multi-day backtesting engine and quote APIs.
- `tests/test_api_endpoints.py`: 4 tests covering configuration, strategy catalogs, and indices.
- `tests/test_simulator.py`: 30 tests covering broker book reconciliation, fees, and engine replay.
- `tests/test_blank_chart_fix.py`: 8 tests verifying candle schema, timestamp ordering, and chart loading.
- `tests/test_multi_agent_visualization.py`: 8 tests verifying signal rendering, Council consensus, and journal generation.

---

## 📡 API Reference

- `GET /api/stocks`: List of supported NSE stocks.
- `GET /api/stock-quote?symbol=TCS`: Detailed stock metrics (LTP, change, day high/low, volume).
- `GET /api/candles?symbol=TCS&date=YYYY-MM-DD`: 5-minute candles with VWAP and ORB lines.
- `POST /api/start`: Start real-time simulation session.
- `POST /api/kill`: Dual-mode emergency kill switch (`mode="stop_new"|"flatten"`).
- `GET /api/state`: Current engine state snapshot.
- `GET /api/stream`: Server-Sent Events (SSE) live simulation stream.
- `GET /api/strategies`: Catalog of all 10 technical strategies.
- `GET /api/agent-config`: Current persisted Agent 1 & Agent 3 configuration.
- `POST /api/agent-config`: Update strategy assignments and parameters.
- `POST /api/agent-config/reset`: Reset configurations to factory defaults.
- `POST /api/backtest`: Execute chronological multi-day strategy backtest.
- `GET /api/market-indices`: Live Indian market benchmark indices.

---

## 🔒 Safety & Compliance Notice

- Default mode is **Paper Trading** with virtual capital.
- Real regulatory cost model includes STT (0.025% on sell), Brokerage (₹20 or 0.05%), Exchange turnover fees (0.00345%), GST (18%), and Stamp Duty (0.003% on buy).
- Live broker trading is intentionally guarded and requires explicit API credentials (API key, secret, and TOTP authentication).
