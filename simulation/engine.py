import time
import threading
import datetime
import uuid
from typing import Dict, Any, Optional, List
from simulation.config import (
    TOTAL_DAY_CANDLES, CANDLE_INTERVAL_REAL_SEC, ENTRY_START_TIME,
    ENTRY_END_TIME, SQUARE_OFF_TIME, SLIPPAGE_BPS
)
from simulation.market_data import (
    fetch_daily_ohlc, generate_intraday_candles, generate_fake_prior_day_candles
)
from simulation.indicators import compute_indicators
from simulation.news import fetch_rss_headlines, evaluate_news_agent
from simulation.agents import evaluate_trend_agent, evaluate_contrarian_agent
from simulation.decision import decide_action
from simulation.broker import PaperBroker, round_tick
from simulation.llm import generate_template_reason, async_rewrite_narrative, get_last_llm_error

class SimulationEngine:
    """
    Orchestrates the 50x intraday paper-trading simulator for a full day (09:15 - 15:30).
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Engine state
        self.status = "IDLE"  # IDLE | RUNNING | KILLED | DONE
        self.symbol = "TCS.NS"
        self.initial_amount = 100000.0
        self.stop_loss_pct = 1.0
        self.date_str = datetime.date.today().strftime("%Y-%m-%d")
        self.data_source = "IDLE"
        
        # Candles & Index
        self.candles_1m: List[Dict[str, Any]] = []
        self.prior_day_1m: List[Dict[str, Any]] = []
        self.all_news: List[Dict[str, Any]] = []
        self.current_index = 0
        self.speed_sleep = CANDLE_INTERVAL_REAL_SEC

        # Broker
        self.broker: Optional[PaperBroker] = None

        # Tracking for UI
        self.closes_so_far: List[Dict[str, Any]] = []
        self.buy_markers: List[Dict[str, Any]] = []
        self.sell_markers: List[Dict[str, Any]] = []
        self.latest_agents: Dict[str, Any] = {}
        self.latest_decision: Dict[str, Any] = {}
        self.journal: List[Dict[str, Any]] = []
        self.journal_map: Dict[str, Any] = {} # For fast LLM text updates
        self.summary: Optional[Dict[str, Any]] = None

        # Order queues for NO LOOKAHEAD execution (decided at T, fills at T+1 open)
        self.pending_order: Optional[Dict[str, Any]] = None

    def start_simulation(
        self,
        symbol: str,
        amount: float,
        stop_loss_pct: float,
        target_date_str: Optional[str] = None,
        fast_mode: bool = False
    ):
        with self.lock:
            # Stop existing thread if any
            if self.thread and self.thread.is_alive():
                self._stop_event.set()
                self.thread.join(timeout=2.0)

            self._stop_event.clear()
            self.symbol = symbol if "." in symbol else f"{symbol}.NS"
            self.initial_amount = float(amount)
            self.stop_loss_pct = float(stop_loss_pct)
            
            # 1. Fetch Daily OHLC and generate candles
            ohlc, data_source, resolved_date = fetch_daily_ohlc(self.symbol, target_date_str)
            self.data_source = data_source
            self.date_str = resolved_date
            
            self.candles_1m = generate_intraday_candles(self.symbol, self.date_str, ohlc)
            self.prior_day_1m = generate_fake_prior_day_candles(self.symbol, self.date_str, ohlc["prev_close"])
            self.all_news = fetch_rss_headlines(self.symbol, self.date_str)

            # 2. Reset Broker & Trackers
            self.broker = PaperBroker(self.initial_amount, self.symbol, self.stop_loss_pct)
            self.current_index = 0
            self.status = "RUNNING"
            self.closes_so_far = []
            self.buy_markers = []
            self.sell_markers = []
            self.latest_agents = {
                "trend": {"signal": "HOLD", "confidence": 0.5, "reason": "Awaiting market open indicators"},
                "news": {"signal": "HOLD", "confidence": 0.5, "reason": "Scanning morning headlines"},
                "contrarian": {"signal": "HOLD", "confidence": 0.5, "reason": "Checking statistical range"}
            }
            self.latest_decision = {"action": "HOLD", "size": "none", "rule": "Market opening setup"}
            self.journal = []
            self.journal_map = {}
            self.summary = None
            self.pending_order = None
            self.speed_sleep = 0.0 if fast_mode else CANDLE_INTERVAL_REAL_SEC

        # Launch background runner
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def kill_simulation(self):
        with self.lock:
            if self.status != "RUNNING":
                return
            self.status = "KILLED"
            curr_candle = self.candles_1m[self.current_index] if self.candles_1m else {"close": 0.0, "time": "15:30"}
            curr_p = curr_candle["close"]
            time_str = curr_candle["time"]

            # If holding, force close position
            if self.broker and self.broker.position:
                key = self.broker.get_private_key()
                trade = self.broker.execute_sell(curr_p, time_str, "KILLED by user", key)
                self.sell_markers.append({
                    "time": time_str,
                    "price": curr_p,
                    "pnl": trade.get("net_pnl", 0.0),
                    "reason": "Emergency Kill Switch"
                })

            # Record Kill in Journal
            rec = {
                "time": time_str,
                "price": curr_p,
                "action": "SELL",
                "event_type": "KILL",
                "symbol": self.symbol,
                "rule": "Emergency Kill Switch Activated",
                "fill": curr_p
            }
            entry_id = str(uuid.uuid4())[:8]
            tpl_text = generate_template_reason(rec)
            j_entry = {
                "id": entry_id,
                "time": time_str,
                "action": "SELL",
                "reason": tpl_text,
                "source": "TEMPLATE",
                "is_hold": False
            }
            self.journal.insert(0, j_entry)
            self.journal_map[entry_id] = j_entry
            async_rewrite_narrative(entry_id, rec, self.journal_map)

            self._compute_summary()
            self._stop_event.set()

    def _step_candle(self, i: int):
        candle = self.candles_1m[i]
        time_str = candle["time"]
        candle_open = candle["open"]
        candle_close = candle["close"]
        auth_key = self.broker.get_private_key()

        # -------------------------------------------------------------
        # STEP 1: Execute Pending Orders from previous decision at OPEN (+2 bps slippage)
        # -------------------------------------------------------------
        if self.pending_order:
            order = self.pending_order
            self.pending_order = None
            if order["action"] == "BUY" and not self.broker.position:
                can_b, reason = self.broker.can_buy(i)
                if can_b:
                    fill_price = round_tick(candle_open * (1.0 + SLIPPAGE_BPS))
                    qty, q_reason = self.broker.calculate_position_size(fill_price, order["size"])
                    if qty >= 1:
                        pos = self.broker.execute_buy(fill_price, qty, time_str, order.get("entry_type", "trend"), auth_key)
                        self.buy_markers.append({
                            "time": time_str,
                            "price": fill_price,
                            "qty": qty,
                            "stop_loss": pos["stop_loss"]
                        })
                    else:
                        # Log skip
                        rec = {"time": time_str, "price": fill_price, "action": "HOLD", "event_type": "DECISION", "rule": f"Skipped trade: {q_reason}"}
                        entry_id = str(uuid.uuid4())[:8]
                        j_entry = {"id": entry_id, "time": time_str, "action": "HOLD", "reason": q_reason, "source": "TEMPLATE", "is_hold": True}
                        self.journal.insert(0, j_entry)
                        self.journal_map[entry_id] = j_entry
            elif order["action"] == "SELL" and self.broker.position:
                fill_price = round_tick(candle_open * (1.0 - SLIPPAGE_BPS))
                trade = self.broker.execute_sell(fill_price, time_str, order.get("rule", "Council Exit"), auth_key)
                self.sell_markers.append({
                    "time": time_str,
                    "price": fill_price,
                    "pnl": trade.get("net_pnl", 0.0),
                    "reason": order.get("rule", "")
                })

        # -------------------------------------------------------------
        # STEP 2: Check Stop-Loss on this 1-minute candle
        # -------------------------------------------------------------
        sl_trade = self.broker.check_stop_loss_on_candle(candle, i)
        if sl_trade:
            self.sell_markers.append({
                "time": time_str,
                "price": sl_trade["sell_price"],
                "pnl": sl_trade["net_pnl"],
                "reason": "Stop-Loss Hit"
            })
            rec = {
                "time": time_str,
                "price": sl_trade["sell_price"],
                "stop": sl_trade["sell_price"],
                "pnl": sl_trade["net_pnl"],
                "action": "SELL",
                "event_type": "STOP_LOSS",
                "rule": f"Stop loss triggered at ₹{sl_trade['sell_price']:.2f}"
            }
            entry_id = str(uuid.uuid4())[:8]
            tpl_text = generate_template_reason(rec)
            j_entry = {"id": entry_id, "time": time_str, "action": "SELL", "reason": tpl_text, "source": "TEMPLATE", "is_hold": False}
            self.journal.insert(0, j_entry)
            self.journal_map[entry_id] = j_entry
            async_rewrite_narrative(entry_id, rec, self.journal_map)

        # -------------------------------------------------------------
        # STEP 3: Check 15:15 Intraday Square-Off
        # -------------------------------------------------------------
        if time_str >= SQUARE_OFF_TIME and self.broker.position:
            sq_trade = self.broker.execute_sell(candle_close, time_str, "Intraday Square-off at 15:15", auth_key)
            self.sell_markers.append({
                "time": time_str,
                "price": candle_close,
                "pnl": sq_trade["net_pnl"],
                "reason": "Intraday Square-off (15:15)"
            })
            rec = {
                "time": time_str,
                "price": candle_close,
                "pnl": sq_trade["net_pnl"],
                "action": "SELL",
                "event_type": "SQUARE_OFF",
                "rule": "15:15 IST Mandatory Intraday Square-Off"
            }
            entry_id = str(uuid.uuid4())[:8]
            tpl_text = generate_template_reason(rec)
            j_entry = {"id": entry_id, "time": time_str, "action": "SELL", "reason": tpl_text, "source": "TEMPLATE", "is_hold": False}
            self.journal.insert(0, j_entry)
            self.journal_map[entry_id] = j_entry
            async_rewrite_narrative(entry_id, rec, self.journal_map)

        # -------------------------------------------------------------
        # STEP 4: Check Hard 2% Daily Loss Limit
        # -------------------------------------------------------------
        if self.broker.evaluate_daily_loss_limit(candle_close):
            if self.broker.position:
                self.broker.execute_sell(candle_close, time_str, "Daily Loss Limit (2%) Hit", auth_key)
            rec = {"time": time_str, "price": candle_close, "action": "SELL", "event_type": "DAILY_LOSS_HALT", "rule": "Daily Loss Limit (2%) Circuit Breaker"}
            entry_id = str(uuid.uuid4())[:8]
            tpl = generate_template_reason(rec)
            j_entry = {"id": entry_id, "time": time_str, "action": "SELL", "reason": tpl, "source": "TEMPLATE", "is_hold": False}
            self.journal.insert(0, j_entry)
            self.journal_map[entry_id] = j_entry
            async_rewrite_narrative(entry_id, rec, self.journal_map)

        # -------------------------------------------------------------
        # STEP 5: Decisions on CLOSED 5-minute bars (09:30, 09:35 ... 15:10)
        # -------------------------------------------------------------
        # 09:15 is index 0. Minute 14 is 09:29. 09:30 is index 15 (closes 3rd 5m bar).
        # We decide on closed 5m bars when (i + 1) % 5 == 0 and time_str >= "09:30" and time_str <= "15:10"
        is_5m_bar_close = ((i + 1) % 5 == 0) and (time_str >= "09:30") and (time_str <= "15:10")
        if is_5m_bar_close and not self.broker.is_halted_loss_limit and not self.broker.is_killed:
            closed_candles = self.candles_1m[: i + 1]
            indicators = compute_indicators(self.prior_day_1m, closed_candles)
            is_holding = (self.broker.position is not None)
            entry_type = self.broker.position.get("entry_type", "trend") if is_holding else None
            entry_price = self.broker.position.get("buy_price") if is_holding else None

            # Simulated IST datetime for news filtering
            sim_dt = datetime.datetime.strptime(f"{self.date_str} {time_str}", "%Y-%m-%d %H:%M")
            ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            sim_dt = sim_dt.replace(tzinfo=ist_tz)

            # Evaluate 3 agents
            trend_res = evaluate_trend_agent(indicators, is_holding)
            news_res = evaluate_news_agent(self.all_news, sim_dt)
            contrarian_res = evaluate_contrarian_agent(indicators, is_holding, entry_type, entry_price)

            self.latest_agents = {
                "trend": trend_res,
                "news": news_res,
                "contrarian": contrarian_res
            }

            decision = decide_action(trend_res, news_res, contrarian_res, is_holding, entry_type)
            self.latest_decision = decision

            # Queue pending orders for next candle OPEN
            if decision["action"] == "BUY" and time_str >= ENTRY_START_TIME and time_str <= ENTRY_END_TIME:
                self.pending_order = {
                    "action": "BUY",
                    "size": decision["size"],
                    "rule": decision["rule"],
                    "entry_type": decision.get("entry_type", "trend")
                }
            elif decision["action"] == "SELL" and is_holding:
                self.pending_order = {
                    "action": "SELL",
                    "size": "full",
                    "rule": decision["rule"]
                }

            # Journal entry for EVERY 5-minute decision
            rec = {
                "time": time_str,
                "price": candle_close,
                "action": decision["action"],
                "size": decision["size"],
                "rule": decision["rule"],
                "event_type": "DECISION",
                "trend_reason": trend_res["reason"],
                "news_reason": news_res["reason"],
                "contrarian_reason": contrarian_res["reason"]
            }
            if is_holding and self.broker.position:
                rec["stop"] = self.broker.position["stop_loss"]

            entry_id = str(uuid.uuid4())[:8]
            tpl_text = generate_template_reason(rec)
            j_entry = {
                "id": entry_id,
                "time": time_str,
                "action": decision["action"],
                "reason": tpl_text,
                "source": "TEMPLATE",
                "is_hold": (decision["action"] == "HOLD")
            }
            self.journal.insert(0, j_entry)
            self.journal_map[entry_id] = j_entry
            async_rewrite_narrative(entry_id, rec, self.journal_map)

        # -------------------------------------------------------------
        # STEP 6: Mark Equity at Candle Close & Record Point
        # -------------------------------------------------------------
        self.closes_so_far.append({
            "time": time_str,
            "price": candle_close
        })
        self.current_index = i

    def _compute_summary(self):
        curr_p = self.closes_so_far[-1]["price"] if self.closes_so_far else 0.0
        final_equity = self.broker.get_equity(curr_p) if self.broker else self.initial_amount
        net_pnl = self.broker.get_day_pnl(curr_p) if self.broker else 0.0
        trades = self.broker.closed_trades if self.broker else []
        wins = sum(1 for t in trades if t["net_pnl"] > 0)
        
        # Buy & Hold return for comparison
        if self.candles_1m:
            first_p = self.candles_1m[0]["open"]
            last_p = curr_p
            bh_return_pct = round(((last_p - first_p) / first_p) * 100.0, 2)
        else:
            bh_return_pct = 0.0

        # Verify books reconcile
        if self.broker:
            reconciled, diff, exp = self.broker.reconcile_books(curr_p)
        else:
            reconciled = True

        self.summary = {
            "total_trades": len(trades),
            "wins": wins,
            "losses": len(trades) - wins,
            "win_rate_pct": round((wins / max(1, len(trades))) * 100.0, 1),
            "starting_amount": self.initial_amount,
            "final_equity": final_equity,
            "net_pnl": net_pnl,
            "return_pct": round((net_pnl / self.initial_amount) * 100.0, 2),
            "buy_and_hold_return_pct": bh_return_pct,
            "reconciled": reconciled,
            "closed_trades": trades
        }

    def _run_loop(self):
        for i in range(len(self.candles_1m)):
            if self._stop_event.is_set():
                break

            with self.lock:
                self._step_candle(i)

            if i == len(self.candles_1m) - 1:
                with self.lock:
                    self.status = "DONE"
                    self._compute_summary()
                break

            if self.speed_sleep > 0:
                time.sleep(self.speed_sleep)

    def get_state(self) -> Dict[str, Any]:
        with self.lock:
            curr_candle = self.candles_1m[self.current_index] if self.candles_1m and self.current_index < len(self.candles_1m) else None
            curr_p = curr_candle["close"] if curr_candle else 0.0
            sim_time = curr_candle["time"] if curr_candle else "09:15"

            equity = self.broker.get_equity(curr_p) if self.broker else self.initial_amount
            cash = self.broker.cash if self.broker else self.initial_amount
            day_pnl = self.broker.get_day_pnl(curr_p) if self.broker else 0.0

            position_data = None
            active_stop = None
            if self.broker and self.broker.position:
                pos = self.broker.position
                pnl = round((curr_p - pos["buy_price"]) * pos["qty"] - pos["buy_fees"], 2)
                active_stop = pos["stop_loss"]
                position_data = {
                    "symbol": pos["symbol"],
                    "qty": pos["qty"],
                    "buy_price": pos["buy_price"],
                    "buy_time": pos["buy_time"],
                    "current_price": curr_p,
                    "stop_loss": active_stop,
                    "profit_loss": pnl,
                    "entry_type": pos["entry_type"]
                }

            return {
                "status": self.status,
                "symbol": self.symbol,
                "data_source": self.data_source,
                "date": self.date_str,
                "simulated_time": sim_time,
                "current_index": self.current_index,
                "total_candles": len(self.candles_1m),
                "current_price": curr_p,
                "equity": equity,
                "cash": round(cash, 2),
                "day_pnl": day_pnl,
                "position": position_data,
                "active_stop_loss": active_stop,
                "closes_so_far": self.closes_so_far,
                "buy_markers": self.buy_markers,
                "sell_markers": self.sell_markers,
                "latest_agents": self.latest_agents,
                "latest_decision": self.latest_decision,
                "journal": self.journal[:50],  # Latest 50 entries
                "summary": self.summary,
                "llm_status": {"last_error": get_last_llm_error()}
            }

# Singleton instance
engine = SimulationEngine()

