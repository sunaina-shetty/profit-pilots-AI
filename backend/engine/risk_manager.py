"""The independent risk manager. Rules only, no AI.

Every order passes through approve() before it reaches the mock exchange.
The AI agents can only *request* orders; they cannot change these limits or
bypass the kill switch.
"""
import math

from .config import (
    CIRCUIT_BREAKER_MOVE, COOLDOWN_TICKS, DAILY_LOSS_LIMIT_PCT,
    MAX_POSITION_PCT, RISK_PER_TRADE, STARTING_CASH, STOP_LOSS_PCT,
)


class RiskManager:
    def __init__(self):
        self.kill_switch = False
        self.session_start_equity = STARTING_CASH
        self.cooldown = 0
        self.halted = False

    def on_tick(self, price, prev_price, equity):
        """Update market-wide state before any order is considered."""
        move = abs(price / prev_price - 1)
        if move > CIRCUIT_BREAKER_MOVE:
            self.cooldown = COOLDOWN_TICKS
        elif self.cooldown > 0:
            self.cooldown -= 1
        if equity <= self.session_start_equity * (1 - DAILY_LOSS_LIMIT_PCT):
            self.halted = True
        return move

    def stop_hit(self, position, price):
        return position is not None and price <= position["stop"]

    def approve(self, action, size, ctx):
        """ctx: price, equity, cash, position, fresh. Returns a verdict with every check shown."""
        checks = []

        def check(name, ok, detail):
            checks.append({"name": name, "ok": ok, "detail": detail})
            return ok

        price, equity = ctx["price"], ctx["equity"]

        ok = check("Kill switch", not self.kill_switch,
                   "Engaged: all AI orders blocked" if self.kill_switch else "Off")
        ok &= check("Data freshness", ctx["fresh"],
                    "Fresh" if ctx["fresh"] else "Stale data: no trading on old prices")

        if action == "SELL":
            qty = ctx["position"]["qty"] if ctx["position"] else 0
            ok &= check("Position exists", qty > 0, f"Selling {qty} shares" if qty else "Nothing to sell")
            return {"approved": bool(ok), "qty": qty, "stop": None, "checks": checks}

        # BUY checks
        ok &= check("Session loss limit", not self.halted,
                    f"Halted: equity fell {DAILY_LOSS_LIMIT_PCT:.0%} from session start" if self.halted
                    else f"Within {DAILY_LOSS_LIMIT_PCT:.0%} limit")
        ok &= check("Abnormal market", self.cooldown == 0,
                    f"Cooling down for {self.cooldown} more ticks after a >{CIRCUIT_BREAKER_MOVE:.0%} move"
                    if self.cooldown else "Normal volatility")

        stop = round(price * (1 - STOP_LOSS_PCT), 2)
        risk_amount = equity * RISK_PER_TRADE * size
        qty_by_risk = math.floor(risk_amount / (price - stop))
        qty_by_cap = math.floor(equity * MAX_POSITION_PCT / price)
        qty_by_cash = math.floor(ctx["cash"] / (price * 1.002))
        qty = max(0, min(qty_by_risk, qty_by_cap, qty_by_cash))
        ok &= check("Position size", qty > 0,
                    f"{qty} shares: risks {RISK_PER_TRADE * size:.1%} of equity, stop at {stop}"
                    if qty else "Size rounds to zero")

        return {"approved": bool(ok), "qty": qty if ok else 0, "stop": stop, "checks": checks}

    def snapshot(self):
        return {"kill_switch": self.kill_switch, "cooldown": self.cooldown, "halted": self.halted}
