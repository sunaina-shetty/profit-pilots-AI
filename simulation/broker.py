import math
import uuid
from typing import Dict, Any, Optional, List, Tuple
from simulation.config import (
    BROKERAGE_PCT, BROKERAGE_MAX, STT_SELL_PCT, EXCHANGE_TXN_PCT,
    GST_PCT, STAMP_DUTY_BUY_PCT, TICK_SIZE, SLIPPAGE_BPS,
    DAILY_LOSS_LIMIT_PCT, MAX_BUYS_PER_DAY, STOP_LOSS_COOLDOWN_MINUTES
)

def round_down_tick(price: float, tick: float = TICK_SIZE) -> float:
    return round(math.floor(price / tick + 1e-9) * tick, 2)

def round_tick(price: float, tick: float = TICK_SIZE) -> float:
    return round(round(price / tick) * tick, 2)

def calculate_fees(price: float, qty: int, side: str) -> float:
    # A: Return 0 when qty == 0 (no fees on zero-qty orders)
    if qty <= 0:
        return 0.0
    val = price * qty
    brokerage = min(BROKERAGE_MAX, val * BROKERAGE_PCT)
    exchange = val * EXCHANGE_TXN_PCT
    gst = (brokerage + exchange) * GST_PCT

    if side == "BUY":
        stamp = val * STAMP_DUTY_BUY_PCT
        stt = 0.0
    else:
        stamp = 0.0
        stt = val * STT_SELL_PCT

    return round(brokerage + exchange + gst + stamp + stt, 2)

def compute_round_trip_cost(price: float, qty: int) -> float:
    """F: Compute total round-trip brokerage & regulatory fees for a buy and sell."""
    if qty <= 0:
        return 0.0
    return round(calculate_fees(price, qty, "BUY") + calculate_fees(price, qty, "SELL"), 2)

