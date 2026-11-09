import time
import threading
import datetime
import uuid
from typing import Dict, Any, Optional, List
from simulation.config import (
    DEFAULT_CONFIG, TOTAL_DAY_CANDLES, CANDLE_INTERVAL_REAL_SEC,
    ENTRY_START_TIME, ENTRY_END_TIME, SQUARE_OFF_TIME, SLIPPAGE_BPS
)
from simulation.market_data import (
    fetch_daily_ohlc, generate_intraday_candles, generate_fake_prior_day_candles,
    fetch_5min_candles, is_within_5min_window, _resample_1m_to_5m_candles
)
from simulation.indicators import compute_indicators
from simulation.news import fetch_rss_headlines, evaluate_news_agent
from simulation.agents import (
    evaluate_agent1, evaluate_agent3,
    evaluate_orb_vwap_agent, evaluate_vwap_reversion_agent,
    evaluate_trend_agent, evaluate_contrarian_agent
)
from simulation.decision import decide_action
from simulation.agent_config import agent_config_manager
from simulation.broker import PaperBroker, round_tick, compute_round_trip_cost
from simulation.regime import detect_regime
from simulation.llm import generate_template_reason, async_rewrite_narrative, get_last_llm_error

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

class SimulationEngine:
    """
    Orchestrates the intraday paper-trading simulator for a full day (09:15 - 15:30).
    Replays 5-minute bars with continuous graded multi-agent scoring and council execution.
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

        # Real data tracking
        self.is_real_data = False
        self.data_banner = ""
        self.candle_granularity = "5m"
        self.avg_opening_volume = 0.0

        # Candles & Index
        self.candles_1m: List[Dict[str, Any]] = []
        self.prior_day_1m: List[Dict[str, Any]] = []
        self.all_news: List[Dict[str, Any]] = []
        self.current_index = 0
        self.speed_sleep = 6.0

        # ORB & Strategy tracking
        self.orb_entry_done = False
        self.highest_close_since_entry = 0.0
        self.entry_time_str: Optional[str] = None
        self.current_regime = "UNCLEAR"
        self.orb_high = 0.0
        self.orb_low = 0.0
        self.agent_mode = "combined"
        self.current_indicators: Dict[str, Any] = {}

        # Broker
        self.broker: Optional[PaperBroker] = None

        # Tracking for UI
        self.closes_so_far: List[Dict[str, Any]] = []
        self.buy_markers: List[Dict[str, Any]] = []
        self.sell_markers: List[Dict[str, Any]] = []
        self.trade_connections: List[Dict[str, Any]] = []
        self.current_trade_id: Optional[str] = None
        self.latest_agents: Dict[str, Any] = {}
        self.latest_decision: Dict[str, Any] = {}
        self.journal: List[Dict[str, Any]] = []
        self.journal_map: Dict[str, Any] = {}
        self.summary: Optional[Dict[str, Any]] = None

        # Order queues for NO LOOKAHEAD execution (decided at T, fills at T+1 open)
        self.pending_order: Optional[Dict[str, Any]] = None

    def start_simulation(
        self,
        symbol: str,
        amount: float,
        stop_loss_pct: float,
        target_date_str: Optional[str] = None,
        fast_mode: bool = False,
        agent_mode: str = "combined"
    ):
        with self.lock:
            if self.thread and self.thread.is_alive():
                self._stop_event.set()
                self.thread.join(timeout=2.0)

            self._stop_event.clear()
            self.symbol = symbol if "." in symbol else f"{symbol}.NS"
            self.initial_amount = float(amount)
            self.stop_loss_pct = float(stop_loss_pct)
            self.agent_mode = agent_mode

            resolved_date = target_date_str or datetime.date.today().strftime("%Y-%m-%d")
            candles_5m, warmup_5m, is_real, data_banner, avg_opening_volume = fetch_5min_candles(
                self.symbol, resolved_date
            )
            self.is_real_data = is_real
            self.data_banner = data_banner
            self.avg_opening_volume = avg_opening_volume
            self.orb_entry_done = False
            self.highest_close_since_entry = 0.0
            self.entry_time_str = None
            self.current_regime = "UNCLEAR"
            self.orb_high = 0.0
            self.orb_low = 0.0

            if candles_5m:
                self.candles_1m = candles_5m
                self.prior_day_1m = warmup_5m
                self.data_source = data_banner
                self.date_str = resolved_date
                self.candle_granularity = "5m"
                self.speed_sleep = 0.0 if fast_mode else 6.0
            else:
                ohlc, data_source, resolved_date = fetch_daily_ohlc(self.symbol, target_date_str)
                self.data_source = data_banner if data_banner else data_source
                self.date_str = resolved_date
                self.candles_1m = generate_intraday_candles(self.symbol, self.date_str, ohlc)
                self.prior_day_1m = generate_fake_prior_day_candles(self.symbol, self.date_str, ohlc["prev_close"])
                self.candle_granularity = "1m"
                self.speed_sleep = 0.0 if fast_mode else CANDLE_INTERVAL_REAL_SEC

            self.all_news = fetch_rss_headlines(self.symbol, self.date_str)

            # Reset Broker & Trackers
            self.broker = PaperBroker(self.initial_amount, self.symbol, self.stop_loss_pct)
            self.current_index = 0
            self.status = "RUNNING"
            self.closes_so_far = []
            self.buy_markers = []
            self.sell_markers = []
            self.trade_connections = []
            self.current_trade_id = None
            self.latest_agents = {
                "trend": {"status": "ANALYSING", "signal": "HOLD", "score": 0.0, "confidence": 0, "reason": "Awaiting opening range (first 15 min)"},
                "news": {"status": "HOLD", "signal": "HOLD", "score": 0.0, "confidence": 0, "reason": "Scanning news feeds"},
                "contrarian": {"status": "HOLD", "signal": "HOLD", "score": 0.0, "confidence": 0, "reason": "Checking VWAP deviation"},
                "council": {"status": "HOLD", "final_decision": "HOLD", "score": 0.0, "confidence": 0, "approved": False, "approved_quantity": 0, "approved_stop_loss": 0.0}
            }
            self.latest_decision = {"action": "HOLD", "size": "none", "rule": "Market opening setup", "score": 0.0, "confidence": 0}
            self.journal = []
            self.journal_map = {}
            self.summary = None
            self.pending_order = None

        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def kill_simulation(self, mode: str = "flatten"):
        """
        Emergency Kill Switch.
        mode="stop_new": Halts opening of new positions while letting current position run with SL/TP.
        mode="flatten": Emergency market liquidation of open positions and halts all trading.
        """
        with self.lock:
            if self.status != "RUNNING":
                return

            curr_candle = self.candles_1m[self.current_index] if self.candles_1m and self.current_index < len(self.candles_1m) else {"close": 0.0, "time": "15:30"}
            curr_p = curr_candle["close"]
            time_str = curr_candle["time"]

            if mode == "stop_new":
                if self.broker:
                    self.broker.stop_new_trades_only = True
                if self.pending_order and self.pending_order.get("action") in ("BUY", "SHORT"):
                    self.pending_order = None

                rec = {
                    "time": time_str,
                    "price": curr_p,
                    "action": "HOLD",
                    "event_type": "KILL_STOP_NEW",
                    "symbol": self.symbol,
                    "rule": "Kill Switch (Stop New Trades): New order entries paused; active position managed by SL/TP",
                    "fill": curr_p
                }
                entry_id = str(uuid.uuid4())[:8]
                tpl_text = generate_template_reason(rec)
                j_entry = {
                    "id": entry_id,
                    "time": time_str,
                    "action": "HOLD",
                    "reason": tpl_text,
                    "source": "TEMPLATE",
                    "is_hold": True
                }
                self.journal.insert(0, j_entry)
                self.journal_map[entry_id] = j_entry
                return

            # Default: Emergency Flatten
            self.status = "KILLED"
            if self.broker:
                self.broker.is_killed = True
                # Emergency flatten open position if holding
                if self.broker.position:
                    flatten_reason = "Emergency Flatten: Market Closed by Kill Switch"
                    flat_trade = self.broker.execute_sell(
                        curr_p, time_str, flatten_reason, self.broker.get_private_key(), self.current_index
                    )
                    trade_id = self.current_trade_id or str(uuid.uuid4())[:8]
                    self.current_trade_id = None
                    candle_ts = curr_candle.get("timestamp") or (1700000000 + self.current_index * 300)
                    self.sell_markers.append({
                        "id": f"sell-{trade_id}",
                        "trade_id": trade_id,
                        "time": candle_ts,
                        "time_str": time_str,
                        "timestamp": candle_ts,
                        "price": curr_p,
                        "qty": flat_trade.get("qty", 0),
                        "pnl": flat_trade.get("net_pnl", 0.0),
                        "gross_pnl": flat_trade.get("gross_pnl", 0.0),
                        "fees": flat_trade.get("total_fees", 0.0),
                        "agent_name": "Emergency Flatten",
                        "agent_tag": "Kill Switch",
                        "action": "SELL",
                        "reason": flatten_reason,
                        "buy_price": flat_trade.get("buy_price", 0.0),
                        "buy_time": flat_trade.get("buy_time", ""),
                        "sell_time": time_str,
                        "holding_duration": "Flattened",
                        "symbol": self.symbol
                    })

            self.pending_order = None

            rec = {
                "time": time_str,
                "price": curr_p,
                "action": "HOLD",
                "event_type": "KILL",
                "symbol": self.symbol,
                "rule": "Emergency Kill Switch Activated: all pending orders cancelled, positions flattened, simulation stopped",
                "fill": curr_p
            }
            entry_id = str(uuid.uuid4())[:8]
            tpl_text = generate_template_reason(rec)
            j_entry = {
                "id": entry_id,
                "time": time_str,
                "action": "HOLD",
                "reason": tpl_text,
                "source": "TEMPLATE",
                "is_hold": True
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
        indicators = self.current_indicators

        candle_ts = candle.get("timestamp")
        if not isinstance(candle_ts, int):
            try:
                ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
                dt = datetime.datetime.strptime(f"{self.date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=ist_tz)
                candle_ts = int(dt.timestamp())
            except Exception:
                candle_ts = 1700000000 + i * 300

        # =============================================================
        # STEP 1: MANAGE OPEN POSITION BEFORE EVALUATING NEW ENTRIES
        # =============================================================
        
        # 1.1 Check Stop-Loss, Take-Profit (1.5R) and Breakeven Trailing (+1R)
        st_trade = self.broker.check_stop_and_target_on_candle(candle, i)
        if st_trade:
            trade_id = self.current_trade_id or str(uuid.uuid4())[:8]
            self.current_trade_id = None
            duration_str = compute_holding_duration(st_trade.get("buy_time", ""), time_str)
            action_tag = "Stop-Loss Risk Trigger" if st_trade.get("is_stop_loss") else "Take-Profit Target (1.5R)"

            self.sell_markers.append({
                "id": f"sell-{trade_id}",
                "trade_id": trade_id,
                "time": candle_ts,
                "time_str": time_str,
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
                "sell_time": time_str,
                "holding_duration": duration_str,
                "symbol": self.symbol
            })
            self.trade_connections.append({
                "trade_id": trade_id,
                "symbol": self.symbol,
                "entry_time": st_trade.get("buy_time", ""),
                "entry_price": st_trade.get("buy_price", 0.0),
                "exit_time": time_str,
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
                "time": time_str,
                "price": st_trade["sell_price"],
                "stop": st_trade["sell_price"],
                "pnl": st_trade["net_pnl"],
                "action": "SELL",
                "event_type": "STOP_LOSS" if st_trade.get("is_stop_loss") else "TAKE_PROFIT",
                "rule": st_trade["reason"]
            }
            entry_id = str(uuid.uuid4())[:8]
            tpl_text = generate_template_reason(rec)
            j_entry = {"id": entry_id, "time": time_str, "action": "SELL", "reason": tpl_text, "source": "TEMPLATE", "is_hold": False}
            self.journal.insert(0, j_entry)
            self.journal_map[entry_id] = j_entry
            async_rewrite_narrative(entry_id, rec, self.journal_map)

        # 1.2 Check 15:15 IST Mandatory Intraday Square-Off
        if time_str >= SQUARE_OFF_TIME and self.broker.position:
            exit_reason = "15:15 IST Mandatory Intraday Square-Off"
            sq_trade = self.broker.execute_sell(candle_close, time_str, exit_reason, auth_key, i)
            trade_id = self.current_trade_id or str(uuid.uuid4())[:8]
            self.current_trade_id = None
            duration_str = compute_holding_duration(sq_trade.get("buy_time", ""), time_str)

            self.sell_markers.append({
                "id": f"sell-{trade_id}",
                "trade_id": trade_id,
                "time": candle_ts,
                "time_str": time_str,
                "timestamp": candle_ts,
                "price": candle_close,
                "qty": sq_trade.get("qty", 0),
                "pnl": sq_trade["net_pnl"],
                "gross_pnl": sq_trade.get("gross_pnl", 0.0),
                "entry_fees": sq_trade.get("buy_fees", 0.0),
                "exit_fees": sq_trade.get("sell_fees", 0.0),
                "fees": sq_trade.get("total_fees", 0.0),
                "agent_name": "15:15 IST Square-Off Trigger",
                "agent_tag": "Risk Management",
                "action": "SELL",
                "reason": exit_reason,
                "buy_price": sq_trade.get("buy_price", 0.0),
                "buy_time": sq_trade.get("buy_time", ""),
                "sell_time": time_str,
                "holding_duration": duration_str,
                "symbol": self.symbol
            })
            self.trade_connections.append({
                "trade_id": trade_id,
                "symbol": self.symbol,
                "entry_time": sq_trade.get("buy_time", ""),
                "entry_price": sq_trade.get("buy_price", 0.0),
                "exit_time": time_str,
                "exit_price": candle_close,
                "qty": sq_trade.get("qty", 0),
                "pnl": sq_trade["net_pnl"],
                "gross_pnl": sq_trade.get("gross_pnl", 0.0),
                "fees": sq_trade.get("total_fees", 0.0),
                "agent_name": "15:15 IST Square-Off Trigger",
                "agent_tag": "Risk Management",
                "reason": exit_reason
            })
            rec = {"time": time_str, "price": candle_close, "pnl": sq_trade["net_pnl"], "action": "SELL", "event_type": "SQUARE_OFF", "rule": exit_reason}
            entry_id = str(uuid.uuid4())[:8]
            tpl_text = generate_template_reason(rec)
            j_entry = {"id": entry_id, "time": time_str, "action": "SELL", "reason": tpl_text, "source": "TEMPLATE", "is_hold": False}
            self.journal.insert(0, j_entry)
            self.journal_map[entry_id] = j_entry
            async_rewrite_narrative(entry_id, rec, self.journal_map)

        # 1.3 Check Hard 2% Daily Loss Limit Circuit Breaker
        if self.broker.evaluate_daily_loss_limit(candle_close):
            if self.broker.position:
                exit_reason = "Daily Loss Limit (2%) Circuit Breaker"
                dl_trade = self.broker.execute_sell(candle_close, time_str, exit_reason, auth_key, i)
                trade_id = self.current_trade_id or str(uuid.uuid4())[:8]
                self.current_trade_id = None
                duration_str = compute_holding_duration(dl_trade.get("buy_time", ""), time_str)
                self.sell_markers.append({
                    "id": f"sell-{trade_id}",
                    "trade_id": trade_id,
                    "time": candle_ts,
                    "time_str": time_str,
                    "timestamp": candle_ts,
                    "price": candle_close,
                    "qty": dl_trade.get("qty", 0),
                    "pnl": dl_trade["net_pnl"],
                    "gross_pnl": dl_trade.get("gross_pnl", 0.0),
                    "entry_fees": dl_trade.get("buy_fees", 0.0),
                    "exit_fees": dl_trade.get("sell_fees", 0.0),
                    "fees": dl_trade.get("total_fees", 0.0),
                    "agent_name": "Daily Loss Circuit Breaker",
                    "agent_tag": "Risk Management",
                    "action": "SELL",
                    "reason": exit_reason,
                    "buy_price": dl_trade.get("buy_price", 0.0),
                    "buy_time": dl_trade.get("buy_time", ""),
                    "sell_time": time_str,
                    "holding_duration": duration_str,
                    "symbol": self.symbol
                })
            rec = {"time": time_str, "price": candle_close, "action": "SELL", "event_type": "DAILY_LOSS_HALT", "rule": "Daily Loss Limit (2%) Circuit Breaker"}
            entry_id = str(uuid.uuid4())[:8]
            tpl = generate_template_reason(rec)
            j_entry = {"id": entry_id, "time": time_str, "action": "SELL", "reason": tpl, "source": "TEMPLATE", "is_hold": False}
            self.journal.insert(0, j_entry)
            self.journal_map[entry_id] = j_entry
            async_rewrite_narrative(entry_id, rec, self.journal_map)

        # =============================================================
        # STEP 2: EXECUTE PENDING ORDERS FROM PREVIOUS DECISION (AT OPEN)
        # =============================================================
        if self.pending_order and not self.broker.is_halted_loss_limit and not self.broker.is_killed:
            order = self.pending_order
            self.pending_order = None
            action = order["action"]
            atr = float(order.get("atr", 0.0))

            if action == "BUY" and not self.broker.position:
                # LONG Entry
                can_t, reason = self.broker.can_trade(i, "LONG")
                if can_t:
                    fill_price = round_tick(candle_open * (1.0 + SLIPPAGE_BPS))
                    qty, q_reason = self.broker.calculate_position_size(fill_price, order["size"], atr=atr)
                    if qty >= 1:
                        # Cost filter: expected gain >= 1.5x round trip fees
                        stop_dist = self.broker.calculate_stop_distance(fill_price, atr)
                        expected_gain = (stop_dist * DEFAULT_CONFIG.take_profit_r_multiple) * qty
                        rt_fees = compute_round_trip_cost(fill_price, qty)

                        if expected_gain < (DEFAULT_CONFIG.cost_filter_multiplier * rt_fees):
                            skip_msg = f"Skipped cost filter: expected gain ₹{expected_gain:.2f} < {DEFAULT_CONFIG.cost_filter_multiplier}x round-trip cost ₹{DEFAULT_CONFIG.cost_filter_multiplier * rt_fees:.2f}"
                            rec = {"time": time_str, "price": fill_price, "action": "HOLD", "event_type": "DECISION", "rule": skip_msg}
                            entry_id = str(uuid.uuid4())[:8]
                            j_entry = {"id": entry_id, "time": time_str, "action": "HOLD", "reason": skip_msg, "source": "TEMPLATE", "is_hold": True}
                            self.journal.insert(0, j_entry)
                            self.journal_map[entry_id] = j_entry
                        else:
                            entry_type = order.get("entry_type", "orb")
                            pos = self.broker.execute_buy(fill_price, qty, time_str, entry_type, auth_key, atr=atr)
                            self.highest_close_since_entry = fill_price
                            self.entry_time_str = time_str
                            if entry_type == "orb":
                                self.orb_entry_done = True

                            trade_id = str(uuid.uuid4())[:8]
                            self.current_trade_id = trade_id
                            agent_name = "Agent 1: ORB + VWAP Trend" if entry_type == "orb" else ("Agent 3: VWAP Reversion" if entry_type == "reversion" else "Council Consensus Gate")
                            agent_tag = "Agent 1 (ORB)" if entry_type == "orb" else ("Agent 3 (Reversion)" if entry_type == "reversion" else "Council")
                            risk_amount = round(abs(fill_price - pos["stop_loss"]) * qty, 2)
                            rule_text = order.get("rule", "Council Consensus BUY")

                            self.buy_markers.append({
                                "id": f"buy-{trade_id}",
                                "trade_id": trade_id,
                                "time": candle_ts,
                                "time_str": time_str,
                                "timestamp": candle_ts,
                                "price": fill_price,
                                "qty": qty,
                                "stop_loss": pos["stop_loss"],
                                "risk_amount": risk_amount,
                                "agent_name": agent_name,
                                "agent_tag": agent_tag,
                                "action": "BUY",
                                "reason": rule_text,
                                "fees": pos["buy_fees"],
                                "symbol": self.symbol,
                                "pnl": None
                            })

                            if "council" in self.latest_agents:
                                self.latest_agents["council"]["status"] = "EXECUTED"

                            buy_rec = {
                                "time": time_str,
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
                            buy_id = str(uuid.uuid4())[:8]
                            buy_tpl = generate_template_reason(buy_rec)
                            buy_j = {"id": buy_id, "time": time_str, "action": "BUY", "reason": buy_tpl, "source": "TEMPLATE", "is_hold": False}
                            self.journal.insert(0, buy_j)
                            self.journal_map[buy_id] = buy_j
                            async_rewrite_narrative(buy_id, buy_rec, self.journal_map)
                    else:
                        skip_msg = f"Skipped: allowed size is 0 shares because {q_reason}"
                        rec = {"time": time_str, "price": fill_price, "action": "HOLD", "event_type": "DECISION", "rule": skip_msg}
                        entry_id = str(uuid.uuid4())[:8]
                        j_entry = {"id": entry_id, "time": time_str, "action": "HOLD", "reason": skip_msg, "source": "TEMPLATE", "is_hold": True}
                        self.journal.insert(0, j_entry)
                        self.journal_map[entry_id] = j_entry
                else:
                    skip_msg = f"Skipped: order blocked by risk gate — {reason}"
                    rec = {"time": time_str, "price": candle_open, "action": "HOLD", "event_type": "DECISION", "rule": skip_msg}
                    entry_id = str(uuid.uuid4())[:8]
                    j_entry = {"id": entry_id, "time": time_str, "action": "HOLD", "reason": skip_msg, "source": "TEMPLATE", "is_hold": True}
                    self.journal.insert(0, j_entry)
                    self.journal_map[entry_id] = j_entry

            elif action == "SHORT" and not self.broker.position:
                # SHORT Entry
                can_t, reason = self.broker.can_trade(i, "SHORT")
                if can_t:
                    fill_price = round_tick(candle_open * (1.0 - SLIPPAGE_BPS))
                    qty, q_reason = self.broker.calculate_position_size(fill_price, order["size"], atr=atr)
                    if qty >= 1:
                        stop_dist = self.broker.calculate_stop_distance(fill_price, atr)
                        expected_gain = (stop_dist * DEFAULT_CONFIG.take_profit_r_multiple) * qty
                        rt_fees = compute_round_trip_cost(fill_price, qty)

                        if expected_gain < (DEFAULT_CONFIG.cost_filter_multiplier * rt_fees):
                            skip_msg = f"Skipped cost filter: expected gain ₹{expected_gain:.2f} < {DEFAULT_CONFIG.cost_filter_multiplier}x round-trip cost"
                            rec = {"time": time_str, "price": fill_price, "action": "HOLD", "event_type": "DECISION", "rule": skip_msg}
                            entry_id = str(uuid.uuid4())[:8]
                            j_entry = {"id": entry_id, "time": time_str, "action": "HOLD", "reason": skip_msg, "source": "TEMPLATE", "is_hold": True}
                            self.journal.insert(0, j_entry)
                            self.journal_map[entry_id] = j_entry
                        else:
                            entry_type = order.get("entry_type", "orb")
                            pos = self.broker.execute_short(fill_price, qty, time_str, entry_type, auth_key, atr=atr)
                            self.entry_time_str = time_str
                            trade_id = str(uuid.uuid4())[:8]
                            self.current_trade_id = trade_id
                            agent_name = "Agent 1: ORB + VWAP Trend" if entry_type == "orb" else "Council Consensus Gate"
                            agent_tag = "Agent 1 (ORB Short)" if entry_type == "orb" else "Council (Short)"
                            risk_amount = round(abs(pos["stop_loss"] - fill_price) * qty, 2)
                            rule_text = order.get("rule", "Council Consensus SHORT")

                            # Add marker to chart (action SELL represents short entry marker)
                            self.buy_markers.append({
                                "id": f"short-{trade_id}",
                                "trade_id": trade_id,
                                "time": candle_ts,
                                "time_str": time_str,
                                "timestamp": candle_ts,
                                "price": fill_price,
                                "qty": qty,
                                "stop_loss": pos["stop_loss"],
                                "risk_amount": risk_amount,
                                "agent_name": agent_name,
                                "agent_tag": agent_tag,
                                "action": "BUY",
                                "reason": rule_text,
                                "fees": pos["buy_fees"],
                                "symbol": self.symbol,
                                "pnl": None
                            })

                            if "council" in self.latest_agents:
                                self.latest_agents["council"]["status"] = "EXECUTED"

                            short_rec = {
                                "time": time_str,
                                "price": fill_price,
                                "qty": qty,
                                "fees": pos["buy_fees"],
                                "stop": pos["stop_loss"],
                                "action": "SELL",
                                "event_type": "FILL",
                                "rule": rule_text,
                                "entry_type": entry_type,
                                "symbol": self.symbol
                            }
                            s_id = str(uuid.uuid4())[:8]
                            s_tpl = generate_template_reason(short_rec)
                            s_j = {"id": s_id, "time": time_str, "action": "SELL", "reason": s_tpl, "source": "TEMPLATE", "is_hold": False}
                            self.journal.insert(0, s_j)
                            self.journal_map[s_id] = s_j
                    else:
                        skip_msg = f"Skipped: allowed size is 0 shares because {q_reason}"
                        rec = {"time": time_str, "price": fill_price, "action": "HOLD", "event_type": "DECISION", "rule": skip_msg}
                        entry_id = str(uuid.uuid4())[:8]
                        j_entry = {"id": entry_id, "time": time_str, "action": "HOLD", "reason": skip_msg, "source": "TEMPLATE", "is_hold": True}
                        self.journal.insert(0, j_entry)
                        self.journal_map[entry_id] = j_entry

            elif action in ("SELL", "COVER") and self.broker.position:
                # Closing position (Long exit or Short cover)
                pos = self.broker.position
                side = pos.get("side", "LONG")
                slippage_mult = (1.0 - SLIPPAGE_BPS) if side == "LONG" else (1.0 + SLIPPAGE_BPS)
                fill_price = round_tick(candle_open * slippage_mult)
                exit_rule = order.get("rule", "Council Exit")
                trade = self.broker.execute_sell(fill_price, time_str, exit_rule, auth_key, i)

                agent_name = "Agent 1: ORB + VWAP Trend" if order.get("entry_type") == "orb" else ("Agent 3: VWAP Reversion" if order.get("entry_type") == "reversion" else "Council Consensus Gate")
                agent_tag = "Agent 1 (ORB)" if order.get("entry_type") == "orb" else ("Agent 3 (Reversion)" if order.get("entry_type") == "reversion" else "Council")
                trade_id = self.current_trade_id or str(uuid.uuid4())[:8]
                self.current_trade_id = None
                duration_str = compute_holding_duration(trade.get("buy_time", ""), time_str)

                self.sell_markers.append({
                    "id": f"sell-{trade_id}",
                    "trade_id": trade_id,
                    "time": candle_ts,
                    "time_str": time_str,
                    "timestamp": candle_ts,
                    "price": fill_price,
                    "qty": trade.get("qty", 0),
                    "pnl": trade.get("net_pnl", 0.0),
                    "gross_pnl": trade.get("gross_pnl", 0.0),
                    "entry_fees": trade.get("buy_fees", 0.0),
                    "exit_fees": trade.get("sell_fees", 0.0),
                    "fees": trade.get("total_fees", 0.0),
                    "agent_name": agent_name,
                    "agent_tag": agent_tag,
                    "action": "SELL",
                    "reason": exit_rule,
                    "buy_price": trade.get("buy_price", 0.0),
                    "buy_time": trade.get("buy_time", ""),
                    "sell_time": time_str,
                    "holding_duration": duration_str,
                    "symbol": self.symbol
                })
                self.trade_connections.append({
                    "trade_id": trade_id,
                    "symbol": self.symbol,
                    "entry_time": trade.get("buy_time", ""),
                    "entry_price": trade.get("buy_price", 0.0),
                    "exit_time": time_str,
                    "exit_price": fill_price,
                    "qty": trade.get("qty", 0),
                    "pnl": trade.get("net_pnl", 0.0),
                    "gross_pnl": trade.get("gross_pnl", 0.0),
                    "fees": trade.get("total_fees", 0.0),
                    "agent_name": agent_name,
                    "agent_tag": agent_tag,
                    "reason": exit_rule
                })
                if "council" in self.latest_agents:
                    self.latest_agents["council"]["status"] = "EXECUTED"

        # =============================================================
        # STEP 3: DECISIONS ON CLOSED 5-MINUTE BARS (09:20 ... 15:10)
        # =============================================================
        if self.candle_granularity == "5m":
            is_5m_bar_close = (time_str >= "09:20") and (time_str <= "15:10")
        else:
            is_5m_bar_close = ((i + 1) % 5 == 0) and (time_str >= "09:20") and (time_str <= "15:10")

        if is_5m_bar_close and not self.broker.is_halted_loss_limit and not self.broker.is_killed:
            closed_candles = self.candles_1m[: i + 1]
            if self.candle_granularity == "5m":
                candles_5m_today = closed_candles
            else:
                candles_5m_today = _resample_1m_to_5m_candles(closed_candles, self.date_str)

            # Opening Range: first 3 bars (first 15 min: 09:15, 09:20, 09:25)
            orb_bars = candles_5m_today[:min(3, len(candles_5m_today))]
            if orb_bars:
                self.orb_high = max(float(b["high"]) for b in orb_bars)
                self.orb_low = min(float(b["low"]) for b in orb_bars)

            indicators = compute_indicators(self.prior_day_1m, closed_candles)
            self.current_indicators = indicators
            is_holding = (self.broker.position is not None)
            entry_type = self.broker.position.get("entry_type", "orb") if is_holding else None
            entry_price = self.broker.position.get("buy_price") if is_holding else None
            pos_side = self.broker.position.get("side", "LONG") if is_holding else "LONG"

            # Detect market regime
            current_regime, regime_reason = detect_regime(
                candles_5m_today, self.orb_high, self.orb_low, indicators
            )
            self.current_regime = current_regime

            # Simulated IST datetime for news filtering
            sim_dt = datetime.datetime.strptime(f"{self.date_str} {time_str}", "%Y-%m-%d %H:%M")
            ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
            sim_dt = sim_dt.replace(tzinfo=ist_tz)

            # 3.1 Evaluate Agent 1 (Trend / Breakout with Configurable Strategy)
            trend_res = evaluate_agent1(
                candles_5m_today=candles_5m_today,
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

            # 3.2 Evaluate Agent 2 (News Sentiment & Event Classification)
            news_res = evaluate_news_agent(self.all_news, sim_dt)

            # 3.3 Evaluate Agent 3 (Mean Reversion / Reversal with Configurable Strategy)
            rt_cost_pct = (compute_round_trip_cost(candle_close, 10) / (candle_close * 10)) if candle_close > 0 else 0.001
            contrarian_res = evaluate_agent3(
                candles_5m_today=candles_5m_today,
                indicators=indicators,
                is_holding=is_holding,
                entry_type=entry_type,
                entry_time_str=self.entry_time_str,
                entry_price=entry_price,
                stop_loss_pct=self.stop_loss_pct,
                round_trip_cost_pct=rt_cost_pct,
                position_side=pos_side
            )

            # 3.4 Council Decision via continuous weighted scoring
            decision = decide_action(
                trend_res=trend_res,
                news_res=news_res,
                contrarian_res=contrarian_res,
                is_holding=is_holding,
                entry_type=entry_type,
                regime=current_regime,
                regime_reason=regime_reason,
                agent_mode=self.agent_mode,
                position_side=pos_side
            )
            self.latest_decision = decision

            # 3.5 Format card statuses for UI
            if is_holding:
                t_status = "SELL" if trend_res.get("signal") == "SELL" else "HOLD"
            elif trend_res.get("signal") == "BUY":
                t_status = "BUY" if decision["action"] == "BUY" else "HOLD"
            elif trend_res.get("signal") == "SELL":
                t_status = "SELL" if decision["action"] == "SELL" else "HOLD"
            else:
                t_status = "HOLD"
            trend_res["status"] = t_status
            trend_res["agent_name"] = f"Agent 1: {trend_res.get('strategy_name', 'ORB + VWAP Trend')}"
            trend_res["last_evaluation_time"] = time_str

            n_status = "HOLD"
            if news_res.get("veto_buy") or news_res.get("veto_short"):
                n_status = "BLOCKED"
            elif news_res.get("signal") in ("BUY", "SELL"):
                n_status = news_res.get("signal")
            news_res["status"] = n_status
            news_res["agent_name"] = "Agent 2: News Sentiment"
            news_res["last_evaluation_time"] = time_str
            news_sentiment = news_res.get("score", 0.0)
            news_res["sentiment"] = f"{news_sentiment:+.2f}"
            news_res["in_play"] = (trend_res.get("facts", {}).get("in_play", True) and len(self.all_news) > 0)
            news_res["veto_status"] = "Active VETO: Negative headlines" if news_res.get("veto_buy") else ("Active VETO: Positive headlines" if news_res.get("veto_short") else "None (Clear)")

            if is_holding:
                c3_status = "SELL" if contrarian_res.get("signal") == "SELL" else "HOLD"
            elif contrarian_res.get("signal") == "BUY":
                c3_status = "BUY" if decision["action"] == "BUY" else "HOLD"
            elif contrarian_res.get("signal") == "SELL":
                c3_status = "SELL" if decision["action"] == "SELL" else "HOLD"
            else:
                c3_status = "HOLD"
            contrarian_res["status"] = c3_status
            contrarian_res["agent_name"] = f"Agent 3: {contrarian_res.get('strategy_name', 'VWAP Reversion')}"
            contrarian_res["last_evaluation_time"] = time_str

            # Council status
            approved_qty = 0
            approved_stop = 0.0
            atr_val = indicators.get("atr", 0.0)

            if decision["action"] == "BUY" and not is_holding:
                approved_qty, _ = self.broker.calculate_position_size(candle_close, decision["size"], atr=atr_val)
                stop_dist = self.broker.calculate_stop_distance(candle_close, atr_val)
                approved_stop = round_tick(candle_close - stop_dist)
            elif decision["action"] == "SELL" and not is_holding:
                approved_qty, _ = self.broker.calculate_position_size(candle_close, decision["size"], atr=atr_val)
                stop_dist = self.broker.calculate_stop_distance(candle_close, atr_val)
                approved_stop = round_tick(candle_close + stop_dist)

            if decision["action"] == "BUY":
                council_status = "BUY" if approved_qty >= 1 else "BLOCKED"
            elif decision["action"] == "SELL":
                council_status = "SELL"
            elif decision.get("rejection_reason"):
                council_status = "BLOCKED"
            else:
                council_status = "HOLD"

            council_res = {
                "agent_name": "Council Consensus Gate",
                "status": council_status,
                "final_decision": decision["action"],
                "approved": (decision["approved"] and approved_qty >= 1),
                "rejection_reason": decision.get("rejection_reason", ""),
                "approved_quantity": approved_qty,
                "approved_stop_loss": approved_stop,
                "regime": current_regime,
                "last_evaluation_time": time_str,
                "rule": decision.get("rule", ""),
                "score": decision.get("score", 0.0),
                "confidence": decision.get("confidence", 0.0)
            }

            self.latest_agents = {
                "trend": trend_res,
                "news": news_res,
                "contrarian": contrarian_res,
                "council": council_res
            }

            # 3.6 Queue Pending Orders for next bar OPEN (within entry window)
            if not is_holding and time_str >= ENTRY_START_TIME and time_str <= ENTRY_END_TIME:
                if decision["action"] == "BUY" and approved_qty >= 1:
                    self.pending_order = {
                        "action": "BUY",
                        "size": decision["size"],
                        "rule": decision["rule"],
                        "entry_type": decision.get("entry_type", "orb"),
                        "vwap": indicators.get("vwap", candle_close),
                        "atr": atr_val,
                    }
                elif decision["action"] == "SELL" and approved_qty >= 1:
                    self.pending_order = {
                        "action": "SHORT",
                        "size": decision["size"],
                        "rule": decision["rule"],
                        "entry_type": decision.get("entry_type", "orb"),
                        "vwap": indicators.get("vwap", candle_close),
                        "atr": atr_val,
                    }
            elif is_holding and decision["action"] in ("BUY", "SELL"):
                # Exit signal from council
                self.pending_order = {
                    "action": decision["action"],
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
                "score": decision.get("score", 0.0),
                "confidence": decision.get("confidence", 0.0),
                "orb_score": trend_res.get("score", 0.0),
                "news_score": news_res.get("score", 0.0),
                "vwap_score": contrarian_res.get("score", 0.0),
                "trend_reason": trend_res.get("reason", ""),
                "news_reason": news_res.get("reason", ""),
                "contrarian_reason": contrarian_res.get("reason", "")
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
                "is_hold": (decision["action"] == "HOLD"),
                "score": decision.get("score", 0.0),
                "confidence": decision.get("confidence", 0.0),
                "orb_score": trend_res.get("score", 0.0),
                "news_score": news_res.get("score", 0.0),
                "vwap_score": contrarian_res.get("score", 0.0),
            }
            self.journal.insert(0, j_entry)
            self.journal_map[entry_id] = j_entry
            async_rewrite_narrative(entry_id, rec, self.journal_map)

        # =============================================================
        # STEP 4: MARK EQUITY AT CANDLE CLOSE & RECORD POINT
        # =============================================================
        active_pos = self.broker.position
        active_stop = active_pos["stop_loss"] if active_pos else None
        active_entry = active_pos["buy_price"] if active_pos else None

        candle_buys = [m for m in self.buy_markers if m.get("time_str") == time_str or m.get("timestamp") == candle_ts or m.get("time") == candle_ts]
        candle_sells = [m for m in self.sell_markers if m.get("time_str") == time_str or m.get("timestamp") == candle_ts or m.get("time") == candle_ts]

        self.closes_so_far.append({
            "time": candle_ts,
            "timestamp": candle_ts,
            "time_str": time_str,
            "price": candle_close,
            "open": candle_open,
            "high": candle["high"],
            "low": candle["low"],
            "close": candle_close,
            "volume": int(candle.get("volume", 0)),
            "vwap": round(indicators.get("vwap", candle_close), 2) if indicators else candle_close,
            "orb_high": round(self.orb_high, 2) if self.orb_high > 0 else None,
            "orb_low": round(self.orb_low, 2) if self.orb_low > 0 else None,
            "stop_loss": active_stop,
            "entry_price": active_entry,
            "buyMarker": candle_buys[-1] if candle_buys else None,
            "sellMarker": candle_sells[-1] if candle_sells else None
        })
        self.current_index = i

    def _compute_summary(self):
        curr_p = self.closes_so_far[-1]["price"] if self.closes_so_far else 0.0
        final_equity = self.broker.get_equity(curr_p) if self.broker else self.initial_amount
        net_pnl = self.broker.get_day_pnl(curr_p) if self.broker else 0.0
        trades = self.broker.closed_trades if self.broker else []
        wins = sum(1 for t in trades if t["net_pnl"] > 0)
        
        if self.candles_1m:
            first_p = self.candles_1m[0]["open"]
            last_p = curr_p
            bh_return_pct = round(((last_p - first_p) / first_p) * 100.0, 2)
        else:
            bh_return_pct = 0.0

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
                side = pos.get("side", "LONG")
                if side == "LONG":
                    pnl = round((curr_p - pos["buy_price"]) * pos["qty"] - pos["buy_fees"], 2)
                else:
                    pnl = round((pos["buy_price"] - curr_p) * pos["qty"] - pos["buy_fees"], 2)
                active_stop = pos["stop_loss"]
                position_data = {
                    "symbol": pos["symbol"],
                    "side": side,
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
                "trade_connections": self.trade_connections,
                "latest_agents": self.latest_agents,
                "latest_decision": self.latest_decision,
                "journal": self.journal[:50],
                "summary": self.summary,
                "llm_status": {"last_error": get_last_llm_error()},
                "is_real_data": self.is_real_data,
                "data_banner": self.data_banner,
                "candle_granularity": self.candle_granularity,
                "current_regime": self.current_regime,
                "orb_high": self.orb_high,
                "orb_low": self.orb_low,
                "agent_mode": self.agent_mode,
                "agent_config": agent_config_manager.get_config(),
                "portfolio": self.broker.get_portfolio_state(curr_p) if self.broker else None,
            }

engine = SimulationEngine()
