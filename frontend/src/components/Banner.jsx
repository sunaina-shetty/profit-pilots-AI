import React from 'react';

export default function Banner({ systemState, killSwitch, dayPnl, equity, cash }) {
  const isKilled = killSwitch === 'ON' || systemState === 'KILLED';
  const isHalted = systemState === 'HALTED_DAILY_LOSS';
  const isStale = systemState === 'DATA_STALE';

  return (
    <header className="bg-[#0f172a] border-b border-[#1e293b] px-4 py-2.5 flex flex-wrap items-center justify-between gap-3 text-sm sticky top-0 z-40">
      {/* Brand & Tagline */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">✈️</span>
          <div>
            <div className="font-bold tracking-wider text-cyan-400 text-base leading-tight">PROFITPILOT <span className="text-xs px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">AI</span></div>
            <div className="text-[10px] text-slate-400 font-mono">FLY FOR PROFIT. LAND SAFE.</div>
          </div>
        </div>

        {/* Paper Trading Warning Badge */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-950/60 border border-amber-600/40 text-amber-300 text-xs font-semibold">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
          PAPER TRADING — VIRTUAL MONEY ONLY
        </div>
      </div>

      {/* System State & Metrics */}
      <div className="flex items-center gap-4">
        {/* Status Badge */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">STATE:</span>
          {isKilled ? (
            <span className="px-2.5 py-1 rounded bg-red-950 text-red-400 border border-red-600 text-xs font-bold animate-pulse">
              🛑 KILLED (ORDERS BLOCKED)
            </span>
          ) : isHalted ? (
            <span className="px-2.5 py-1 rounded bg-amber-950 text-amber-400 border border-amber-600 text-xs font-bold">
              ⚠️ HALTED (DAILY LOSS LIMIT HIT)
            </span>
          ) : isStale ? (
            <span className="px-2.5 py-1 rounded bg-purple-950 text-purple-400 border border-purple-600 text-xs font-bold">
              ⏳ DATA STALE (NO_TRADE)
            </span>
          ) : (
            <span className="px-2.5 py-1 rounded bg-emerald-950 text-emerald-400 border border-emerald-600/50 text-xs font-bold flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> RUNNING
            </span>
          )}
        </div>

        {/* Live Equity */}
        <div className="hidden sm:flex items-center gap-2 bg-[#1e293b]/60 px-3 py-1 rounded border border-[#334155]">
          <span className="text-xs text-slate-400">EQUITY:</span>
          <span className="font-mono font-bold text-slate-100">₹{(equity || 100000).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
        </div>

        {/* Today's P&L */}
        <div className="hidden sm:flex items-center gap-2 bg-[#1e293b]/60 px-3 py-1 rounded border border-[#334155]">
          <span className="text-xs text-slate-400">DAY P&L:</span>
          <span className={`font-mono font-bold ${(dayPnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {(dayPnl || 0) >= 0 ? '+' : ''}₹{(dayPnl || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </span>
        </div>
      </div>
    </header>
  );
}

