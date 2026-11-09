"""
broker.py — Paper Broker & Risk Manager.

Enforces:
  - Dynamic volatility-adaptive stop: max(1.5 × ATR(14), minStopPct × price), capped at 1% guardrail.
  - Fallback fixed 0.7% if ATR unavailable.
  - Risk 0.5% of current capital per trade: size = floor((capital × 0.005) / stopDistance),
    capped by available cash and max % of capital per position.
  - Take-profit 1.5R. Stop moved to breakeven after +1R.
  - Support for both BUY (long) and SELL (short) entries.
  - Daily loss circuit breaker at -2% of starting capital.
  - Max 6 trades/day and 3-bar cooldown.
  - Full portfolio ledger state and book reconciliation.
"""
import math
import uuid
from typing import Dict, Any, Optional, List, Tuple
from simulation.config import (
    DEFAULT_CONFIG, TICK_SIZE, SLIPPAGE_BPS,
    DAILY_LOSS_LIMIT_PCT, MAX_BUYS_PER_DAY, STOP_LOSS_COOLDOWN_MINUTES
)

def round_down_tick(price: float, tick: float = TICK_SIZE) -> float:
    return round(math.floor(price / tick + 1e-9) * tick, 2)

def round_tick(price: float, tick: float = TICK_SIZE) -> float:
    return round(round(price / tick) * tick, 2)

def calculate_fees(price: float, qty: int, side: str) -> float:
    """Calculate regulatory and brokerage fees for an execution."""
    if qty <= 0:
        return 0.0
    val = price * qty
    brokerage = min(DEFAULT_CONFIG.brokerage_max, val * DEFAULT_CONFIG.brokerage_pct)
    exchange = val * DEFAULT_CONFIG.exchange_txn_pct
    gst = (brokerage + exchange) * DEFAULT_CONFIG.gst_pct

    if side == "BUY":
        stamp = val * DEFAULT_CONFIG.stamp_duty_buy_pct
        stt = 0.0
    else:
        stamp = 0.0
        stt = val * DEFAULT_CONFIG.stt_sell_pct

    return round(brokerage + exchange + gst + stamp + stt, 2)

def compute_round_trip_cost(price: float, qty: int) -> float:
    """Compute total round-trip brokerage & regulatory fees for a buy and sell."""
    if qty <= 0:
        return 0.0
    return round(calculate_fees(price, qty, "BUY") + calculate_fees(price, qty, "SELL"), 2)


