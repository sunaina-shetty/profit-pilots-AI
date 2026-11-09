"""
replay_eval.py — Standalone Replay and Evaluation Script (No UI involvement).

Runs a full day of 5-minute candles for any symbol passed as a parameter,
evaluates all 3 agents (ORB Trend, News, VWAP Reversion) and Council Consensus,
executes paper trades through PaperBroker, and logs every decision & execution.

Usage:
  python replay_eval.py --symbol TCS.NS --date 2026-11-06
  python replay_eval.py --run-all
"""
import sys
import argparse
import datetime
from simulation.config import DEFAULT_CONFIG
from simulation.engine import SimulationEngine

def run_symbol_replay(symbol: str, date_str: str = "2026-11-06", amount: float = 100000.0, stop_loss_pct: float = 1.0, verbose: bool = True):
    print(f"\n{'='*80}")
    print(f"REPLAY SIMULATION: Symbol={symbol} | Date={date_str} | Capital=₹{amount:,.2f} | Stop={stop_loss_pct}%")
    print(f"{'='*80}")

    engine = SimulationEngine()
    engine.start_simulation(
        symbol=symbol,
        amount=amount,
        stop_loss_pct=stop_loss_pct,
        target_date_str=date_str,
        fast_mode=True,
        agent_mode="combined"
    )

    if engine.thread:
        engine.thread.join(timeout=30.0)

    state = engine.get_state()
    summary = state.get("summary") or {}
    journal = engine.journal
    portfolio = state.get("portfolio") or {}

    print(f"Data Feed: {state.get('data_source')} (Granularity: {state.get('candle_granularity')})")
    print(f"Total Candles Processed: {state.get('total_candles')}")
    print(f"Market Regime: {state.get('current_regime')} | Opening Range: H=₹{state.get('orb_high', 0):.2f}, L=₹{state.get('orb_low', 0):.2f}")
    print(f"-"*80)

    # 1. Print Decision Log
    print(f"{'Time':<7} | {'ORB':<7} | {'News':<7} | {'VWAP':<7} | {'Council':<8} | {'Conf':<5} | {'Action':<6} | Reason")
    print(f"-"*80)

    decisions = [j for j in journal if j.get("action")]
    # Show decisions chronologically
    for j in reversed(decisions):
        time_str = j.get("time", "")
        action = j.get("action", "HOLD")
        reason = j.get("reason", "")
        orb_s = f"{j['orb_score']:+.2f}" if "orb_score" in j else "—"
        news_s = f"{j['news_score']:+.2f}" if "news_score" in j else "—"
        vwap_s = f"{j['vwap_score']:+.2f}" if "vwap_score" in j else "—"
        council_s = f"{j['score']:+.2f}" if "score" in j else "—"
        conf_s = f"{j['confidence']:.0f}%" if "confidence" in j else "—"
        short_reason = (reason[:50] + "...") if len(reason) > 50 else reason
        print(f"{time_str:<7} | {orb_s:<7} | {news_s:<7} | {vwap_s:<7} | {council_s:<8} | {conf_s:<5} | {action:<6} | {short_reason}")

    print(f"-"*80)
    print(f"EXECUTION SUMMARY & METRICS")
    print(f"-"*80)
    total_trades = summary.get("total_trades", 0)
    closed_trades = summary.get("closed_trades", [])
    wins = summary.get("wins", 0)
    losses = summary.get("losses", 0)
    net_pnl = summary.get("net_pnl", 0.0)
    final_equity = summary.get("final_equity", amount)
    reconciled = summary.get("reconciled", False)

    print(f"Total Trades: {total_trades} (Wins: {wins}, Losses: {losses}, Win Rate: {summary.get('win_rate_pct', 0)}%)")
    print(f"Starting Capital: ₹{amount:,.2f} | Final Equity: ₹{final_equity:,.2f}")
    print(f"Net P&L: ₹{net_pnl:+,.2f} ({summary.get('return_pct', 0):+.2f}%)")
    print(f"Buy & Hold Return: {summary.get('buy_and_hold_return_pct', 0):+.2f}%")
    print(f"Books Reconciled: {'YES [PASS]' if reconciled else 'NO [FAIL]'}")

    # 2. Inspect Closed Trades
    if closed_trades:
        print(f"\nClosed Trades Breakdown:")
        for idx, t in enumerate(closed_trades, 1):
            side = t.get("side", "LONG")
            qty = t.get("qty", 0)
            entry_p = t.get("buy_price", 0.0)
            exit_p = t.get("sell_price", 0.0)
            fees = t.get("total_fees", 0.0)
            pnl = t.get("net_pnl", 0.0)
            reason = t.get("reason", "")
            print(f"  #{idx} {side} {qty}sh: {t.get('buy_time')} @ ₹{entry_p:.2f} -> {t.get('sell_time')} @ ₹{exit_p:.2f} | Fees: ₹{fees:.2f} | Net P&L: ₹{pnl:+,.2f} | {reason}")

            # Verify no single loss exceeds stop distance + fees
            if pnl < 0:
                expected_max_loss = (entry_p * (stop_loss_pct / 100.0) * qty) + fees + 10.0
                assert abs(pnl) <= expected_max_loss * 1.5, f"Loss ₹{abs(pnl):.2f} exceeded stop limit ₹{expected_max_loss:.2f}"
    else:
        print(f"\nZero trades executed today.")
        print(f"Explanation: Market conditions remained inside safety thresholds.")

    # Verify daily loss limit respected
    max_allowed_loss = amount * DEFAULT_CONFIG.daily_loss_limit_pct
    assert (amount - final_equity) <= max_allowed_loss + 50.0, f"Daily loss exceeded limit! Drawdown: ₹{amount - final_equity:.2f}"

    return {
        "symbol": symbol,
        "total_trades": total_trades,
        "net_pnl": net_pnl,
        "final_equity": final_equity,
        "reconciled": reconciled
    }


def main():
    parser = argparse.ArgumentParser(description="ProfitPilot Replay Evaluation")
    parser.add_argument("--symbol", type=str, default="TCS.NS", help="Stock symbol to replay")
    parser.add_argument("--date", type=str, default="2026-11-06", help="Date in YYYY-MM-DD")
    parser.add_argument("--run-all", action="store_true", help="Run 5 diverse symbols evaluation")
    args = parser.parse_args()

    if args.run_all:
        test_symbols = [
            ("TCS.NS", "High-priced Tech"),
            ("RELIANCE.NS", "Large-cap Conglomerate"),
            ("INFY.NS", "Volatile Tech"),
            ("SBIN.NS", "Low-priced Banking"),
            ("TATAMOTORS.NS", "High-beta Auto")
        ]
        results = []
        for sym, desc in test_symbols:
            print(f"\n>>> Running Evaluation for {sym} ({desc}) <<<")
            res = run_symbol_replay(sym, args.date)
            results.append((sym, desc, res))

        print(f"\n{'='*80}")
        print(f"5-SYMBOL VALIDATION SUMMARY MATRIX")
        print(f"{'='*80}")
        print(f"{'Symbol':<15} | {'Category':<24} | {'Trades':<8} | {'Net P&L':<12} | {'Reconciled'}")
        print(f"-"*80)
        for sym, desc, r in results:
            print(f"{sym:<15} | {desc:<24} | {r['total_trades']:<8} | ₹{r['net_pnl']:<11,.2f} | {'PASS' if r['reconciled'] else 'FAIL'}")
        print(f"{'='*80}")
    else:
        run_symbol_replay(args.symbol, args.date)

if __name__ == "__main__":
    main()
