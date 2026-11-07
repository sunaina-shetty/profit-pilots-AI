import React from 'react';

export default function LossLimitMeter({ usedPct = 0, limitAmount = 2000, dayPnl = 0, onResetLimit }) {
  const isHalted = usedPct >= 100;
  const isWarn = usedPct >= 50 && !isHalted;

  return (
    <div className={`p-3 rounded-lg border transition-colors ${
      isHalted ? 'bg-red-950/40 border-red-600/70' :
      isWarn ? 'bg-amber-950/30 border-amber-600/50' :
      'bg-[#1e293b]/50 border-[#334155]'
    }`}>
      <div className="flex items-center justify-between text-xs mb-1.5">
        <div className="flex items-center gap-1.5 font-semibold text-slate-300">
          <span>🛑</span> DAILY LOSS LIMIT (2% SOD EQUALITY)
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-slate-400">
            Cap: ₹{limitAmount?.toLocaleString('en-IN')}
          </span>
          <span className={`font-mono font-bold ${
            isHalted ? 'text-rose-400' : isWarn ? 'text-amber-400' : 'text-emerald-400'
          }`}>
            {usedPct?.toFixed(1)}% used
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-800 rounded-full h-2.5 overflow-hidden relative">
        <div
          className={`h-full transition-all duration-300 ${
            isHalted ? 'bg-red-500 animate-pulse' :
            isWarn ? 'bg-amber-500' : 'bg-emerald-500'
          }`}
          style={{ width: `${Math.min(100, Math.max(0, usedPct))}%` }}
        />
      </div>

      {/* State or Reset Prompt */}
      {isHalted ? (
        <div className="mt-2 flex items-center justify-between text-xs text-rose-300 bg-red-900/40 p-2 rounded border border-red-700/50">
          <span className="font-bold">⚠️ TRADING HALTED - DAILY LOSS LIMIT HIT (PROTECTING CAPITAL)</span>
          {onResetLimit && (
            <button
              onClick={onResetLimit}
              className="px-2 py-0.5 rounded bg-red-700 hover:bg-red-600 text-white font-semibold text-[11px]"
            >
              Reset for Demo
            </button>
          )}
        </div>
      ) : (
        <div className="mt-1 text-[11px] text-slate-400 flex justify-between">
          <span>Loss limit prevents emotional drawdown during adverse market regimes.</span>
          <span>Day P&L: ₹{dayPnl?.toFixed(2)}</span>
        </div>
      )}
    </div>
  );
}

