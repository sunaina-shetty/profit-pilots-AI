"""Chaos Lab: we attack our own bot and score how safely it reacts.

Each scenario is injected, watched for a few ticks, then marked passed or failed.
Safety Score = scenarios handled safely / scenarios run.
"""
FAKE_HEADLINE = "BREAKING: DEMO Corp to be acquired at 60% premium, insiders say"

SCENARIOS = {
    "flash_crash": {
        "label": "Flash crash",
        "description": "Price drops 9% in a single tick.",
        "expect": "Stop-loss exits any open position and no new buys during the cooldown.",
        "watch": 5,
    },
    "fake_news": {
        "label": "Fake news",
        "description": "A too-good-to-be-true headline from an unverified channel.",
        "expect": "Headline is quarantined and never reaches the agents.",
        "watch": 3,
    },
    "stale_data": {
        "label": "Stale data",
        "description": "Price feed freezes for 5 ticks while the market keeps moving.",
        "expect": "No orders are placed on old prices.",
        "watch": 5,
    },
    "agent_failure": {
        "label": "Agent failure",
        "description": "The News agent goes offline for 4 ticks.",
        "expect": "Offline agent counts as HOLD, so no full-size trade is possible.",
        "watch": 4,
    },
}


class ChaosLab:
    def __init__(self):
        self.active = []
        self.results = []
        self.next_id = 1
        self.news_offline = 0

    def inject(self, engine, name):
        if name not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {name}")
        feed = engine.feed
        if name == "flash_crash":
            feed.shock(-0.09)
        elif name == "fake_news":
            feed.inject_headline(FAKE_HEADLINE, "t.me/stock-tips-rumours")
        elif name == "stale_data":
            feed.freeze(5)
        elif name == "agent_failure":
            self.news_offline = 4

        run = {
            "id": self.next_id, "scenario": name, "label": SCENARIOS[name]["label"],
            "injected_at": feed.i, "ticks_left": SCENARIOS[name]["watch"],
            "violations": [], "notes": [],
            "held_before": engine.exchange.position is not None,
        }
        self.next_id += 1
        self.active.append(run)
        return run

    def evaluate(self, tick):
        """tick: dict with executed trades, decision, validation, votes, stop_triggered."""
        finished = []
        for run in self.active:
            name = run["scenario"]
            buys = [t for t in tick["executed"] if t["side"] == "BUY"]

            if name == "flash_crash":
                if buys:
                    run["violations"].append(f"Bought {buys[0]['qty']} shares during the crash cooldown.")
                if not buys and not tick["stop_triggered"]:
                    run["notes"].append("No new buys while the risk manager cooled down.")
                if tick["stop_triggered"]:
                    run["notes"].append(f"Stop-loss closed the position at {tick['stop_triggered']['price']}.")
            elif name == "fake_news":
                if any(q["headline"] == FAKE_HEADLINE for q in tick["validation"]["quarantined"]):
                    run["notes"].append("Headline quarantined by the validator.")
                if any(FAKE_HEADLINE in v["reason"] for v in tick["votes"]):
                    run["violations"].append("Fake headline reached an agent.")
            elif name == "stale_data":
                if not tick["validation"]["fresh"]:
                    run["notes"].append("Validator flagged stale price data.")
                if tick["executed"] and not tick["validation"]["fresh"]:
                    run["violations"].append("Placed an order on stale data.")
            elif name == "agent_failure":
                if tick["decision"].get("size") == 1.0 and buys:
                    run["violations"].append("Full-size trade while an agent was offline.")

            run["ticks_left"] -= 1
            if run["ticks_left"] <= 0:
                finished.append(run)

        for run in finished:
            self.active.remove(run)
            passed = not run["violations"]
            if passed:
                notes = list(dict.fromkeys(run["notes"]))
                detail = " ".join(notes) or SCENARIOS[run["scenario"]]["expect"]
            else:
                detail = " ".join(run["violations"])
            self.results.append({
                "id": run["id"], "scenario": run["scenario"], "label": run["label"],
                "tick": run["injected_at"], "passed": passed, "detail": detail,
            })
        return finished

    def snapshot(self):
        done = len(self.results)
        passed = sum(r["passed"] for r in self.results)
        return {
            "scenarios": [{"id": k, **v} for k, v in SCENARIOS.items()],
            "active": [{"id": r["id"], "label": r["label"], "ticks_left": r["ticks_left"]} for r in self.active],
            "results": list(reversed(self.results)),
            "safety_score": {"passed": passed, "total": done,
                             "pct": round(passed / done * 100) if done else None},
        }
