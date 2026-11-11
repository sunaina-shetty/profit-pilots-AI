import os
import time
import datetime
import threading
import uuid
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

from simulation.config import DEFAULT_CONFIG, POPULAR_NSE_STOCKS, SQUARE_OFF_TIME, SLIPPAGE_BPS
from simulation.indicators import enrich_candles_with_all_indicators, compute_indicators
from simulation.news import fetch_moneycontrol_news, fetch_rss_headlines, evaluate_news_agent
from simulation.broker import PaperBroker, round_tick, compute_round_trip_cost
from simulation.decision import decide_action
from simulation.agents import evaluate_agent1, evaluate_agent3
from simulation.agent_config import agent_config_manager
from simulation.regime import detect_regime
from simulation.llm import generate_template_reason, async_rewrite_narrative

def get_ist_now() -> datetime.datetime:
    """Returns current datetime in Indian Standard Time (UTC+05:30)."""
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))

def check_nse_market_hours(dt_ist: Optional[datetime.datetime] = None) -> Dict[str, Any]:
    """
    NSE / BSE trading hours: Monday to Friday, 09:15 to 15:30 IST.
    Returns:
      is_open: bool
      status: "OPEN" | "CLOSED" | "PRE_MARKET"
      reason: string explanation
    """
    if dt_ist is None:
        dt_ist = get_ist_now()

    # Manual mock override for test environments if explicitly configured
    if os.getenv("FORCE_LIVE_MARKET_OPEN", "0") == "1":
        return {
            "is_open": True,
            "status": "OPEN",
            "reason": "Live Market Open (Override active).",
            "current_time_ist": dt_ist.strftime("%H:%M:%S"),
            "weekday": dt_ist.weekday()
        }

    weekday = dt_ist.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday
    time_str = dt_ist.strftime("%H:%M")

    if weekday in (5, 6):
        day_name = "Saturday" if weekday == 5 else "Sunday"
        return {
            "is_open": False,
            "status": "CLOSED",
            "reason": f"Market Closed ({day_name} Weekend). Continuous trading opens Monday at 09:15 AM IST.",
            "current_time_ist": dt_ist.strftime("%H:%M:%S"),
            "weekday": weekday
        }
    elif time_str < "09:00":
        return {
            "is_open": False,
            "status": "CLOSED",
            "reason": "Market Closed (Pre-market opens at 09:00 AM, Regular trading at 09:15 AM IST).",
            "current_time_ist": dt_ist.strftime("%H:%M:%S"),
            "weekday": weekday
        }
    elif "09:00" <= time_str < "09:15":
        return {
            "is_open": False,
            "status": "PRE_MARKET",
            "reason": "Pre-Market Session (09:00 - 09:15 IST). Continuous live trading begins at 09:15 AM IST.",
            "current_time_ist": dt_ist.strftime("%H:%M:%S"),
            "weekday": weekday
        }
    elif "09:15" <= time_str <= "15:30":
        return {
            "is_open": True,
            "status": "OPEN",
            "reason": "Live Market Open (Continuous Intraday Session 09:15 - 15:30 IST).",
            "current_time_ist": dt_ist.strftime("%H:%M:%S"),
            "weekday": weekday
        }
    else:
        return {
            "is_open": False,
            "status": "CLOSED",
            "reason": "Market Closed (Trading ended at 03:30 PM IST). Next session opens at 09:15 AM IST.",
            "current_time_ist": dt_ist.strftime("%H:%M:%S"),
            "weekday": weekday
        }

