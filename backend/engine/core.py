"""The engine wires the pipeline from the deck together, one tick at a time:

1 data + news -> 2 validate -> 3 three agents -> 4 decision agent
-> 5 size + stop-loss -> 6 risk manager -> 7 mock exchange -> 8 journal
"""
from .agents import contrarian_agent, decide, news_agent, trend_agent, validate
from .chaos import ChaosLab
from .config import CIRCUIT_BREAKER_MOVE, STARTING_CASH, SYMBOL
from .data_feed import DataFeed
from .exchange import MockExchange
from .risk_manager import RiskManager


class Engine:
    def __init__(self, csv_path=None, record_journal=True):
        self.csv_path = csv_path
        self.feed = DataFeed(csv_path)
        self.exchange = MockExchange()
        self.risk = RiskManager()
        self.chaos = ChaosLab()
        self.record_journal = record_journal
        self.journal = []
        self.last = None
        self.hold_logged_at = {}
        self.seen_issues = set()
        self.equity_curve = []
        self._log("SYSTEM", f"Paper trading session started with {STARTING_CASH:,.0f} in virtual cash ({self.feed.source}).")

    # ------------------------------------------------------------ journal
    def _log(self, kind, text):
        if self.record_journal:
            self.journal.append({"id": len(self.journal) + 1, "tick": self.feed.i, "kind": kind, "text": text})

    # ------------------------------------------------------------ main loop
    def tick(self):
        if not self.feed.advance():
            return False

        snap = self.feed.snapshot()
        val = validate(snap)
        price, t = snap["price"], self.feed.i
        ex, risk = self.exchange, self.risk
        executed, stop_trade = [], None

        move = risk.on_tick(price, snap["prev_price"], ex.equity(price))
        if move > CIRCUIT_BREAKER_MOVE:
            self._log("ALERT", f"Abnormal market: price moved {move:.1%} in one tick. New entries paused while it settles.")
        for issue in val["issues"]:
            if issue not in self.seen_issues:
                self.seen_issues.add(issue)
                self._log("ALERT", issue + ".")
        if val["fresh"]:
            self.seen_issues = {i for i in self.seen_issues if not i.startswith("Price data")}

        # Step 6a: protective stop-loss. Rule-based, runs even if the AI is paused.
        if val["fresh"] and risk.stop_hit(ex.position, price):
            pos = ex.position
            stop_trade = ex.sell(price, t, "stop-loss")
            executed.append(stop_trade)
            self._log("RISK", f"Stop-loss hit: sold {pos['qty']} {SYMBOL} at {stop_trade['price']} "
                              f"(stop was {pos['stop']}). Realised {stop_trade['pnl']:,.2f}, "
                              f"{abs(stop_trade['pnl']) / STARTING_CASH:.1%} of starting capital. The AI was not consulted.")

        # Steps 3-4: agents vote, decision agent decides
        votes = []
        agent_offline = self.chaos.news_offline > 0
        if self.chaos.news_offline > 0:
            self.chaos.news_offline -= 1

        if risk.kill_switch:
            decision = {"action": "HOLD", "size": 0, "signal": None, "reason": "Kill switch engaged by a human. Agents are paused."}
        elif not val["fresh"]:
            decision = {"action": "HOLD", "size": 0, "signal": None, "reason": "Price data is stale, so the bot will not trade."}
        else:
            history = snap["history"]
            votes = [trend_agent(history), news_agent(val["headlines"]), contrarian_agent(history)]
            if agent_offline:
                votes[1] = {"agent": "News", "vote": "HOLD", "confidence": 0,
                            "reason": "Agent offline. Counted as HOLD so it can never push a trade.", "offline": True}
            decision = decide(votes, holding=ex.position is not None)

        # Steps 5-7: size, risk check, execute
        verdict = None
        if decision["action"] != "HOLD":
            verdict = risk.approve(decision["action"], decision["size"], {
                "price": price, "equity": ex.equity(price), "cash": ex.cash,
                "position": ex.position, "fresh": val["fresh"],
            })
            if verdict["approved"]:
                if decision["action"] == "BUY":
                    trade = ex.buy(verdict["qty"], price, verdict["stop"], t, decision["size"])
                    self._log("TRADE", self._buy_text(trade, verdict, decision, votes))
                else:
                    trade = ex.sell(price, t, "agents")
                    self._log("TRADE", self._sell_text(trade, decision, votes))
                executed.append(trade)
            else:
                failed = "; ".join(c["detail"] for c in verdict["checks"] if not c["ok"])
                self._log("BLOCKED", f"Agents wanted to {decision['action']} but the risk manager refused: {failed}.")
        elif t - self.hold_logged_at.get(decision["reason"], -99) > 15:
            # log each kind of HOLD at most once every 15 ticks to keep the journal readable
            self.hold_logged_at[decision["reason"]] = t
            self._log("HOLD", decision["reason"])

        # Chaos Lab scoring
        tick_info = {"executed": executed, "decision": decision, "validation": val,
                     "votes": votes, "stop_triggered": stop_trade}
        for run in self.chaos.evaluate(tick_info):
            result = self.chaos.results[-1]
            verdict_word = "handled safely" if result["passed"] else "FAILED"
            self._log("CHAOS", f"Chaos test '{run['label']}' {verdict_word}. {result['detail']}")

        true_price = self.feed.true_price()
        self.equity_curve.append({"t": t, "equity": ex.equity(true_price)})
        self.last = {"tick": t, "votes": votes, "decision": decision, "verdict": verdict,
                     "validation": val, "executed": executed, "agent_offline": agent_offline}
        return True

    # ------------------------------------------------------------ journal text
    @staticmethod
    def _votes_text(votes):
        return " ".join(f"{v['agent']}: {v['vote']} ({v['reason']})" for v in votes)

    def _buy_text(self, trade, verdict, decision, votes):
        return (f"Bought {trade['qty']} {SYMBOL} at {trade['price']}. {decision['reason']} "
                f"{self._votes_text(votes)} Stop-loss set at {verdict['stop']}; fee {trade['fee']}.")

    def _sell_text(self, trade, decision, votes):
        outcome = "profit" if trade["pnl"] >= 0 else "loss"
        return (f"Sold {trade['qty']} {SYMBOL} at {trade['price']} for a {outcome} of {abs(trade['pnl']):,.2f} after fees. "
                f"{decision['reason']} {self._votes_text(votes)}")

    # ------------------------------------------------------------ actions
    def set_kill_switch(self, engaged):
        if engaged != self.risk.kill_switch:
            self.risk.kill_switch = engaged
            self._log("SYSTEM", "Kill switch ENGAGED by a human. All AI orders are blocked; stop-losses stay active."
                      if engaged else "Kill switch released. Agents resume on the next tick.")

    def inject_chaos(self, name):
        run = self.chaos.inject(self, name)
        self._log("CHAOS", f"Chaos test started: {run['label']}. Watching the next {run['ticks_left']} ticks.")
        return run

    # ------------------------------------------------------------ API view
    def state(self, window=150):
        f = self.feed
        price = f.true_price()
        start = max(0, f.i - window + 1)
        trades_by_tick = {}
        for tr in self.exchange.trades:
            trades_by_tick.setdefault(tr["tick"], []).append(tr)
        prices = []
        for k in range(start, f.i + 1):
            p = {"t": k, "price": f.closes[k]}
            for tr in trades_by_tick.get(k, []):
                p["buy" if tr["side"] == "BUY" else "sell"] = tr["price"]
            prices.append(p)

        return {
            "symbol": SYMBOL,
            "data_source": f.source,
            "tick": f.i,
            "total_ticks": len(f.closes) - 1,
            "done": f.done(),
            "price": price,
            "prices": prices,
            "last": self.last,
            "portfolio": self.exchange.snapshot(price),
            "risk": self.risk.snapshot(),
            "chaos": self.chaos.snapshot(),
            "journal": list(reversed(self.journal[-60:])),
        }


