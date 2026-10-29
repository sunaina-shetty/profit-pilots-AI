"""Paper-trading exchange: virtual cash, virtual fills, real-looking costs."""
from .config import FEE_PCT, SLIPPAGE_PCT, STARTING_CASH


class MockExchange:
    def __init__(self):
        self.cash = STARTING_CASH
        self.position = None          # {"qty", "entry", "stop", "cost"}
        self.realized_pnl = 0.0
        self.fees_paid = 0.0
        self.trades = []              # every fill, for chart markers and stats

    def buy(self, qty, price, stop, tick, size):
        fill = round(price * (1 + SLIPPAGE_PCT), 2)
        notional = fill * qty
        fee = round(notional * FEE_PCT, 2)
        self.cash -= notional + fee
        self.fees_paid += fee
        self.position = {"qty": qty, "entry": fill, "stop": stop, "cost": notional + fee, "size": size}
        trade = {"tick": tick, "side": "BUY", "qty": qty, "price": fill, "fee": fee}
        self.trades.append(trade)
        return trade

    def sell(self, price, tick, reason):
        pos = self.position
        fill = round(price * (1 - SLIPPAGE_PCT), 2)
        notional = fill * pos["qty"]
        fee = round(notional * FEE_PCT, 2)
        pnl = round(notional - fee - pos["cost"], 2)
        self.cash += notional - fee
        self.fees_paid += fee
        self.realized_pnl += pnl
        self.position = None
        trade = {"tick": tick, "side": "SELL", "qty": pos["qty"], "price": fill, "fee": fee, "pnl": pnl, "reason": reason}
        self.trades.append(trade)
        return trade

    def equity(self, price):
        held = self.position["qty"] * price if self.position else 0
        return round(self.cash + held, 2)

    def snapshot(self, price):
        pos = self.position
        unrealized = round(pos["qty"] * price - pos["cost"], 2) if pos else 0.0
        eq = self.equity(price)
        closed = [t for t in self.trades if t["side"] == "SELL"]
        wins = sum(1 for t in closed if t["pnl"] > 0)
        return {
            "cash": round(self.cash, 2),
            "equity": eq,
            "return_pct": round((eq / STARTING_CASH - 1) * 100, 2),
            "position": pos,
            "unrealized_pnl": unrealized,
            "realized_pnl": round(self.realized_pnl, 2),
            "fees_paid": round(self.fees_paid, 2),
            "closed_trades": len(closed),
            "win_rate": round(wins / len(closed) * 100) if closed else None,
        }
