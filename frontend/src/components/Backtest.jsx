import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";
import { api, fmt } from "../api.js";

export default function Backtest() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      setData(await api.backtest());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const m = data?.metrics;
  return (
    <>
      <div className="panel-head">
        <h2>Honest backtest</h2>
        <button className="btn" onClick={load} disabled={loading}>
          {loading ? "Running backtest…" : data ? "Run backtest again" : "Run backtest"}
        </button>
      </div>
      {!data && !error && (
        <p className="empty">Runs the same bot over the full price history, fees and slippage included, and compares it with simply buying and holding.</p>
      )}
      {error && <p className="down">{error}</p>}
      {data && (
        <div className="backtest">
          <div className="chart-box chart-box-short">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.curve} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="var(--line)" strokeDasharray="2 4" vertical={false} />
                <XAxis dataKey="t" minTickGap={28} tick={{ fill: "var(--muted)", fontSize: 11 }} stroke="var(--line)" />
                <YAxis domain={["auto", "auto"]} tick={{ fill: "var(--muted)", fontSize: 11 }} stroke="var(--line)" width={64}
                  tickFormatter={(v) => fmt(v, 0)} />
                <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 6 }}
                  formatter={(v) => fmt(v, 0)} labelFormatter={(t) => `Tick ${t}`} />
                <Legend wrapperStyle={{ color: "var(--muted)", fontSize: 12 }} />
                <Line dataKey="bot" name="ProfitPilot" stroke="var(--glass)" strokeWidth={2} dot={false} isAnimationActive={false} />
                <Line dataKey="hold" name="Buy and hold" stroke="var(--amber)" strokeWidth={1.5} strokeDasharray="4 3" dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <table className="metrics">
            <thead>
              <tr><th></th><th>ProfitPilot</th><th>Buy and hold</th></tr>
            </thead>
            <tbody>
              <tr><th>Return</th><td>{m.bot_return_pct}%</td><td>{m.hold_return_pct}%</td></tr>
              <tr><th>Worst drawdown</th><td>{m.bot_max_drawdown_pct}%</td><td>{m.hold_max_drawdown_pct}%</td></tr>
              <tr><th>Closed trades</th><td>{m.trades}{m.win_rate !== null ? ` (${m.win_rate}% won)` : ""}</td><td>1</td></tr>
              <tr><th>Fees + slippage</th><td>{fmt(m.fees_paid)}</td><td>–</td></tr>
            </tbody>
          </table>
          <p className="muted">
            {m.bot_return_pct < m.hold_return_pct
              ? "The bot made less than buy-and-hold here, but with a far smaller worst drawdown. That trade-off is the point: it stays out of the market when the agents disagree."
              : "The bot beat buy-and-hold here. Check the drawdown row too: risk taken matters as much as return."}
          </p>
        </div>
      )}
    </>
  );
}
