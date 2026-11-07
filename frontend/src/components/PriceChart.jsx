import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Dot
} from 'recharts';

export default function PriceChart({ ticks = [], symbol = 'RELIANCE.NS', lastStopLoss = null }) {
  // Custom Dot renderer for BUY/SELL/HOLD markers
  const CustomizedDot = (props) => {
    const { cx, cy, payload } = props;
    if (!payload || !payload.action) {
      return null;
    }

    if (payload.action === 'BUY') {
      return (
        <svg x={cx - 10} y={cy - 10} width={20} height={20} viewBox="0 0 20 20">
          <circle cx="10" cy="10" r="8" fill="#10b981" stroke="#047857" strokeWidth="2" />
          <polygon points="10,5 6,12 14,12" fill="#ffffff" />
        </svg>
      );
    }

    if (payload.action === 'SELL') {
      return (
        <svg x={cx - 10} y={cy - 10} width={20} height={20} viewBox="0 0 20 20">
          <circle cx="10" cy="10" r="8" fill="#ef4444" stroke="#b91c1c" strokeWidth="2" />
          <polygon points="10,14 6,7 14,7" fill="#ffffff" />
        </svg>
      );
    }

    if (payload.action === 'HOLD') {
      return (
        <circle cx={cx} cy={cy} r="3" fill="#64748b" opacity="0.6" />
      );
    }

    return null;
  };

  // Custom Tooltip showing price, decision, and agents
  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-[#0f172a] border border-[#334155] p-3 rounded-lg shadow-xl text-xs max-w-xs z-50">
          <div className="flex items-center justify-between border-b border-slate-700 pb-1.5 mb-2">
            <span className="font-mono text-cyan-400 font-bold">{data.timeStr}</span>
            <span className="font-mono text-white font-bold text-sm">₹{data.price?.toFixed(2)}</span>
          </div>

          {data.action && (
            <div className="mb-2">
              <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                data.action === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-600' :
                data.action === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-600' :
                'bg-slate-800 text-slate-300'
              }`}>
                {data.action} ({data.sizeTier || 'ZERO'})
              </span>
              <p className="text-slate-300 mt-1 text-[11px] leading-tight">{data.reason}</p>
            </div>
          )}

          {data.votes && (
            <div className="space-y-1 pt-1.5 border-t border-slate-800 text-[10px]">
              <div className="text-slate-400 font-semibold uppercase tracking-wider">Council Votes:</div>
              <div className="flex justify-between">
                <span className="text-slate-400">Trend:</span>
                <span className="font-mono text-slate-200">{data.votes.trend?.vote} ({Math.round((data.votes.trend?.confidence || 0)*100)}%)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">News:</span>
                <span className="font-mono text-slate-200">{data.votes.news?.vote} ({Math.round((data.votes.news?.confidence || 0)*100)}%)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Contrarian:</span>
                <span className="font-mono text-slate-200">{data.votes.contrarian?.vote} ({Math.round((data.votes.contrarian?.confidence || 0)*100)}%)</span>
              </div>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  const minPrice = ticks.length ? Math.min(...ticks.map(t => t.price)) * 0.998 : 2800;
  const maxPrice = ticks.length ? Math.max(...ticks.map(t => t.price)) * 1.002 : 2900;

  return (
    <div className="w-full h-[360px] relative">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={ticks} margin={{ top: 15, right: 25, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis 
            dataKey="timeStr" 
            stroke="#64748b" 
            tick={{ fontSize: 11 }} 
            interval="preserveStartEnd"
          />
          <YAxis 
            domain={[minPrice, maxPrice]} 
            stroke="#64748b" 
            orientation="right"
            tick={{ fontSize: 11 }}
            tickFormatter={(val) => `₹${val.toFixed(1)}`}
          />
          <Tooltip content={<CustomTooltip />} />
          
          {lastStopLoss && (
            <ReferenceLine 
              y={lastStopLoss} 
              stroke="#ef4444" 
              strokeDasharray="4 4" 
              label={{ value: `Stop-Loss: ₹${lastStopLoss}`, fill: '#f87171', fontSize: 10, position: 'insideBottomRight' }}
            />
          )}

          <Line
            type="monotone"
            dataKey="price"
            stroke="#06b6d4"
            strokeWidth={2}
            isAnimationActive={false}
            dot={<CustomizedDot />}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Markers Legend */}
      <div className="absolute top-2 left-4 flex items-center gap-4 text-[11px] bg-[#0b0f19]/80 px-2.5 py-1 rounded border border-[#1e293b]">
        <div className="flex items-center gap-1.5 text-emerald-400">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span> BUY Order
        </div>
        <div className="flex items-center gap-1.5 text-rose-400">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span> SELL / Exit
        </div>
        <div className="flex items-center gap-1.5 text-slate-400">
          <span className="w-2 h-2 rounded-full bg-slate-500"></span> HOLD Evaluated
        </div>
        {lastStopLoss && (
          <div className="flex items-center gap-1.5 text-red-400">
            <span className="w-3 h-0.5 bg-red-500"></span> Active Stop-Loss
          </div>
        )}
      </div>
    </div>
  );
}

