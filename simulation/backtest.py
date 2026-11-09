"""
simulation/backtest.py — Backtesting Engine for Quantitative Strategies.

Enables out-of-sample and chronological multi-day backtesting for all 10 registered
technical trading strategies with exact transaction fee accounting, no look-ahead bias,
and institutional performance analytics.
"""

import math
import datetime
from typing import Dict, Any, List, Optional

from simulation.config import (
    DEFAULT_CONFIG, TICK_SIZE, SLIPPAGE_BPS,
    ENTRY_START_TIME, ENTRY_END_TIME, SQUARE_OFF_TIME
)
from simulation.strategies.registry import get_strategy
from simulation.indicators import compute_indicators
from simulation.broker import round_tick, calculate_fees, compute_round_trip_cost
from simulation.market_data import fetch_5min_candles


def run_strategy_backtest(
    symbol: str = "TCS",
    strategy_id: str = "strat_ema_rsi_vol",
    strategy_params: Optional[Dict[str, Any]] = None,
    days: int = 5,
    initial_capital: float = 100000.0,
    risk_per_trade_pct: float = 0.5,
    stop_loss_pct: float = 1.0,
    target_rr: float = 1.5
) -> Dict[str, Any]:
    """
    Executes a multi-day chronological intraday backtest for the specified strategy.
    
    Returns structured results:
      - metrics: net_profit, gross_profit, win_rate, profit_factor, max_drawdown, sharpe_ratio, total_trades
      - equity_curve: list of {time, timestamp, equity, cash, drawdown}
      - trades: list of executed and closed trades with entry, exit, fees, net_pnl, duration, exit_reason
    """
    strategy = get_strategy(strategy_id)
    if not strategy:
        raise ValueError(f"Unknown strategy ID: '{strategy_id}'")

    clean_sym = symbol.strip().upper()
    yf_symbol = clean_sym if "." in clean_sym else f"{clean_sym}.NS"

    # Step 1: Ingest 5-minute historical candles across multiple trading days
    all_day_candles: List[List[Dict[str, Any]]] = []
    overall_is_real = False
    today = datetime.date.today()

    # Collect past N weekdays
    target_dates: List[str] = []
    curr = today
    while len(target_dates) < days:
        if curr.weekday() < 5:  # Monday to Friday
            target_dates.append(curr.strftime("%Y-%m-%d"))
        curr -= datetime.timedelta(days=1)
    target_dates.reverse()

    for d_str in target_dates:
        try:
            day_candles, _, is_real, _, _ = fetch_5min_candles(yf_symbol, d_str)
            if day_candles and len(day_candles) >= 10:
                all_day_candles.append(day_candles)
                if is_real:
                    overall_is_real = True
        except Exception:
            continue

    if not all_day_candles:
        raise RuntimeError(f"Could not load historical candles for symbol {clean_sym}")

    # Step 2: Run chronological backtest loop
    capital = float(initial_capital)
    peak_capital = capital
    equity_curve: List[Dict[str, Any]] = []
    closed_trades: List[Dict[str, Any]] = []
    
    current_position: Optional[Dict[str, Any]] = None
    pending_entry: Optional[Dict[str, Any]] = None

    for day_candles in all_day_candles:
        closes_so_far: List[Dict[str, Any]] = []
        
        for bar_idx, candle in enumerate(day_candles):
            closes_so_far.append(candle)
            curr_time = candle.get("time_str") or (candle.get("time") if isinstance(candle.get("time"), str) else "09:15")
            curr_price = float(candle["close"])
            curr_ts = candle.get("timestamp") or int(datetime.datetime.now().timestamp())
            candle_date = candle.get("date") or target_dates[0]

            # Compute technical indicators at this bar
            indicators = compute_indicators([], closes_so_far)

            # Check pending fill from previous bar signal (no lookahead execution at open!)
            if pending_entry is not None:
                fill_price = float(candle["open"])
                side = pending_entry["side"]
                risk_dist = pending_entry["risk_dist"]
                
                # Position sizing based on capital and risk distance
                risk_amount = capital * (risk_per_trade_pct / 100.0)
                qty = max(1, int(risk_amount / max(0.5, risk_dist)))
                
                # Cap qty by cash
                max_afford = int((capital * 0.95) / fill_price)
                qty = min(qty, max(1, max_afford))

                entry_fees = calculate_fees(fill_price, qty, side)
                capital -= entry_fees

                if side == "BUY":
                    stop_price = round_tick(fill_price - risk_dist)
                    target_price = round_tick(fill_price + risk_dist * target_rr)
                else:
                    stop_price = round_tick(fill_price + risk_dist)
                    target_price = round_tick(fill_price - risk_dist * target_rr)

                current_position = {
                    "id": f"trade_{len(closed_trades) + 1}",
                    "side": side,
                    "symbol": clean_sym,
                    "strategy_name": strategy.name,
                    "qty": qty,
                    "entry_price": fill_price,
                    "entry_time": curr_time,
                    "entry_timestamp": curr_ts,
                    "date": candle_date,
                    "stop_loss": stop_price,
                    "target": target_price,
                    "risk_dist": risk_dist,
                    "entry_fees": entry_fees,
                    "reason": pending_entry["reason"]
                }
                pending_entry = None

            # Manage active position
            if current_position is not None:
                pos = current_position
                qty = pos["qty"]
                side = pos["side"]
                hit_exit = False
                exit_price = curr_price
                exit_reason = ""

                # 1. Stop loss hit on candle high/low
                if side == "BUY" and float(candle["low"]) <= pos["stop_loss"]:
                    hit_exit = True
                    exit_price = pos["stop_loss"]
                    exit_reason = "Stop-Loss Hit"
                elif side == "SELL" and float(candle["high"]) >= pos["stop_loss"]:
                    hit_exit = True
                    exit_price = pos["stop_loss"]
                    exit_reason = "Stop-Loss Hit"
                # 2. Target hit
                elif side == "BUY" and float(candle["high"]) >= pos["target"]:
                    hit_exit = True
                    exit_price = pos["target"]
                    exit_reason = f"Target Hit (+{target_rr}R)"
                elif side == "SELL" and float(candle["low"]) <= pos["target"]:
                    hit_exit = True
                    exit_price = pos["target"]
                    exit_reason = f"Target Hit (+{target_rr}R)"
                # 3. Square-off time check (15:15 IST)
                elif curr_time >= SQUARE_OFF_TIME:
                    hit_exit = True
                    exit_price = curr_price
                    exit_reason = "EOD Intraday Square-Off"

                if hit_exit:
                    exit_fees = calculate_fees(exit_price, qty, "SELL" if side == "BUY" else "BUY")
                    total_fees = pos["entry_fees"] + exit_fees
                    gross_pnl = (exit_price - pos["entry_price"]) * qty if side == "BUY" else (pos["entry_price"] - exit_price) * qty
                    net_pnl = gross_pnl - total_fees

                    capital += net_pnl
                    peak_capital = max(peak_capital, capital)

                    closed_trades.append({
                        "id": pos["id"],
                        "symbol": pos["symbol"],
                        "side": side,
                        "strategy": pos["strategy_name"],
                        "qty": qty,
                        "entry_price": pos["entry_price"],
                        "entry_time": f"{pos['date']} {pos['entry_time']}",
                        "exit_price": exit_price,
                        "exit_time": f"{candle_date} {curr_time}",
                        "gross_pnl": round(gross_pnl, 2),
                        "fees": round(total_fees, 2),
                        "net_pnl": round(net_pnl, 2),
                        "exit_reason": exit_reason
                    })
                    current_position = None

            # Evaluate strategy entry if no active position and within trading window (09:30 to 14:45)
            if current_position is None and pending_entry is None:
                if ENTRY_START_TIME <= curr_time <= ENTRY_END_TIME:
                    eval_res = strategy.evaluate(
                        candles_5m_today=closes_so_far,
                        indicators=indicators,
                        is_holding=False,
                        position_side="LONG",
                        entry_price=None
                    )
                    action = eval_res.get("signal", "HOLD")
                    if action in ("BUY", "SELL"):
                        stop_dist = round_tick(curr_price * (stop_loss_pct / 100.0))
                        pending_entry = {
                            "side": action,
                            "risk_dist": max(0.5, stop_dist),
                            "reason": eval_res.get("reason") or f"{strategy.name} entry signal"
                        }

            # Record periodic equity curve point (every bar)
            unrealized_pnl = 0.0
            if current_position is not None:
                p = current_position
                unrealized_pnl = (curr_price - p["entry_price"]) * p["qty"] if p["side"] == "BUY" else (p["entry_price"] - curr_price) * p["qty"]

            current_equity = round(capital + unrealized_pnl, 2)
            peak_capital = max(peak_capital, current_equity)
            drawdown_pct = round(((peak_capital - current_equity) / peak_capital) * 100.0, 2)

            equity_curve.append({
                "time": f"{candle_date} {curr_time}",
                "timestamp": curr_ts,
                "equity": current_equity,
                "drawdown": drawdown_pct
            })

    # Step 3: Compute aggregate performance statistics
    total_trades = len(closed_trades)
    winning_trades = [t for t in closed_trades if t["net_pnl"] > 0]
    losing_trades = [t for t in closed_trades if t["net_pnl"] < 0]
    
    win_rate = round((len(winning_trades) / total_trades) * 100.0, 1) if total_trades > 0 else 0.0
    gross_profits = sum(t["gross_pnl"] for t in winning_trades)
    gross_losses = abs(sum(t["gross_pnl"] for t in losing_trades))
    profit_factor = round(gross_profits / gross_losses, 2) if gross_losses > 0 else (99.0 if gross_profits > 0 else 0.0)

    total_fees = round(sum(t["fees"] for t in closed_trades), 2)
    net_profit = round(capital - initial_capital, 2)
    net_roi_pct = round((net_profit / initial_capital) * 100.0, 2)
    max_drawdown = max([pt["drawdown"] for pt in equity_curve]) if equity_curve else 0.0

    # Sharpe ratio approximation
    trade_pnls = [t["net_pnl"] for t in closed_trades]
    if len(trade_pnls) >= 2:
        mean_pnl = sum(trade_pnls) / len(trade_pnls)
        variance = sum((p - mean_pnl) ** 2 for p in trade_pnls) / (len(trade_pnls) - 1)
        stdev = math.sqrt(variance) if variance > 0 else 1.0
        sharpe_ratio = round((mean_pnl / stdev) * math.sqrt(len(trade_pnls)), 2)
    else:
        sharpe_ratio = 0.0

    return {
        "status": "success",
        "symbol": clean_sym,
        "strategy_id": strategy_id,
        "strategy_name": strategy.name,
        "days_tested": len(all_day_candles),
        "is_real_data": overall_is_real,
        "initial_capital": initial_capital,
        "final_capital": round(capital, 2),
        "metrics": {
            "net_profit": net_profit,
            "net_roi_pct": net_roi_pct,
            "total_trades": total_trades,
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "total_fees": total_fees
        },
        "equity_curve": equity_curve[::3] if len(equity_curve) > 150 else equity_curve,
        "trades": closed_trades
    }
