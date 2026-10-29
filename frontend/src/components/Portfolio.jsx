import { fmt } from "../api.js";

export default function Portfolio({ state }) {
  const p = state.portfolio;
  const r = state.risk;
  const pos = p.position;

  return (
    <>
      <div className="panel-head"><h2>Account</h2></div>
      <div className="equity">
        <span className="big-num">{fmt(p.equity, 0)}</span>
        <span className={p.return_pct >= 0 ? "up" : "down"}>
          {p.return_pct >= 0 ? "+" : ""}{p.return_pct}% since start
        </span>
      </div>

      <dl className="stats">
        <dt>Cash</dt><dd>{fmt(p.cash, 0)}</dd>
        <dt>Position</dt>
        <dd>{pos ? `${pos.qty} @ ${pos.entry} (${pos.size === 1 ? "full" : "half"} size)` : "Flat"}</dd>
        <dt>Stop-loss</dt><dd>{pos ? pos.stop : "–"}</dd>
        <dt>Open P&amp;L</dt><dd className={p.unrealized_pnl >= 0 ? "up" : "down"}>{fmt(p.unrealized_pnl)}</dd>
        <dt>Realised P&amp;L</dt><dd className={p.realized_pnl >= 0 ? "up" : "down"}>{fmt(p.realized_pnl)}</dd>
        <dt>Fees + slippage paid</dt><dd>{fmt(p.fees_paid)}</dd>
        <dt>Closed trades</dt><dd>{p.closed_trades}{p.win_rate !== null ? `, ${p.win_rate}% won` : ""}</dd>
      </dl>

      <ul className="flags">
        <li className={r.kill_switch ? "flag-bad" : "flag-ok"}>Kill switch {r.kill_switch ? "engaged" : "off"}</li>
        <li className={r.halted ? "flag-bad" : "flag-ok"}>{r.halted ? "Session loss limit hit" : "Within loss limit"}</li>
        <li className={r.cooldown ? "flag-warn" : "flag-ok"}>{r.cooldown ? `Cooldown: ${r.cooldown} ticks` : "Normal volatility"}</li>
      </ul>
    </>
  );
}