def compute_holding_duration(buy_time_str: str, sell_time_str: str) -> str:
    """Format holding time between entry and exit in minutes and 5-min bars."""
    try:
        t1 = datetime.datetime.strptime(buy_time_str, "%H:%M")
        t2 = datetime.datetime.strptime(sell_time_str, "%H:%M")
        mins = int((t2 - t1).total_seconds() / 60)
        if mins < 0:
            mins = 0
        bars = max(1, mins // 5)
        return f"{mins} mins ({bars} bars)"
    except Exception:
        return "5 mins (1 bar)"

class LiveMarketManager:
    """
    Manages real-time Live Market data injection and the automated multi-agent trading bot.
    Strictly aligns with real-world Indian Market operating hours (09:15 - 15:30 IST, Mon-Fri):
    - When market is OPEN: streams live quotes, forms dynamic 5-min candles, runs multi-agent trading bot.
    - When market is CLOSED: locks to official closing data from latest session, preserves completed candles,
      and halts fake tick generation and live order fills.
    - Automated Trading Bot:
      - Uses selected strategies for Agent 1 and Agent 3 from agent_config_manager.
      - Uses Agent 2 News agent (Moneycontrol or RSS).
      - Executes Council Consensus trades with zero bot fee and PaperBroker risk management.
    """
    def __init__(self):
        self.lock = threading.RLock()
        self.symbol = "HDFCBANK.NS"
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Market timing state
        timing = check_nse_market_hours()
        self.is_market_open = timing["is_open"]
        self.market_status = timing["status"]
        self.market_status_message = timing["reason"]

        # Real-time / Official closing quote state
        self.current_price = 798.15
        self.day_open = 788.00
        self.day_high = 801.90
        self.day_low = 785.95
        self.prev_close = 788.25
        self.change = 9.90
        self.change_pct = 1.26
        self.volume = 1500000
        self.last_update_time = timing["current_time_ist"]

        # Candles and Indicators
        self.candles: List[Dict[str, Any]] = []
        self.timeframe = "5m"
        self.current_indicators: Dict[str, Any] = {}

        # News
        self.news_headlines: List[Dict[str, Any]] = []
        self.last_news_fetch_ts = 0.0
        self.last_price_fetch_ts = 0.0

        # Live Paper Broker (Zero bot fees)
        self.initial_amount = 100000.0
        self.stop_loss_pct = 1.0
        self.broker = PaperBroker(initial_cash=self.initial_amount, symbol=self.symbol, stop_loss_pct=self.stop_loss_pct)

        # Automated Trading Bot State
        self.bot_status = "IDLE"  # "IDLE" | "RUNNING" | "STOPPED" | "PAUSED_NEW"
        self.auto_trade_enabled = False
        self.buy_markers: List[Dict[str, Any]] = []
        self.sell_markers: List[Dict[str, Any]] = []
        self.trade_connections: List[Dict[str, Any]] = []
        self.journal: List[Dict[str, Any]] = []
        self.journal_map: Dict[str, Any] = {}
        self.current_trade_id: Optional[str] = None
        self.highest_close_since_entry = 0.0
        self.orb_entry_done = False
        self.entry_time_str: Optional[str] = None
        self.orb_high = 0.0
        self.orb_low = 0.0
        self.current_regime = "UNCLEAR"
        self.avg_opening_volume = 0.0

        # Multi-Agent State
        self.latest_agents: Dict[str, Any] = {
            "trend": {"status": "ANALYSING", "signal": "HOLD", "score": 0.0, "confidence": 50, "reason": "Monitoring market setup"},
            "news": {"status": "YES", "signal": "BUY", "score": 0.50, "confidence": 65, "reason": "Moneycontrol: Default YES (No adverse breaking news)"},
            "contrarian": {"status": "HOLD", "signal": "HOLD", "score": 0.0, "confidence": 50, "reason": "Checking statistical range"},
            "council": {"status": "HOLD", "action": "HOLD", "confidence": 50, "reason": "Awaiting market consensus"}
        }
        self.latest_decision: Dict[str, Any] = {
            "action": "HOLD",
            "size": "none",
            "rule": "Market initial setup",
            "score": 0.0,
            "confidence": 0
        }

        # Initialize baseline data
        self._refresh_initial_data()

    def set_symbol(self, symbol: str):
        """Switch live market to a new stock."""
        clean_sym = symbol.strip().upper()
        if not clean_sym.endswith(".NS") and "." not in clean_sym:
            clean_sym = f"{clean_sym}.NS"

        with self.lock:
            if clean_sym != self.symbol:
                self.symbol = clean_sym
                self.broker.symbol = clean_sym
                self.candles = []
                self._refresh_initial_data()

    def _refresh_initial_data(self):
        """Fetches initial live data and candles for the active symbol."""
        timing = check_nse_market_hours()
        self.is_market_open = timing["is_open"]
        self.market_status = timing["status"]
        self.market_status_message = timing["reason"]

        try:
            import yfinance as yf
            ticker = yf.Ticker(self.symbol)
            fast = ticker.fast_info
            
            ltp = float(fast.last_price or 0.0)
            prev = float(fast.previous_close or ltp)
            if ltp > 0:
                self.current_price = round(ltp, 2)
                self.prev_close = round(prev, 2)
                self.day_high = round(float(fast.day_high or ltp), 2)
                self.day_low = round(float(fast.day_low or ltp), 2)
                self.day_open = round(float(fast.open or prev), 2)
                self.change = round(self.current_price - self.prev_close, 2)
                self.change_pct = round((self.change / self.prev_close) * 100.0, 2) if self.prev_close > 0 else 0.0

            df = ticker.history(interval="5m", period="5d")
            if not df.empty:
                df = df.reset_index()
                dt_col = "Datetime" if "Datetime" in df.columns else "Date"
                ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                
                df["dt_parsed"] = pd.to_datetime(df[dt_col])
                df["dt_ist"] = df["dt_parsed"].apply(lambda d: d.tz_localize("UTC").tz_convert(ist_tz) if d.tzinfo is None else d.tz_convert(ist_tz))
                df["date_str"] = df["dt_ist"].dt.strftime("%Y-%m-%d")
                
                latest_date = df["date_str"].iloc[-1]
                day_df = df[df["date_str"] == latest_date]
                
                raw_candles = []
                for _, row in day_df.iterrows():
                    dt_ist = row["dt_ist"]
                    ts = int(dt_ist.timestamp())
                    raw_candles.append({
                        "time": ts,
                        "timestamp": ts,
                        "time_str": dt_ist.strftime("%H:%M"),
                        "open": round(float(row["Open"]), 2),
                        "high": round(float(row["High"]), 2),
                        "low": round(float(row["Low"]), 2),
                        "close": round(float(row["Close"]), 2),
                        "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0
                    })
                
                if raw_candles:
                    self.candles = enrich_candles_with_all_indicators(raw_candles)
                    if not self.is_market_open:
                        self.current_price = raw_candles[-1]["close"]
                        self.day_open = raw_candles[0]["open"]
                        self.day_high = max(c["high"] for c in raw_candles)
                        self.day_low = min(c["low"] for c in raw_candles)
                        self.change = round(self.current_price - self.prev_close, 2)
                        self.change_pct = round((self.change / self.prev_close) * 100.0, 2) if self.prev_close > 0 else 0.0
        except Exception:
            pass

        if not self.candles:
            self._generate_fallback_candles()

        # Compute initial indicators
        if self.candles:
            self.current_indicators = compute_indicators([], self.candles)

    def _generate_fallback_candles(self):
        """Generates realistic initial candles if API history is unavailable."""
        now = datetime.datetime.now()
        ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        base_ts = int(datetime.datetime(now.year, now.month, now.day, 9, 15, tzinfo=ist_tz).timestamp())
        
        raw_candles = []
        curr = self.current_price
        for i in range(25):
            t_stamp = base_ts + i * 300
            time_label = datetime.datetime.fromtimestamp(t_stamp, tz=ist_tz).strftime("%H:%M")
            o = round(curr * (1.0 + np.random.uniform(-0.002, 0.002)), 2)
            c = round(o * (1.0 + np.random.uniform(-0.003, 0.003)), 2)
            h = round(max(o, c) + abs(c - o) * np.random.uniform(0.1, 0.5) + 0.5, 2)
            l = round(min(o, c) - abs(c - o) * np.random.uniform(0.1, 0.5) - 0.5, 2)
            v = int(np.random.uniform(10000, 80000))
            curr = c
            
            raw_candles.append({
                "time": t_stamp,
                "timestamp": t_stamp,
                "time_str": time_label,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": v
            })
            
        self.candles = enrich_candles_with_all_indicators(raw_candles)

    def start(self):
        """Starts live streaming worker thread."""
        with self.lock:
            if self.is_running:
                return
            self.is_running = True
            self._stop_event.clear()
            self.worker_thread = threading.Thread(target=self._live_stream_loop, daemon=True)
            self.worker_thread.start()

    def stop(self):
        """Stops live streaming worker."""
        with self.lock:
            self.is_running = False
            self._stop_event.set()

    def start_trade_bot(self, amount: float = 100000.0, stop_loss_pct: float = 1.0) -> Dict[str, Any]:
        """
        Starts the automated trading bot on live market data with selected strategies.
        """
        with self.lock:
            self.initial_amount = float(amount)
            self.stop_loss_pct = float(stop_loss_pct)
            self.broker = PaperBroker(initial_cash=self.initial_amount, symbol=self.symbol, stop_loss_pct=self.stop_loss_pct)
            self.bot_status = "RUNNING"
            self.auto_trade_enabled = True
            self.buy_markers = []
            self.sell_markers = []
            self.trade_connections = []
            self.journal = []
            self.journal_map = {}
            self.current_trade_id = None
            self.highest_close_since_entry = 0.0
            self.orb_entry_done = False
            self.entry_time_str = None

            now_str = get_ist_now().strftime("%H:%M")
            timing = check_nse_market_hours()
            status_note = "Continuous live execution active." if timing["is_open"] else f"Market currently closed ({timing['status']}). Orders will execute during live market hours (09:15 AM - 03:30 PM IST)."
            entry_id = str(uuid.uuid4())[:8]
            msg = f"Automated Trade Bot started for {self.symbol} with capital ₹{self.initial_amount:,.2f} and stop-loss {self.stop_loss_pct}%. {status_note}"
            j_entry = {
                "id": entry_id,
                "time": now_str,
                "action": "START",
                "reason": msg,
                "source": "TEMPLATE",
                "is_hold": True
            }
            self.journal.insert(0, j_entry)
            self.journal_map[entry_id] = j_entry

            if not self.is_running:
                self.start()

            return {"status": "started", "bot_status": self.bot_status, "state": self.get_state()}

    def stop_trade_bot(self, mode: str = "flatten") -> Dict[str, Any]:
        """
        Stops the automated trading bot.
        mode="flatten": Emergency liquidation of open positions.
        mode="stop_new": Halts opening of new positions while active trade runs with SL/TP.
        """
        with self.lock:
            now_str = get_ist_now().strftime("%H:%M")
            auth_key = self.broker.get_private_key()

            if mode == "stop_new":
                self.broker.stop_new_trades_only = True
                self.bot_status = "PAUSED_NEW"
                entry_id = str(uuid.uuid4())[:8]
                j_entry = {
                    "id": entry_id,
                    "time": now_str,
                    "action": "HOLD",
                    "reason": "Live Bot paused new entries; active position managed by SL/TP.",
                    "source": "TEMPLATE",
                    "is_hold": True
                }
                self.journal.insert(0, j_entry)
                self.journal_map[entry_id] = j_entry
                return {"status": "paused_new", "bot_status": self.bot_status, "state": self.get_state()}

            self.bot_status = "STOPPED"
            self.auto_trade_enabled = False
            if self.broker.position:
                flat_trade = self.broker.execute_sell(
                    self.current_price, now_str, "Live Bot Stopped (Emergency Flatten)", auth_key, max(0, len(self.candles) - 1)
                )
                trade_id = self.current_trade_id or str(uuid.uuid4())[:8]
                self.current_trade_id = None
                candle_ts = int(get_ist_now().timestamp())
                self.sell_markers.append({
                    "id": f"sell-{trade_id}",
                    "trade_id": trade_id,
                    "time": candle_ts,
                    "time_str": now_str,
                    "timestamp": candle_ts,
                    "price": self.current_price,
                    "qty": flat_trade.get("qty", 0),
                    "pnl": flat_trade.get("net_pnl", 0.0),
                    "gross_pnl": flat_trade.get("gross_pnl", 0.0),
                    "fees": flat_trade.get("total_fees", 0.0),
                    "agent_name": "Emergency Flatten",
                    "agent_tag": "Live Bot Stop",
                    "action": "SELL",
                    "reason": "Live Bot Stopped (Emergency Flatten)",
                    "buy_price": flat_trade.get("buy_price", 0.0),
                    "buy_time": flat_trade.get("buy_time", ""),
                    "sell_time": now_str,
                    "holding_duration": "Flattened",
                    "symbol": self.symbol
                })
                self.trade_connections.append({
                    "trade_id": trade_id,
                    "symbol": self.symbol,
                    "entry_time": flat_trade.get("buy_time", ""),
                    "entry_price": flat_trade.get("buy_price", 0.0),
                    "exit_time": now_str,
                    "exit_price": self.current_price,
                    "qty": flat_trade.get("qty", 0),
                    "pnl": flat_trade.get("net_pnl", 0.0),
                    "gross_pnl": flat_trade.get("gross_pnl", 0.0),
                    "fees": flat_trade.get("total_fees", 0.0),
                    "agent_name": "Emergency Flatten",
                    "agent_tag": "Live Bot Stop",
                    "reason": "Live Bot Stopped (Emergency Flatten)"
                })

            entry_id = str(uuid.uuid4())[:8]
            j_entry = {
                "id": entry_id,
                "time": now_str,
                "action": "STOP",
                "reason": "Live Bot stopped. Positions flattened and automated trading halted.",
                "source": "TEMPLATE",
                "is_hold": True
            }
            self.journal.insert(0, j_entry)
            self.journal_map[entry_id] = j_entry
            return {"status": "stopped", "bot_status": self.bot_status, "state": self.get_state()}

    def _live_stream_loop(self):
        """Background loop injecting live market data every 2.5 seconds."""
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:
                pass
            time.sleep(2.5)

    def _tick(self):
        """Processes live market updates and runs multi-agent trading bot aligned with market hours."""
        with self.lock:
            timing = check_nse_market_hours()
            self.is_market_open = timing["is_open"]
            self.market_status = timing["status"]
            self.market_status_message = timing["reason"]
            now_ist = get_ist_now()
            now_str = now_ist.strftime("%H:%M")
            self.last_update_time = now_ist.strftime("%H:%M:%S")

            # -----------------------------------------------------------------
            # 1. FETCH NEWS HEADLINES (every 60s)
            # -----------------------------------------------------------------
            now_sec = time.time()
            cfg_agent2 = agent_config_manager.get_config().get("agent2", {})
            use_mc = cfg_agent2.get("use_moneycontrol", True)
            if now_sec - self.last_news_fetch_ts > 60.0:
                if use_mc:
                    self.news_headlines = fetch_moneycontrol_news(self.symbol)
                else:
                    self.news_headlines = fetch_rss_headlines(self.symbol, now_ist.strftime("%Y-%m-%d"))
                self.last_news_fetch_ts = now_sec

            news_eval = evaluate_news_agent(self.news_headlines, now_ist, default_yes=use_mc)

            # -----------------------------------------------------------------
            # 2. MARKET DATA TICK / BAR UPDATES
            # -----------------------------------------------------------------
            if self.is_market_open:
                # Real-Time Intraday Data Streaming & Live Ticks
                # Throttle external yfinance HTTP calls to every 15s to keep API responses instantaneous
                if now_sec - self.last_price_fetch_ts > 15.0:
                    try:
                        import yfinance as yf
                        ticker = yf.Ticker(self.symbol)
                        fast = ticker.fast_info
                        ltp = float(fast.last_price or 0.0)
                        if ltp > 0:
                            self.current_price = round(ltp, 2)
                            self.day_high = max(self.day_high, self.current_price)
                            self.day_low = min(self.day_low, self.current_price)
                            self.change = round(self.current_price - self.prev_close, 2)
                            self.change_pct = round((self.change / self.prev_close) * 100.0, 2) if self.prev_close > 0 else 0.0
                            self.last_price_fetch_ts = now_sec
                    except Exception:
                        pass
                else:
                    drift = np.random.normal(0.0, 0.0003)
                    self.current_price = round(self.current_price * (1.0 + drift), 2)
                    self.day_high = max(self.day_high, self.current_price)
                    self.day_low = min(self.day_low, self.current_price)
                    self.change = round(self.current_price - self.prev_close, 2)
                    self.change_pct = round((self.change / self.prev_close) * 100.0, 2) if self.prev_close > 0 else 0.0

                ts_now = int(now_ist.timestamp())
                rounded_5m_ts = ts_now - (ts_now % 300)

                if not self.candles:
                    self._generate_fallback_candles()

                last_c = self.candles[-1]
                last_ts = last_c.get("timestamp") or last_c.get("time")

                if last_ts == rounded_5m_ts:
                    last_c["close"] = self.current_price
                    last_c["high"] = max(last_c["high"], self.current_price)
                    last_c["low"] = min(last_c["low"], self.current_price)
                    last_c["volume"] += int(np.random.uniform(500, 2500))
                else:
                    new_c = {
                        "time": rounded_5m_ts,
                        "timestamp": rounded_5m_ts,
                        "time_str": now_str,
                        "open": self.current_price,
                        "high": self.current_price,
                        "low": self.current_price,
                        "close": self.current_price,
                        "volume": int(np.random.uniform(500, 2000))
                    }
                    self.candles.append(new_c)
                    if len(self.candles) > 150:
                        self.candles = self.candles[-150:]

                self.candles = enrich_candles_with_all_indicators(self.candles)

            # -----------------------------------------------------------------
            # 3. COMPUTE STRATEGY INDICATORS & MULTI-AGENT EVALUATIONS
            # -----------------------------------------------------------------
            if not self.candles:
                self._generate_fallback_candles()

            indicators = compute_indicators([], self.candles)
            self.current_indicators = indicators

            # Opening Range (first 3 bars)
            orb_bars = self.candles[:min(3, len(self.candles))]
            if orb_bars:
                self.orb_high = max(float(b.get("high", self.current_price)) for b in orb_bars)
                self.orb_low = min(float(b.get("low", self.current_price)) for b in orb_bars)

            # Regime Detection
            current_regime, regime_reason = detect_regime(
                self.candles, self.orb_high, self.orb_low, indicators
            )
            self.current_regime = current_regime

            is_holding = (self.broker.position is not None)
            entry_type = self.broker.position.get("entry_type", "orb") if is_holding else None
            entry_price = self.broker.position.get("buy_price") if is_holding else None
            pos_side = self.broker.position.get("side", "LONG") if is_holding else "LONG"

            # 3.1 Evaluate Agent 1 (Uses User-Configured Strategy from agent_config_manager)
            trend_res = evaluate_agent1(
                candles_5m_today=self.candles,
                indicators=indicators,
                is_holding=is_holding,
                entry_type=entry_type,
                entry_price=entry_price,
                avg_opening_volume=self.avg_opening_volume,
                orb_entry_done_today=self.orb_entry_done,
                stop_loss_pct=self.stop_loss_pct,
                highest_close_since_entry=self.highest_close_since_entry,
                position_side=pos_side
            )
            trend_res["last_evaluation_time"] = now_str
            trend_res["agent_name"] = f"Agent 1: {trend_res.get('strategy_name', 'Trend')}"

            # 3.2 Evaluate Agent 2 (News Agent)
            news_res = news_eval
            news_res["last_evaluation_time"] = now_str
            news_res["agent_name"] = "Agent 2: News Sentiment"
            news_res["in_play"] = len(self.news_headlines) > 0

            # 3.3 Evaluate Agent 3 (Uses User-Configured Strategy from agent_config_manager)
            rt_cost_pct = (compute_round_trip_cost(self.current_price, 10) / (self.current_price * 10)) if self.current_price > 0 else 0.001
            contrarian_res = evaluate_agent3(
                candles_5m_today=self.candles,
                indicators=indicators,
                is_holding=is_holding,
                entry_type=entry_type,
                entry_time_str=self.entry_time_str,
                entry_price=entry_price,
                stop_loss_pct=self.stop_loss_pct,
                round_trip_cost_pct=rt_cost_pct,
                position_side=pos_side
            )
            contrarian_res["last_evaluation_time"] = now_str
            contrarian_res["agent_name"] = f"Agent 3: {contrarian_res.get('strategy_name', 'Mean Reversion')}"

            # 3.4 Council Decision via Continuous Weighted Scoring
            decision = decide_action(
                trend_res=trend_res,
                news_res=news_res,
                contrarian_res=contrarian_res,
                is_holding=is_holding,
                entry_type=entry_type,
                regime=current_regime,
                regime_reason=regime_reason,
                agent_mode="combined",
                position_side=pos_side
            )
            self.latest_decision = decision

            # Update UI Agent Cards
            self.latest_agents = {
                "trend": trend_res,
                "news": news_res,
                "contrarian": contrarian_res,
                "council": {
                    "status": decision["action"],
                    "action": decision["action"],
                    "score": decision.get("score", 0.0),
                    "confidence": decision.get("confidence", 50),
                    "reason": decision.get("rule", f"Consensus: {decision['action']}"),
                    "approved": decision["action"] in ("BUY", "SELL")
                }
            }

            # -----------------------------------------------------------------
            # 4. AUTOMATED TRADING BOT EXECUTION (When bot is RUNNING and Market is OPEN)
            # -----------------------------------------------------------------
            if not self.is_market_open:
                # Outside market hours: No automated orders fill
                return

            if self.bot_status != "RUNNING":
                # Bot not started: skip automated trade placement
                return

            auth_key = self.broker.get_private_key()
            candle_ts = int(now_ist.timestamp())

            # 4.1 RISK GATE: Stop-Loss, Take-Profit (1.5R), Trailing (+1R breakeven)
            if self.candles and self.broker.position:
                st_trade = self.broker.check_stop_and_target_on_candle(self.candles[-1], len(self.candles) - 1)
                if st_trade:
                    trade_id = self.current_trade_id or str(uuid.uuid4())[:8]
                    self.current_trade_id = None
                    duration_str = compute_holding_duration(st_trade.get("buy_time", ""), now_str)
                    action_tag = "Stop-Loss Risk Trigger" if st_trade.get("is_stop_loss") else "Take-Profit Target (1.5R)"

                    self.sell_markers.append({
                        "id": f"sell-{trade_id}",
                        "trade_id": trade_id,
                        "time": candle_ts,
                        "time_str": now_str,
                        "timestamp": candle_ts,
                        "price": st_trade["sell_price"],
                        "qty": st_trade.get("qty", 0),
                        "pnl": st_trade["net_pnl"],
                        "gross_pnl": st_trade.get("gross_pnl", 0.0),
                        "entry_fees": st_trade.get("buy_fees", 0.0),
                        "exit_fees": st_trade.get("sell_fees", 0.0),
                        "fees": st_trade.get("total_fees", 0.0),
                        "agent_name": action_tag,
                        "agent_tag": "Risk Management",
                        "action": "SELL",
                        "reason": st_trade["reason"],
                        "buy_price": st_trade.get("buy_price", 0.0),
                        "buy_time": st_trade.get("buy_time", ""),
                        "sell_time": now_str,
                        "holding_duration": duration_str,
                        "symbol": self.symbol
                    })
                    self.trade_connections.append({
                        "trade_id": trade_id,
                        "symbol": self.symbol,
                        "entry_time": st_trade.get("buy_time", ""),
                        "entry_price": st_trade.get("buy_price", 0.0),
                        "exit_time": now_str,
                        "exit_price": st_trade["sell_price"],
                        "qty": st_trade.get("qty", 0),
                        "pnl": st_trade["net_pnl"],
                        "gross_pnl": st_trade.get("gross_pnl", 0.0),
                        "fees": st_trade.get("total_fees", 0.0),
                        "agent_name": action_tag,
                        "agent_tag": "Risk Management",
                        "reason": st_trade["reason"]
                    })
                    rec = {
                        "time": now_str,
                        "price": st_trade["sell_price"],
                        "stop": st_trade["sell_price"],
                        "pnl": st_trade["net_pnl"],
                        "action": "SELL",
                        "event_type": "STOP_LOSS" if st_trade.get("is_stop_loss") else "TAKE_PROFIT",
                        "rule": st_trade["reason"]
                    }
                    entry_id = str(uuid.uuid4())[:8]
                    tpl_text = generate_template_reason(rec)
                    j_entry = {"id": entry_id, "time": now_str, "action": "SELL", "reason": tpl_text, "source": "TEMPLATE", "is_hold": False}
                    self.journal.insert(0, j_entry)
                    self.journal_map[entry_id] = j_entry
                    async_rewrite_narrative(entry_id, rec, self.journal_map)

            # 4.2 Mandatory 15:15 IST Square-Off
            if now_str >= SQUARE_OFF_TIME and self.broker.position:
                exit_reason = "15:15 IST Mandatory Intraday Square-Off"
                sq_trade = self.broker.execute_sell(self.current_price, now_str, exit_reason, auth_key, len(self.candles) - 1)
                trade_id = self.current_trade_id or str(uuid.uuid4())[:8]
                self.current_trade_id = None
                duration_str = compute_holding_duration(sq_trade.get("buy_time", ""), now_str)

                self.sell_markers.append({
                    "id": f"sell-{trade_id}",
                    "trade_id": trade_id,
                    "time": candle_ts,
                    "time_str": now_str,
                    "timestamp": candle_ts,
                    "price": self.current_price,
                    "qty": sq_trade.get("qty", 0),
                    "pnl": sq_trade["net_pnl"],
                    "gross_pnl": sq_trade.get("gross_pnl", 0.0),
                    "fees": sq_trade.get("total_fees", 0.0),
                    "agent_name": "15:15 IST Square-Off Trigger",
                    "agent_tag": "Risk Management",
                    "action": "SELL",
                    "reason": exit_reason,
                    "buy_price": sq_trade.get("buy_price", 0.0),
                    "buy_time": sq_trade.get("buy_time", ""),
                    "sell_time": now_str,
                    "holding_duration": duration_str,
                    "symbol": self.symbol
                })
                self.trade_connections.append({
                    "trade_id": trade_id,
                    "symbol": self.symbol,
                    "entry_time": sq_trade.get("buy_time", ""),
                    "entry_price": sq_trade.get("buy_price", 0.0),
                    "exit_time": now_str,
                    "exit_price": self.current_price,
                    "qty": sq_trade.get("qty", 0),
                    "pnl": sq_trade["net_pnl"],
                    "gross_pnl": sq_trade.get("gross_pnl", 0.0),
                    "fees": sq_trade.get("total_fees", 0.0),
                    "agent_name": "15:15 IST Square-Off Trigger",
                    "agent_tag": "Risk Management",
                    "reason": exit_reason
                })
                rec = {"time": now_str, "price": self.current_price, "pnl": sq_trade["net_pnl"], "action": "SELL", "event_type": "SQUARE_OFF", "rule": exit_reason}
                entry_id = str(uuid.uuid4())[:8]
                tpl_text = generate_template_reason(rec)
                j_entry = {"id": entry_id, "time": now_str, "action": "SELL", "reason": tpl_text, "source": "TEMPLATE", "is_hold": False}
                self.journal.insert(0, j_entry)
                self.journal_map[entry_id] = j_entry
                async_rewrite_narrative(entry_id, rec, self.journal_map)

            # 4.3 2% Daily Loss Limit Circuit Breaker
            if self.broker.evaluate_daily_loss_limit(self.current_price):
                if self.broker.position:
                    exit_reason = "Daily Loss Limit (2%) Circuit Breaker"
                    dl_trade = self.broker.execute_sell(self.current_price, now_str, exit_reason, auth_key, len(self.candles) - 1)
                    trade_id = self.current_trade_id or str(uuid.uuid4())[:8]
                    self.current_trade_id = None
                    duration_str = compute_holding_duration(dl_trade.get("buy_time", ""), now_str)
                    self.sell_markers.append({
                        "id": f"sell-{trade_id}",
                        "trade_id": trade_id,
                        "time": candle_ts,
                        "time_str": now_str,
                        "timestamp": candle_ts,
                        "price": self.current_price,
                        "qty": dl_trade.get("qty", 0),
                        "pnl": dl_trade["net_pnl"],
                        "gross_pnl": dl_trade.get("gross_pnl", 0.0),
                        "fees": dl_trade.get("total_fees", 0.0),
                        "agent_name": "Daily Loss Circuit Breaker",
                        "agent_tag": "Risk Management",
                        "action": "SELL",
                        "reason": exit_reason,
                        "buy_price": dl_trade.get("buy_price", 0.0),
                        "buy_time": dl_trade.get("buy_time", ""),
                        "sell_time": now_str,
                        "holding_duration": duration_str,
                        "symbol": self.symbol
                    })
                return

            # 4.4 COUNCIL BUY EXECUTION
            action = decision.get("action", "HOLD")
            atr_val = float(indicators.get("atr", 0.0))

            if action == "BUY" and not self.broker.position and not getattr(self.broker, "stop_new_trades_only", False):
                can_t, r_reason = self.broker.can_trade(len(self.candles) - 1, "LONG")
                if can_t:
                    fill_price = round_tick(self.current_price * (1.0 + SLIPPAGE_BPS))
                    qty, q_reason = self.broker.calculate_position_size(fill_price, decision.get("size", "normal"), atr=atr_val)
                    if qty >= 1:
                        stop_dist = self.broker.calculate_stop_distance(fill_price, atr_val)
                        expected_gain = (stop_dist * DEFAULT_CONFIG.take_profit_r_multiple) * qty
                        rt_fees = compute_round_trip_cost(fill_price, qty)

                        if expected_gain >= (DEFAULT_CONFIG.cost_filter_multiplier * rt_fees):
                            entry_type = decision.get("entry_type", "council_live")
                            pos = self.broker.execute_buy(fill_price, qty, now_str, entry_type, auth_key, atr=atr_val)
                            self.highest_close_since_entry = fill_price
                            self.entry_time_str = now_str
                            trade_id = str(uuid.uuid4())[:8]
                            self.current_trade_id = trade_id
                            risk_amount = round(abs(fill_price - pos["stop_loss"]) * qty, 2)
                            rule_text = decision.get("rule", "Council Consensus Live BUY")

                            self.buy_markers.append({
                                "id": f"buy-{trade_id}",
                                "trade_id": trade_id,
                                "time": candle_ts,
                                "time_str": now_str,
                                "timestamp": candle_ts,
                                "price": fill_price,
                                "qty": qty,
                                "stop_loss": pos["stop_loss"],
                                "risk_amount": risk_amount,
                                "agent_name": f"Council Consensus: {trend_res.get('strategy_name', 'Trend')} + {contrarian_res.get('strategy_name', 'Reversion')}",
                                "agent_tag": "Live Bot Council",
                                "action": "BUY",
                                "reason": rule_text,
                                "fees": pos["buy_fees"],
                                "symbol": self.symbol,
                                "pnl": None
                            })

                            buy_rec = {
                                "time": now_str,
                                "price": fill_price,
                                "qty": qty,
                                "fees": pos["buy_fees"],
                                "stop": pos["stop_loss"],
                                "action": "BUY",
                                "event_type": "FILL",
                                "rule": rule_text,
                                "entry_type": entry_type,
                                "symbol": self.symbol
                            }
                            b_id = str(uuid.uuid4())[:8]
                            b_tpl = generate_template_reason(buy_rec)
                            b_j = {"id": b_id, "time": now_str, "action": "BUY", "reason": b_tpl, "source": "TEMPLATE", "is_hold": False}
                            self.journal.insert(0, b_j)
                            self.journal_map[b_id] = b_j
                            async_rewrite_narrative(b_id, buy_rec, self.journal_map)

            # 4.5 COUNCIL SELL / EXIT EXECUTION
            elif action in ("SELL", "COVER") and self.broker.position:
                fill_price = round_tick(self.current_price * (1.0 - SLIPPAGE_BPS))
                exit_rule = decision.get("rule", "Council Consensus Live Exit")
                trade = self.broker.execute_sell(fill_price, now_str, exit_rule, auth_key, len(self.candles) - 1)
                trade_id = self.current_trade_id or str(uuid.uuid4())[:8]
                self.current_trade_id = None
                duration_str = compute_holding_duration(trade.get("buy_time", ""), now_str)

                self.sell_markers.append({
                    "id": f"sell-{trade_id}",
                    "trade_id": trade_id,
                    "time": candle_ts,
                    "time_str": now_str,
                    "timestamp": candle_ts,
                    "price": fill_price,
                    "qty": trade.get("qty", 0),
                    "pnl": trade.get("net_pnl", 0.0),
                    "gross_pnl": trade.get("gross_pnl", 0.0),
                    "entry_fees": trade.get("buy_fees", 0.0),
                    "exit_fees": trade.get("sell_fees", 0.0),
                    "fees": trade.get("total_fees", 0.0),
                    "agent_name": "Council Consensus Exit",
                    "agent_tag": "Live Bot Council",
                    "action": "SELL",
                    "reason": exit_rule,
                    "buy_price": trade.get("buy_price", 0.0),
                    "buy_time": trade.get("buy_time", ""),
                    "sell_time": now_str,
                    "holding_duration": duration_str,
                    "symbol": self.symbol
                })
                self.trade_connections.append({
                    "trade_id": trade_id,
                    "symbol": self.symbol,
                    "entry_time": trade.get("buy_time", ""),
                    "entry_price": trade.get("buy_price", 0.0),
                    "exit_time": now_str,
                    "exit_price": fill_price,
                    "qty": trade.get("qty", 0),
                    "pnl": trade.get("net_pnl", 0.0),
                    "gross_pnl": trade.get("gross_pnl", 0.0),
                    "fees": trade.get("total_fees", 0.0),
                    "agent_name": "Council Consensus Exit",
                    "agent_tag": "Live Bot Council",
                    "reason": exit_rule
                })
                sell_rec = {
                    "time": now_str,
                    "price": fill_price,
                    "qty": trade.get("qty", 0),
                    "pnl": trade.get("net_pnl", 0.0),
                    "action": "SELL",
                    "event_type": "EXIT",
                    "rule": exit_rule,
                    "symbol": self.symbol
                }
                s_id = str(uuid.uuid4())[:8]
                s_tpl = generate_template_reason(sell_rec)
                s_j = {"id": s_id, "time": now_str, "action": "SELL", "reason": s_tpl, "source": "TEMPLATE", "is_hold": False}
                self.journal.insert(0, s_j)
                self.journal_map[s_id] = s_j
                async_rewrite_narrative(s_id, sell_rec, self.journal_map)

    def recalculate_strategies(self) -> Dict[str, Any]:
        """Immediately recomputes strategy outputs with new configuration in-memory without network I/O."""
        with self.lock:
            now_ist = get_ist_now()
            now_str = now_ist.strftime("%H:%M")
            if not self.candles:
                return self.get_state()

            indicators = compute_indicators([], self.candles)
            self.current_indicators = indicators

            orb_bars = self.candles[:min(3, len(self.candles))]
            if orb_bars:
                self.orb_high = max(float(b.get("high", self.current_price)) for b in orb_bars)
                self.orb_low = min(float(b.get("low", self.current_price)) for b in orb_bars)

            current_regime, regime_reason = detect_regime(
                self.candles, self.orb_high, self.orb_low, indicators
            )
            self.current_regime = current_regime

            is_holding = (self.broker.position is not None)
            entry_type = self.broker.position.get("entry_type", "orb") if is_holding else None
            entry_price = self.broker.position.get("buy_price") if is_holding else None
            pos_side = self.broker.position.get("side", "LONG") if is_holding else "LONG"

            trend_res = evaluate_agent1(
                candles_5m_today=self.candles,
                indicators=indicators,
                is_holding=is_holding,
                entry_type=entry_type,
                entry_price=entry_price,
                avg_opening_volume=self.avg_opening_volume,
                orb_entry_done_today=self.orb_entry_done,
                stop_loss_pct=self.stop_loss_pct,
                highest_close_since_entry=self.highest_close_since_entry,
                position_side=pos_side
            )
            trend_res["last_evaluation_time"] = now_str
            trend_res["agent_name"] = f"Agent 1: {trend_res.get('strategy_name', 'Trend')}"

            cfg_agent2 = agent_config_manager.get_config().get("agent2", {})
            use_mc = cfg_agent2.get("use_moneycontrol", True)
            news_res = evaluate_news_agent(self.news_headlines, now_ist, default_yes=use_mc)
            news_res["last_evaluation_time"] = now_str
            news_res["agent_name"] = "Agent 2: News Sentiment"
            news_res["in_play"] = len(self.news_headlines) > 0

            rt_cost_pct = (compute_round_trip_cost(self.current_price, 10) / (self.current_price * 10)) if self.current_price > 0 else 0.001
            contrarian_res = evaluate_agent3(
                candles_5m_today=self.candles,
                indicators=indicators,
                is_holding=is_holding,
                entry_type=entry_type,
                entry_time_str=self.entry_time_str,
                entry_price=entry_price,
                stop_loss_pct=self.stop_loss_pct,
                round_trip_cost_pct=rt_cost_pct,
                position_side=pos_side
            )
            contrarian_res["last_evaluation_time"] = now_str
            contrarian_res["agent_name"] = f"Agent 3: {contrarian_res.get('strategy_name', 'Mean Reversion')}"

            decision = decide_action(
                trend_res=trend_res,
                news_res=news_res,
                contrarian_res=contrarian_res,
                is_holding=is_holding,
                entry_type=entry_type,
                regime=current_regime,
                regime_reason=regime_reason,
                agent_mode="combined",
                position_side=pos_side
            )
            self.latest_decision = decision

            self.latest_agents = {
                "trend": trend_res,
                "news": news_res,
                "contrarian": contrarian_res,
                "council": {
                    "status": decision["action"],
                    "action": decision["action"],
                    "score": decision.get("score", 0.0),
                    "confidence": decision.get("confidence", 50),
                    "reason": decision.get("rule", f"Consensus: {decision['action']}"),
                    "approved": decision["action"] in ("BUY", "SELL")
                }
            }
            return self.get_state()

    def execute_live_order(self, side: str = "BUY", qty: int = 1) -> Dict[str, Any]:
        """Executes a paper order on the live market with zero bot fee if market is open."""
        with self.lock:
            timing = check_nse_market_hours()
            if not timing["is_open"]:
                return {
                    "status": "rejected",
                    "reason": f"Market Closed: Live orders can only be executed during market hours (09:15 - 15:30 IST, Mon-Fri). {timing['reason']}"
                }

            key = self.broker.get_private_key()
            now_str = get_ist_now().strftime("%H:%M")
            candle_ts = int(get_ist_now().timestamp())

            if side == "BUY" and not self.broker.position:
                pos = self.broker.execute_buy(self.current_price, qty, now_str, "live_manual", key)
                trade_id = str(uuid.uuid4())[:8]
                self.current_trade_id = trade_id
                self.buy_markers.append({
                    "id": f"buy-{trade_id}",
                    "trade_id": trade_id,
                    "time": candle_ts,
                    "time_str": now_str,
                    "timestamp": candle_ts,
                    "price": self.current_price,
                    "qty": qty,
                    "stop_loss": pos["stop_loss"],
                    "risk_amount": round(abs(self.current_price - pos["stop_loss"]) * qty, 2),
                    "agent_name": "Manual Live Order",
                    "agent_tag": "Manual",
                    "action": "BUY",
                    "reason": "User manual live BUY executed",
                    "fees": pos["buy_fees"],
                    "symbol": self.symbol,
                    "pnl": None
                })
                return {"status": "executed", "side": "BUY", "position": pos}

            elif side == "SELL" and self.broker.position:
                closed = self.broker.execute_sell(self.current_price, now_str, "Manual Live Sell", key, max(0, len(self.candles) - 1))
                trade_id = self.current_trade_id or str(uuid.uuid4())[:8]
                self.current_trade_id = None
                duration_str = compute_holding_duration(closed.get("buy_time", ""), now_str)
                self.sell_markers.append({
                    "id": f"sell-{trade_id}",
                    "trade_id": trade_id,
                    "time": candle_ts,
                    "time_str": now_str,
                    "timestamp": candle_ts,
                    "price": self.current_price,
                    "qty": closed.get("qty", 0),
                    "pnl": closed.get("net_pnl", 0.0),
                    "gross_pnl": closed.get("gross_pnl", 0.0),
                    "fees": closed.get("total_fees", 0.0),
                    "agent_name": "Manual Live Sell",
                    "agent_tag": "Manual",
                    "action": "SELL",
                    "reason": "User manual live SELL executed",
                    "buy_price": closed.get("buy_price", 0.0),
                    "buy_time": closed.get("buy_time", ""),
                    "sell_time": now_str,
                    "holding_duration": duration_str,
                    "symbol": self.symbol
                })
                self.trade_connections.append({
                    "trade_id": trade_id,
                    "symbol": self.symbol,
                    "entry_time": closed.get("buy_time", ""),
                    "entry_price": closed.get("buy_price", 0.0),
                    "exit_time": now_str,
                    "exit_price": self.current_price,
                    "qty": closed.get("qty", 0),
                    "pnl": closed.get("net_pnl", 0.0),
                    "gross_pnl": closed.get("gross_pnl", 0.0),
                    "fees": closed.get("total_fees", 0.0),
                    "agent_name": "Manual Live Sell",
                    "agent_tag": "Manual",
                    "reason": "User manual live SELL executed"
                })
                return {"status": "executed", "side": "SELL", "trade": closed}

            return {"status": "skipped", "reason": "Invalid position state for order"}

    def get_state(self) -> Dict[str, Any]:
        """Returns the full live market and trade bot state for UI rendering."""
        with self.lock:
            timing = check_nse_market_hours()
            is_open = timing["is_open"]
            equity = self.broker.get_equity(self.current_price)
            cash = self.broker.cash
            day_pnl = self.broker.get_day_pnl(self.current_price)
            pos = self.broker.position

            position_data = None
            if pos:
                pnl = round((self.current_price - pos["buy_price"]) * pos["qty"], 2) if pos["side"] == "LONG" else round((pos["buy_price"] - self.current_price) * pos["qty"], 2)
                position_data = {
                    "symbol": pos["symbol"],
                    "side": pos["side"],
                    "qty": pos["qty"],
                    "buy_price": pos["buy_price"],
                    "buy_time": pos["buy_time"],
                    "current_price": self.current_price,
                    "stop_loss": pos["stop_loss"],
                    "profit_loss": pnl
                }

            last_bar_time = self.candles[-1].get("time_str", "15:30") if self.candles else "15:30"
            display_sim_time = self.last_update_time[:5] if is_open else last_bar_time

            return {
                "status": ("LIVE_STREAMING" if self.is_running else "LIVE_IDLE") if is_open else "MARKET_CLOSED",
                "mode": "LIVE",
                "is_market_open": is_open,
                "market_status": timing["status"],
                "market_status_message": timing["reason"],
                "symbol": self.symbol,
                "current_price": self.current_price,
                "day_open": self.day_open,
                "day_high": self.day_high,
                "day_low": self.day_low,
                "prev_close": self.prev_close,
                "change": self.change,
                "change_pct": self.change_pct,
                "volume": self.volume,
                "last_update": self.last_update_time,
                "simulated_time": display_sim_time,
                "equity": equity,
                "cash": round(cash, 2),
                "day_pnl": day_pnl,
                "position": position_data,
                "active_stop_loss": pos["stop_loss"] if pos else None,
                "closes_so_far": self.candles,
                "candles": self.candles,
                "latest_agents": self.latest_agents,
                "latest_decision": self.latest_decision,
                "news_headlines": self.news_headlines,
                "current_regime": self.current_regime,
                "agent_config": agent_config_manager.get_config(),
                "portfolio": self.broker.get_portfolio_state(self.current_price),
                # Bot specifics
                "bot_status": self.bot_status,
                "auto_trade_enabled": self.auto_trade_enabled,
                "initial_amount": self.initial_amount,
                "stop_loss_pct": self.stop_loss_pct,
                "buy_markers": self.buy_markers,
                "sell_markers": self.sell_markers,
                "trade_connections": self.trade_connections,
                "journal": self.journal
            }

# Global singleton
live_market_manager = LiveMarketManager()
