import { ComposedChart, Line, XAxis, YAxis, Tooltip, ReferenceLine, ResponsiveContainer, CartesianGrid } from "recharts";
import { fmt } from "../api.js";

const Marker = (color, up) => (props) => {
  const { cx, cy, value, index } = props;
  if (value == null || cx == null || cy == null) return null;
  const d = up ? `M${cx},${cy - 9} L${cx + 7},${cy + 4} L${cx - 7},${cy + 4} Z` : `M${cx},${cy + 9} L${cx + 7},${cy - 4} L${cx - 7},${cy - 4} Z`;
  return <path key={`m-${index}`} d={d} fill={color} stroke="var(--panel)" strokeWidth={1.5} />;
};

export default function PriceChart({ state }) {
  const pos = state.portfolio.position;
  const first = state.prices[0]?.price ?? state.price;
  const change = ((state.price / first - 1) * 100).toFixed(2);

  return (
    <>
      <div className="panel-head">
        <h2>{state.symbol}</h2>
        <div className="price-readout">
          <span className="big-num">{fmt(state.price)}</span>
          <span className={change >= 0 ? "up" : "down"}>{change >= 0 ? "+" : ""}{change}% in view</span>
        </div>
      </div>
      <div className="chart-box">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={state.prices} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="var(--line)" strokeDasharray="2 4" vertical={false} />
            <XAxis dataKey="t" minTickGap={28} tick={{ fill: "var(--muted)", fontSize: 11 }} stroke="var(--line)" />
            <YAxis domain={["auto", "auto"]} tick={{ fill: "var(--muted)", fontSize: 11 }} stroke="var(--line)" width={52} />
            <Tooltip
              contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 6 }}
              labelStyle={{ color: "var(--muted)" }}
              labelFormatter={(t) => `Tick ${t}`}
            />
            {pos && (
              <ReferenceLine y={pos.stop} stroke="var(--stop)" strokeDasharray="5 4"
                label={{ value: `Stop ${pos.stop}`, fill: "var(--stop)", fontSize: 11, position: "insideBottomLeft" }} />
            )}
            {pos && (
              <ReferenceLine y={pos.entry} stroke="var(--go)" strokeDasharray="2 4"
                label={{ value: `Entry ${pos.entry}`, fill: "var(--go)", fontSize: 11, position: "insideTopLeft" }} />
            )}
            <Line type="monotone" dataKey="price" name="Price" stroke="var(--glass)" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line dataKey="buy" name="Buy" stroke="none" dot={Marker("var(--go)", true)} activeDot={false} isAnimationActive={false} legendType="none" />
            <Line dataKey="sell" name="Sell" stroke="none" dot={Marker("var(--stop)", false)} activeDot={false} isAnimationActive={false} legendType="none" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <p className="legend muted">
        <span className="leg leg-buy" /> Buy <span className="leg leg-sell" /> Sell
        <span className="leg-line" /> Stop-loss while holding
      </p>
    </>
  );
}
