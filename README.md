<<<<<<< HEAD
# ProfitPilot AI: working demo

Agentic paper-trading bot. Virtual money only; no real orders are ever placed.

## Run it

Terminal 1 (backend, Flask on port 5000):

    cd backend
    python -m venv venv
    venv\Scripts\activate        # Windows  (macOS/Linux: source venv/bin/activate)
    pip install -r requirements.txt
    python app.py

Terminal 2 (frontend, React + Vite on port 5173):

    cd frontend
    npm install
    npm run dev

Open http://localhost:5173. Vite forwards every /api call to Flask.

## Use real prices instead of the synthetic replay (optional)

    cd backend
    pip install yfinance
    python fetch_data.py INFY.NS

Restart app.py. The synthetic replay is recommended for judging because the story is the same every time.

## Where things live

| Deck step | File |
|---|---|
| 1. Live data + news | backend/engine/data_feed.py |
| 2. Validate (fresh? trusted?) | backend/engine/agents.py → validate() |
| 3. Trend, News, Contrarian agents | backend/engine/agents.py |
| 4. Decision agent (3/3 full, 2/3 half, else HOLD) | backend/engine/agents.py → decide() |
| 5–6. Size, stop-loss, risk manager | backend/engine/risk_manager.py |
| 7. Mock exchange (fees + slippage) | backend/engine/exchange.py |
| 8. Journal + dashboard | backend/engine/core.py, frontend/src |
| Chaos Lab + Safety Score | backend/engine/chaos.py |
| Backtest vs buy-and-hold | backend/engine/core.py → run_backtest() |
| All limits (1% risk, 4% stop, 3% loss cap…) | backend/engine/config.py |

## API

| Method | Path | Body |
|---|---|---|
| GET | /api/state | |
| POST | /api/tick | {"steps": 1} |
| POST | /api/reset | |
| POST | /api/kill-switch | {"engaged": true} |
| POST | /api/chaos | {"scenario": "flash_crash" \| "fake_news" \| "stale_data" \| "agent_failure"} |
| GET | /api/backtest | |
=======
# profit-pilots-AI
>>>>>>> d8193d16763b01b888ebbf503f4ab64f2c216a51
