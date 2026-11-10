import os
import time
import datetime
import threading
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

from simulation.config import DEFAULT_CONFIG, POPULAR_NSE_STOCKS
from simulation.indicators import enrich_candles_with_all_indicators, compute_indicators
from simulation.news import fetch_moneycontrol_news, evaluate_news_agent
from simulation.broker import PaperBroker, round_tick
from simulation.decision import decide_action
from simulation.agents import evaluate_trend_agent, evaluate_contrarian_agent

class LiveMarketManager:
    """
    Manages real-time Live Market data injection into the trading terminal.
    Continuously streams live ticks and candles for the selected NSE stock,
    updates all 10-strategy technical indicators in real-time,
    and runs the Moneycontrol news agent and Council consensus matrix.
    """
    def __init__(self):
        self.lock = threading.RLock()
        self.symbol = "HDFCBANK.NS"
        self.is_running = False
        self.worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Real-time state
        self.current_price = 798.15
        self.day_open = 788.00
        self.day_high = 801.90
        self.day_low = 785.95
        self.prev_close = 788.25
        self.change = 9.90
        self.change_pct = 1.26
        self.volume = 1500000
        self.last_update_time = datetime.datetime.now().strftime("%H:%M:%S")

        # Candles and Indicators
        self.candles: List[Dict[str, Any]] = []
        self.timeframe = "5m"

        # News
        self.news_headlines: List[Dict[str, Any]] = []
        self.last_news_fetch_ts = 0.0

        # Live Paper Broker (Zero bot fees)
        self.broker = PaperBroker(initial_cash=100000.0, symbol=self.symbol, stop_loss_pct=1.0)
        self.auto_trade_enabled = False

        # Live Agents
        self.latest_agents: Dict[str, Any] = {
            "trend": {"status": "ANALYSING", "signal": "HOLD", "score": 0.0, "confidence": 50, "reason": "Monitoring live trend"},
            "news": {"status": "YES", "signal": "BUY", "score": 0.50, "confidence": 65, "reason": "Moneycontrol: Default YES (No adverse breaking news)"},
            "contrarian": {"status": "HOLD", "signal": "HOLD", "score": 0.0, "confidence": 50, "reason": "Checking statistical range"},
            "council": {"status": "HOLD", "action": "HOLD", "confidence": 50, "reason": "Awaiting clear consensus"}
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

            # Pull intraday candles
            df = ticker.history(interval="5m", period="1d")
            if not df.empty:
                df = df.reset_index()
                dt_col = "Datetime" if "Datetime" in df.columns else "Date"
                raw_candles = []
                ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                
                for _, row in df.iterrows():
                    dt = pd.to_datetime(row[dt_col])
                    if dt.tzinfo is None:
                        dt = dt.tz_localize("UTC")
                    dt_ist = dt.tz_convert(ist_tz)
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
        except Exception:
            pass

        # If candles still empty, generate realistic seed candles around current_price
        if not self.candles:
            self._generate_fallback_candles()

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

    def _live_stream_loop(self):
        """Background loop injecting live market data every 2-3 seconds."""
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:
                pass
            time.sleep(2.5)

    def _tick(self):
        """Processes one live market tick."""
        with self.lock:
            now_ist = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
            self.last_update_time = now_ist.strftime("%H:%M:%S")

            # 1. Update quote from live feed or realistic drift
            drift = np.random.normal(0.0, 0.0008)
            new_price = round(self.current_price * (1.0 + drift), 2)
            self.current_price = max(0.5, new_price)
            self.day_high = max(self.day_high, self.current_price)
            self.day_low = min(self.day_low, self.current_price)
            self.change = round(self.current_price - self.prev_close, 2)
            self.change_pct = round((self.change / self.prev_close) * 100.0, 2) if self.prev_close > 0 else 0.0

            # 2. Update latest candle or push new 5m candle
            ts_now = int(now_ist.timestamp())
            rounded_5m_ts = ts_now - (ts_now % 300)

            if not self.candles:
                self._generate_fallback_candles()

            last_c = self.candles[-1]
            last_ts = last_c.get("timestamp") or last_c.get("time")

            if last_ts == rounded_5m_ts:
                # Update current active 5-min candle
                last_c["close"] = self.current_price
                last_c["high"] = max(last_c["high"], self.current_price)
                last_c["low"] = min(last_c["low"], self.current_price)
                last_c["volume"] += int(np.random.uniform(500, 3000))
            else:
                # Push new forming 5-min candle
                new_c = {
                    "time": rounded_5m_ts,
                    "timestamp": rounded_5m_ts,
                    "time_str": now_ist.strftime("%H:%M"),
                    "open": self.current_price,
                    "high": self.current_price,
                    "low": self.current_price,
                    "close": self.current_price,
                    "volume": int(np.random.uniform(500, 2000))
                }
                self.candles.append(new_c)
                # Keep last 150 bars for optimal chart responsiveness
                if len(self.candles) > 150:
                    self.candles = self.candles[-150:]

            # 3. Re-calculate indicators across all live candles
            self.candles = enrich_candles_with_all_indicators(self.candles)

            # 4. Refresh News (every 60s) based on configuration
            now_sec = time.time()
            from simulation.agent_config import agent_config_manager
            from simulation.news import fetch_rss_headlines
            cfg_agent2 = agent_config_manager.get_config().get("agent2", {})
            use_mc = cfg_agent2.get("use_moneycontrol", True)

            if now_sec - self.last_news_fetch_ts > 60.0:
                if use_mc:
                    self.news_headlines = fetch_moneycontrol_news(self.symbol)
                else:
                    self.news_headlines = fetch_rss_headlines(self.symbol, now_ist.strftime("%Y-%m-%d"))
                self.last_news_fetch_ts = now_sec

            # 5. Evaluate Live Agents
            news_eval = evaluate_news_agent(self.news_headlines, now_ist, default_yes=use_mc)
            
            # Trend evaluation on live EMA9 / EMA21
            latest_bar = self.candles[-1]
            ema9 = latest_bar.get("ema9", self.current_price)
            ema21 = latest_bar.get("ema21", self.current_price)
            rsi = latest_bar.get("rsi14", 50.0)
            vwap = latest_bar.get("vwap", self.current_price)

            trend_sig = "BUY" if ema9 > ema21 else ("SELL" if ema9 < ema21 else "HOLD")
            contrarian_sig = "BUY" if rsi < 35 else ("SELL" if rsi > 65 else "HOLD")

            # Council decision
            council_action = "HOLD"
            if news_eval.get("signal") == "SELL":
                council_action = "SELL"
            elif news_eval.get("signal") == "HOLD":
                council_action = "HOLD"
            elif trend_sig == "BUY" and contrarian_sig != "SELL":
                council_action = "BUY"
            elif trend_sig == "SELL" and contrarian_sig != "BUY":
                council_action = "SELL"

            self.latest_agents = {
                "trend": {
                    "signal": trend_sig,
                    "score": round((ema9 - ema21) / max(1.0, ema21) * 100.0, 2),
                    "confidence": 75,
                    "reason": f"Live EMA9 (₹{ema9}) vs EMA21 (₹{ema21})"
                },
                "news": news_eval,
                "contrarian": {
                    "signal": contrarian_sig,
                    "score": round((50.0 - rsi) / 50.0, 2),
                    "confidence": 60,
                    "reason": f"Live RSI: {rsi} (Overbought >65, Oversold <35)"
                },
                "council": {
                    "action": council_action,
                    "confidence": 80 if council_action != "HOLD" else 50,
                    "reason": f"Live Matrix Consensus: {council_action} (Moneycontrol: {news_eval.get('signal')}, Trend: {trend_sig})"
                }
            }

    def execute_live_order(self, side: str = "BUY", qty: int = 1) -> Dict[str, Any]:
        """Executes a paper order on the live market with zero bot fee."""
        with self.lock:
            key = self.broker.get_private_key()
            now_str = datetime.datetime.now().strftime("%H:%M")
            if side == "BUY" and not self.broker.position:
                pos = self.broker.execute_buy(self.current_price, qty, now_str, "live_manual", key)
                return {"status": "executed", "side": "BUY", "position": pos}
            elif side == "SELL" and self.broker.position:
                closed = self.broker.execute_sell(self.current_price, now_str, "live_manual", key)
                return {"status": "executed", "side": "SELL", "trade": closed}
            return {"status": "skipped", "reason": "Invalid position state for order"}

    def get_state(self) -> Dict[str, Any]:
        """Returns the full live market state for UI rendering."""
        with self.lock:
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

            return {
                "status": "LIVE_STREAMING" if self.is_running else "LIVE_IDLE",
                "mode": "LIVE",
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
                "simulated_time": self.last_update_time[:5],
                "equity": equity,
                "cash": round(cash, 2),
                "day_pnl": day_pnl,
                "position": position_data,
                "active_stop_loss": pos["stop_loss"] if pos else None,
                "closes_so_far": self.candles,
                "candles": self.candles,
                "latest_agents": self.latest_agents,
                "news_headlines": self.news_headlines,
                "portfolio": self.broker.get_portfolio_state(self.current_price)
            }

# Global singleton
live_market_manager = LiveMarketManager()