class PaperBroker:
    """
    Paper Broker & Risk Manager (No AI inside).
    Enforces strict risk sizing, stops, slippage, fees, reconciliation,
    and requires an internal private authorization key.
    """
    def __init__(self, initial_cash: float, symbol: str, stop_loss_pct: float):
        self.initial_cash = float(initial_cash)
        self.cash = float(initial_cash)
        self.symbol = symbol
        self.stop_loss_pct = float(stop_loss_pct) / 100.0  # as decimal (e.g. 0.01)

        # Position tracking (at most 1 position)
        self.position: Optional[Dict[str, Any]] = None
        self.closed_trades: List[Dict[str, Any]] = []

        # Risk counters
        self.buy_count = 0
        self.last_stop_hit_index = -999
        self.is_halted_loss_limit = False
        self.is_killed = False

        # Private security key
        self._private_key = uuid.uuid4().hex

    def get_private_key(self) -> str:
        return self._private_key

    def calculate_position_size(self, current_price: float, size_tier: str) -> Tuple[int, str]:
        """
        Position size formula:
        qty = min( 1% of amount / (price x stop-loss%), 50% of amount / price ) * (1.0 or 0.5)
        rounded down.
        """
        if current_price <= 0:
            return 0, "Invalid price"

        risk_budget = self.initial_cash * 0.01 # 1% of capital
        risk_per_share = current_price * self.stop_loss_pct

        qty_risk = risk_budget / (risk_per_share + 1e-9)
        qty_cap = (self.initial_cash * 0.50) / current_price

        multiplier = 1.0 if size_tier == "full" else 0.5
        raw_qty = min(qty_risk, qty_cap) * multiplier
        qty = int(math.floor(raw_qty))

        # Check available cash
        est_cost = (qty * current_price) + calculate_fees(current_price, qty, "BUY")
        if est_cost > self.cash:
            qty = int(math.floor(self.cash / current_price))

        if qty < 1:
            return 0, f"Calculated position size is < 1 share (amount ₹{self.initial_cash:,.2f}, risk budget ₹{risk_budget:,.2f})"

        return qty, "OK"

    def can_buy(self, current_index: int) -> Tuple[bool, str]:
        """Checks risk gates before allowing an order."""
        if self.is_killed:
            return False, "Emergency kill switch active"
        if self.is_halted_loss_limit:
            return False, "Daily loss limit (2%) reached: trading halted"
        if self.position is not None:
            return False, "Already holding an open position"
        if self.buy_count >= MAX_BUYS_PER_DAY:
            return False, f"Maximum daily buy limit ({MAX_BUYS_PER_DAY}) reached"
        if (current_index - self.last_stop_hit_index) < STOP_LOSS_COOLDOWN_MINUTES:
            rem = STOP_LOSS_COOLDOWN_MINUTES - (current_index - self.last_stop_hit_index)
            return False, f"Stop-loss cooldown active ({rem} mins remaining)"
        return True, "OK"

    def execute_buy(self, fill_price: float, qty: int, time_str: str, entry_type: str, auth_key: str) -> Dict[str, Any]:
        if auth_key != self._private_key:
            raise PermissionError("Unauthorized: Private broker authentication key mismatch")

        # A: Runtime asserts — qty >= 1, stop < entry, fees > 0 only if qty > 0
        if qty < 1:
            raise ValueError(f"execute_buy called with qty={qty}. Must be >= 1.")

        fees = calculate_fees(fill_price, qty, "BUY")
        assert fees > 0, f"BUY fees must be > 0 when qty={qty}, got fees={fees}"

        total_deduction = (fill_price * qty) + fees
        self.cash -= total_deduction
        self.buy_count += 1

        stop_price = round_down_tick(fill_price * (1.0 - self.stop_loss_pct))
        assert stop_price > 0, f"stop_price must be > 0, got {stop_price}"
        assert stop_price < fill_price, f"stop_price {stop_price} must be < fill_price {fill_price}"

        self.position = {
            "symbol": self.symbol,
            "qty": qty,
            "buy_price": fill_price,
            "buy_time": time_str,
            "buy_fees": fees,
            "stop_loss": stop_price,
            "entry_type": entry_type
        }
        return self.position

    def execute_sell(self, fill_price: float, time_str: str, reason: str, auth_key: str) -> Dict[str, Any]:
        if auth_key != self._private_key:
            raise PermissionError("Unauthorized: Private broker authentication key mismatch")
        if not self.position:
            return {}

        qty = self.position["qty"]
        buy_price = self.position["buy_price"]
        buy_fees = self.position["buy_fees"]

        sell_fees = calculate_fees(fill_price, qty, "SELL")
        net_proceeds = (fill_price * qty) - sell_fees
        self.cash += net_proceeds

        # A: P&L computed from real entry, exit, qty and fees
        gross_pnl = (fill_price - buy_price) * qty
        net_pnl = round(gross_pnl - buy_fees - sell_fees, 2)

        trade_record = {
            "symbol": self.symbol,
            "qty": qty,
            "buy_price": buy_price,
            "sell_price": fill_price,
            "buy_time": self.position["buy_time"],
            "sell_time": time_str,
            "buy_fees": buy_fees,
            "sell_fees": sell_fees,
            "total_fees": round(buy_fees + sell_fees, 2),
            "gross_pnl": round(gross_pnl, 2),
            "net_pnl": net_pnl,
            "reason": reason,
            "entry_type": self.position["entry_type"]
        }
        self.closed_trades.append(trade_record)
        self.position = None
        return trade_record

    def check_stop_loss_on_candle(self, candle: Dict[str, Any], current_index: int) -> Optional[Dict[str, Any]]:
        """
        Stop-loss checked on EVERY candle:
        if candle low <= stop, sell at min(candle open, stop).
        """
        if not self.position:
            return None

        stop = self.position["stop_loss"]
        if candle["low"] <= stop:
            fill_price = min(candle["open"], stop)
            fill_price = round_tick(fill_price)
            self.last_stop_hit_index = current_index
            trade = self.execute_sell(fill_price, candle["time"], f"Stop-Loss hit at ₹{stop:.2f}", self._private_key)
            trade["is_stop_loss"] = True
            return trade
        return None

    def evaluate_daily_loss_limit(self, current_price: float) -> bool:
        """
        Hard safety rule:
        if day's loss reaches 2% of starting amount, sell everything and stop trading.
        """
        equity = self.get_equity(current_price)
        loss = self.initial_cash - equity
        if loss >= (self.initial_cash * DAILY_LOSS_LIMIT_PCT):
            self.is_halted_loss_limit = True
            return True
        return False

    def get_equity(self, current_price: float) -> float:
        pos_val = (self.position["qty"] * current_price) if self.position else 0.0
        return round(self.cash + pos_val, 2)

    def get_day_pnl(self, current_price: float) -> float:
        return round(self.get_equity(current_price) - self.initial_cash, 2)

    def get_portfolio_state(self, current_price: float) -> Dict[str, Any]:
        """
        Returns full brokerage ledger state:
        - available_cash
        - invested_capital
        - open_positions (count)
        - average_entry_price
        - current_market_price
        - unrealized_pnl
        - realized_pnl
        - total_fees
        - total_equity
        - daily_return_pct
        - position (details)
        """
        curr_p = float(current_price)
        pos = self.position
        pos_val = (pos["qty"] * curr_p) if pos else 0.0
        invested = (pos["qty"] * pos["buy_price"]) if pos else 0.0
        unrealized = round((curr_p - pos["buy_price"]) * pos["qty"] - pos["buy_fees"], 2) if pos else 0.0
        realized = round(sum(t["net_pnl"] for t in self.closed_trades), 2)
        total_fees = round(
            sum(t["total_fees"] for t in self.closed_trades) + (pos["buy_fees"] if pos else 0.0), 2
        )
        total_equity = round(self.cash + pos_val, 2)
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
        Money must reconcile:
        final equity - starting amount == sum of closed trade profits (after fees).
        """
        eq = self.get_equity(current_price)
        diff = round(eq - self.initial_cash, 2)
        sum_closed = round(sum(t["net_pnl"] for t in self.closed_trades), 2)
        if self.position:
            unrealized = round((current_price - self.position["buy_price"]) * self.position["qty"] - self.position["buy_fees"], 2)
            expected = round(sum_closed + unrealized, 2)
        else:
            expected = sum_closed
        is_reconciled = abs(diff - expected) < 0.10
        return is_reconciled, diff, expected