class PaperBroker:
    """
    Paper Broker & Risk Manager.
    Supports LONG and SHORT positions, volatility-adaptive stops, 1.5R targets,
    breakeven trailing, daily loss limit, and exact book reconciliation.
    """
    def __init__(self, initial_cash: float, symbol: str = "TCS.NS", stop_loss_pct: float = 1.0, cfg = None):
        self.config = cfg or DEFAULT_CONFIG
        self.initial_cash = float(initial_cash)
        self.cash = float(initial_cash)
        self.symbol = symbol
        self.stop_loss_pct = float(stop_loss_pct) / 100.0  # as decimal (e.g. 0.01)

        # Position tracking (at most 1 concurrent position)
        self.position: Optional[Dict[str, Any]] = None
        self.closed_trades: List[Dict[str, Any]] = []

        # Risk counters
        self.trade_count = 0
        self.buy_count = 0
        self.last_trade_exit_bar = -999
        self.last_stop_hit_index = -999
        self.is_halted_loss_limit = False
        self.is_killed = False
        self.stop_new_trades_only = False

        # Private security key
        self._private_key = uuid.uuid4().hex

    def get_private_key(self) -> str:
        return self._private_key

    def calculate_stop_distance(self, price: float, atr: float = 0.0) -> float:
        """
        Volatility-adaptive stop:
        max(1.5 x ATR(14), minStopPct x price), capped at 1% guardrail.
        Fallback fixed 0.7% if ATR unavailable.
        """
        if price <= 0:
            return 1.0

        if atr > 0:
            raw_dist = max(self.config.atr_stop_multiplier * atr, price * self.config.min_stop_pct)
        else:
            pct = self.stop_loss_pct if self.stop_loss_pct > 0 else self.config.fallback_stop_pct
            raw_dist = price * pct

        # Cap at 1% guardrail (or stop_loss_pct if higher)
        max_dist = price * max(self.config.max_stop_pct, self.stop_loss_pct)
        stop_dist = min(raw_dist, max_dist)
        return max(stop_dist, self.config.tick_size)

    def calculate_position_size(
        self,
        current_price: float,
        size_tier: str = "full",
        atr: float = 0.0
    ) -> Tuple[int, str]:
        """
        Risk 0.5% of current capital per trade:
        size = floor((capital x 0.005) / stopDistance),
        capped by available cash and max % of capital per position.
        """
        if current_price <= 0:
            return 0, "Invalid price"

        stop_dist = self.calculate_stop_distance(current_price, atr)
        current_capital = max(0.0, self.get_equity(current_price))

        risk_pct = self.config.risk_per_trade_pct if atr > 0 else 0.01
        risk_budget = current_capital * risk_pct
        qty_risk = risk_budget / (stop_dist + 1e-9)

        # Position capital cap (e.g. 50% capital)
        qty_cap = (current_capital * self.config.max_capital_per_position_pct) / current_price

        multiplier = 1.0 if size_tier == "full" else 0.5
        raw_qty = min(qty_risk, qty_cap) * multiplier
        qty = int(math.floor(raw_qty))

        # Check available cash
        est_cost = (qty * current_price) + calculate_fees(current_price, qty, "BUY")
        if est_cost > self.cash:
            qty = int(math.floor(self.cash / (current_price + 1e-9)))

        if qty < 1:
            return 0, f"Calculated position size is < 1 share (capital ₹{current_capital:,.2f}, risk budget ₹{risk_budget:,.2f})"

        return qty, "OK"

    def can_trade(self, current_index: int = 0, side: str = "LONG") -> Tuple[bool, str]:
        """Checks risk gates before allowing any trade execution."""
        if self.is_killed:
            return False, "Emergency kill switch active"
        if self.stop_new_trades_only:
            return False, "New entries paused by user kill switch (managing open position)"
        if self.is_halted_loss_limit:
            return False, "Daily loss limit (2%) reached: trading halted"
        if self.position is not None:
            return False, "Already holding an open position"
        if self.trade_count >= self.config.max_trades_per_day:
            return False, f"Maximum daily trade limit ({self.config.max_trades_per_day}) reached"

        # 3-bar cooldown after last trade exit or stop
        bars_since_exit = current_index - self.last_trade_exit_bar
        if bars_since_exit < self.config.cooldown_bars and self.last_trade_exit_bar >= 0:
            rem = self.config.cooldown_bars - bars_since_exit
            return False, f"Trade cooldown active ({rem} bar{'s' if rem > 1 else ''} remaining)"

        return True, "OK"

    def can_buy(self, current_index: int = 0) -> Tuple[bool, str]:
        """Backward compatibility alias for can_trade(current_index, 'LONG')."""
        return self.can_trade(current_index, "LONG")

    def execute_buy(
        self,
        fill_price: float,
        qty: int,
        time_str: str,
        entry_type: str,
        auth_key: str,
        atr: float = 0.0
    ) -> Dict[str, Any]:
        """Executes LONG entry order."""
        if auth_key != self._private_key:
            raise PermissionError("Unauthorized: Private broker authentication key mismatch")

        if qty < 1:
            raise ValueError(f"execute_buy called with qty={qty}. Must be >= 1.")

        fees = calculate_fees(fill_price, qty, "BUY")
        assert fees > 0, f"BUY fees must be > 0 when qty={qty}, got fees={fees}"

        stop_dist = self.calculate_stop_distance(fill_price, atr)
        stop_price = round_down_tick(fill_price - stop_dist)
        take_profit = round_tick(fill_price + self.config.take_profit_r_multiple * stop_dist)

        assert stop_price > 0, f"stop_price must be > 0, got {stop_price}"
        assert stop_price < fill_price, f"stop_price {stop_price} must be < fill_price {fill_price}"

        total_deduction = (fill_price * qty) + fees
        self.cash -= total_deduction
        self.trade_count += 1
        self.buy_count += 1

        self.position = {
            "symbol": self.symbol,
            "side": "LONG",
            "qty": qty,
            "buy_price": fill_price,
            "buy_time": time_str,
            "buy_fees": fees,
            "stop_loss": stop_price,
            "take_profit": take_profit,
            "stop_distance": stop_dist,
            "breakeven_activated": False,
            "entry_type": entry_type,
            "highest_price": fill_price,
            "lowest_price": fill_price,
        }
        return self.position

    def execute_short(
        self,
        fill_price: float,
        qty: int,
        time_str: str,
        entry_type: str,
        auth_key: str,
        atr: float = 0.0
    ) -> Dict[str, Any]:
        """Executes SHORT entry order."""
        if auth_key != self._private_key:
            raise PermissionError("Unauthorized: Private broker authentication key mismatch")

        if qty < 1:
            raise ValueError(f"execute_short called with qty={qty}. Must be >= 1.")

        fees = calculate_fees(fill_price, qty, "SELL")
        assert fees > 0, f"SHORT fees must be > 0 when qty={qty}, got fees={fees}"

        stop_dist = self.calculate_stop_distance(fill_price, atr)
        stop_price = round_tick(fill_price + stop_dist)
        take_profit = round_down_tick(fill_price - self.config.take_profit_r_multiple * stop_dist)

        assert stop_price > fill_price, f"stop_price {stop_price} must be > fill_price {fill_price} for SHORT"

        self.cash -= fees
        self.trade_count += 1

        self.position = {
            "symbol": self.symbol,
            "side": "SHORT",
            "qty": qty,
            "buy_price": fill_price,
            "buy_time": time_str,
            "buy_fees": fees,
            "stop_loss": stop_price,
            "take_profit": take_profit,
            "stop_distance": stop_dist,
            "breakeven_activated": False,
            "entry_type": entry_type,
            "highest_price": fill_price,
            "lowest_price": fill_price,
        }
        return self.position

    def execute_sell(
        self,
        fill_price: float,
        time_str: str,
        reason: str,
        auth_key: str,
        current_bar_index: int = -1
    ) -> Dict[str, Any]:
        """Closes open position (LONG via sell, or SHORT via buy to cover)."""
        if auth_key != self._private_key:
            raise PermissionError("Unauthorized: Private broker authentication key mismatch")
        if not self.position:
            return {}

        pos = self.position
        side = pos.get("side", "LONG")
        qty = pos["qty"]
        entry_price = pos["buy_price"]
        entry_fees = pos["buy_fees"]

        if side == "LONG":
            exit_fees = calculate_fees(fill_price, qty, "SELL")
            gross_pnl = (fill_price - entry_price) * qty
            net_proceeds = (fill_price * qty) - exit_fees
            self.cash += net_proceeds
        else:
            exit_fees = calculate_fees(fill_price, qty, "BUY")
            gross_pnl = (entry_price - fill_price) * qty
            self.cash += (gross_pnl - exit_fees)

        net_pnl = round(gross_pnl - entry_fees - exit_fees, 2)
        total_fees = round(entry_fees + exit_fees, 2)

        trade_record = {
            "symbol": self.symbol,
            "side": side,
            "qty": qty,
            "buy_price": entry_price,
            "sell_price": fill_price,
            "buy_time": pos["buy_time"],
            "sell_time": time_str,
            "buy_fees": entry_fees,
            "sell_fees": exit_fees,
            "total_fees": total_fees,
            "gross_pnl": round(gross_pnl, 2),
            "net_pnl": net_pnl,
            "reason": reason,
            "entry_type": pos["entry_type"]
        }

        self.closed_trades.append(trade_record)
        self.position = None
        if current_bar_index >= 0:
            self.last_trade_exit_bar = current_bar_index
            self.last_stop_hit_index = current_bar_index

        return trade_record

    def check_stop_and_target_on_candle(
        self,
        candle: Dict[str, Any],
        current_index: int
    ) -> Optional[Dict[str, Any]]:
        """
        Manages open position on every bar before new evaluations:
        - Check Stop-Loss
        - Check Take-Profit (1.5R)
        - Move Stop to Breakeven (+1R)
        """
        if not self.position:
            return None

        pos = self.position
        side = pos.get("side", "LONG")
        c_open = candle["open"]
        c_high = candle["high"]
        c_low = candle["low"]
        time_str = candle["time"]
        entry_p = pos["buy_price"]
        stop_dist = pos["stop_distance"]

        pos["highest_price"] = max(pos["highest_price"], c_high)
        pos["lowest_price"] = min(pos["lowest_price"], c_low)

        if side == "LONG":
            # 1. Stop-Loss
            if c_low <= pos["stop_loss"]:
                fill_price = min(c_open, pos["stop_loss"])
                fill_price = round_down_tick(fill_price)
                self.last_stop_hit_index = current_index
                reason = f"STOP LOSS HIT at ₹{fill_price:.2f} (guard ₹{pos['stop_loss']:.2f})"
                trade = self.execute_sell(fill_price, time_str, reason, self._private_key, current_index)
                trade["is_stop_loss"] = True
                trade["sell_price"] = fill_price
                return trade

            # 2. Take-Profit (1.5R)
            if c_high >= pos["take_profit"]:
                fill_price = max(c_open, pos["take_profit"])
                fill_price = round_tick(fill_price)
                reason = f"TAKE PROFIT (1.5R) HIT at ₹{fill_price:.2f}"
                trade = self.execute_sell(fill_price, time_str, reason, self._private_key, current_index)
                trade["is_take_profit"] = True
                trade["sell_price"] = fill_price
                return trade

            # 3. Breakeven Trailing (+1R)
            if not pos["breakeven_activated"]:
                breakeven_trigger = entry_p + self.config.breakeven_r_multiple * stop_dist
                if c_high >= breakeven_trigger:
                    pos["stop_loss"] = max(pos["stop_loss"], entry_p)
                    pos["breakeven_activated"] = True

        else:
            # SHORT
            # 1. Stop-Loss
            if c_high >= pos["stop_loss"]:
                fill_price = max(c_open, pos["stop_loss"])
                fill_price = round_tick(fill_price)
                self.last_stop_hit_index = current_index
                reason = f"SHORT STOP LOSS HIT at ₹{fill_price:.2f} (guard ₹{pos['stop_loss']:.2f})"
                trade = self.execute_sell(fill_price, time_str, reason, self._private_key, current_index)
                trade["is_stop_loss"] = True
                trade["sell_price"] = fill_price
                return trade

            # 2. Take-Profit (1.5R)
            if c_low <= pos["take_profit"]:
                fill_price = min(c_open, pos["take_profit"])
                fill_price = round_down_tick(fill_price)
                reason = f"SHORT TAKE PROFIT (1.5R) HIT at ₹{fill_price:.2f}"
                trade = self.execute_sell(fill_price, time_str, reason, self._private_key, current_index)
                trade["is_take_profit"] = True
                trade["sell_price"] = fill_price
                return trade

            # 3. Breakeven Trailing (+1R)
            if not pos["breakeven_activated"]:
                breakeven_trigger = entry_p - self.config.breakeven_r_multiple * stop_dist
                if c_low <= breakeven_trigger:
                    pos["stop_loss"] = min(pos["stop_loss"], entry_p)
                    pos["breakeven_activated"] = True

        return None

    def check_stop_loss_on_candle(self, candle: Dict[str, Any], current_index: int) -> Optional[Dict[str, Any]]:
        """Backward compatible wrapper for check_stop_and_target_on_candle."""
        return self.check_stop_and_target_on_candle(candle, current_index)

    def evaluate_daily_loss_limit(self, current_price: float) -> bool:
        """
        Hard safety circuit breaker:
        If total drawdown reaches 2% of initial capital, halt all trading.
        """
        equity = self.get_equity(current_price)
        loss = self.initial_cash - equity
        if loss >= (self.initial_cash * self.config.daily_loss_limit_pct):
            self.is_halted_loss_limit = True
            return True
        return False

    def get_equity(self, current_price: float) -> float:
        """Returns total portfolio equity (cash + mark-to-market position value)."""
        curr_p = float(current_price)
        if not self.position:
            return round(self.cash, 2)

        pos = self.position
        side = pos.get("side", "LONG")
        qty = pos["qty"]
        if side == "LONG":
            pos_val = qty * curr_p
            return round(self.cash + pos_val, 2)
        else:
            unrealized = (pos["buy_price"] - curr_p) * qty
            return round(self.cash + unrealized, 2)

    def get_day_pnl(self, current_price: float) -> float:
        return round(self.get_equity(current_price) - self.initial_cash, 2)

    def get_portfolio_state(self, current_price: float) -> Dict[str, Any]:
        """
        Returns full brokerage ledger state with the exact 10 fields consumed by UI:
        available_cash, invested_capital, open_positions, average_entry_price,
        current_market_price, unrealized_pnl, realized_pnl, total_fees,
        total_equity, daily_return_pct.
        """
        curr_p = float(current_price)
        pos = self.position
        side = pos.get("side", "LONG") if pos else "LONG"

        if pos:
            qty = pos["qty"]
            invested = qty * pos["buy_price"]
            if side == "LONG":
                unrealized = round((curr_p - pos["buy_price"]) * qty - pos["buy_fees"], 2)
            else:
                unrealized = round((pos["buy_price"] - curr_p) * qty - pos["buy_fees"], 2)
        else:
            invested = 0.0
            unrealized = 0.0

        realized = round(sum(t["net_pnl"] for t in self.closed_trades), 2)
        total_fees = round(
            sum(t["total_fees"] for t in self.closed_trades) + (pos["buy_fees"] if pos else 0.0), 2
        )
        total_equity = self.get_equity(curr_p)
        daily_return = round(((total_equity - self.initial_cash) / self.initial_cash) * 100.0, 2)

        return {
            "available_cash": round(self.cash, 2),
            "invested_capital": round(invested, 2),
            "open_positions": 1 if pos else 0,
            "average_entry_price": pos["buy_price"] if pos else 0.0,
            "current_market_price": curr_p,
            "unrealized_pnl": unrealized,
            "realized_pnl": realized,
            "total_fees": total_fees,
            "total_equity": total_equity,
            "daily_return_pct": daily_return,
            "position": pos
        }

    def reconcile_books(self, current_price: float) -> Tuple[bool, float, float]:
        """
        Reconciles portfolio books:
        final equity - starting amount == sum of closed trade net P&L + unrealized P&L.
        """
        eq = self.get_equity(current_price)
        diff = round(eq - self.initial_cash, 2)
        sum_closed = round(sum(t["net_pnl"] for t in self.closed_trades), 2)

        if self.position:
            pos = self.position
            side = pos.get("side", "LONG")
            if side == "LONG":
                unrealized = round((current_price - pos["buy_price"]) * pos["qty"] - pos["buy_fees"], 2)
            else:
                unrealized = round((pos["buy_price"] - current_price) * pos["qty"] - pos["buy_fees"], 2)
            expected = round(sum_closed + unrealized, 2)
        else:
            expected = sum_closed

        is_reconciled = abs(diff - expected) < 0.10
        return is_reconciled, diff, expected