# ---------------------------------------------------------------- backtest
def run_backtest(csv_path=None):
    """Run the same engine over the whole dataset with no chaos and compare to buy-and-hold."""
    eng = Engine(csv_path, record_journal=False)
    first_price = eng.feed.true_price()
    curve = []
    while eng.tick():
        p = eng.feed.true_price()
        curve.append({"t": eng.feed.i, "bot": eng.exchange.equity(p),
                      "hold": round(STARTING_CASH * p / first_price, 2)})

    def max_drawdown(series):
        peak, worst = series[0], 0.0
        for v in series:
            peak = max(peak, v)
            worst = min(worst, v / peak - 1)
        return round(worst * 100, 2)

    bot = [c["bot"] for c in curve]
    hold = [c["hold"] for c in curve]
    snap = eng.exchange.snapshot(eng.feed.true_price())
    step = max(1, len(curve) // 200)
    return {
        "curve": curve[::step],
        "metrics": {
            "bot_return_pct": round((bot[-1] / STARTING_CASH - 1) * 100, 2),
            "hold_return_pct": round((hold[-1] / STARTING_CASH - 1) * 100, 2),
            "bot_max_drawdown_pct": max_drawdown(bot),
            "hold_max_drawdown_pct": max_drawdown(hold),
            "trades": snap["closed_trades"],
            "win_rate": snap["win_rate"],
            "fees_paid": snap["fees_paid"],
            "ticks": len(curve),
        },
    }
