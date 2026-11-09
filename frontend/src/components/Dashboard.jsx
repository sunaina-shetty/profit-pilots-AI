import React from 'react';
import { Play, TrendingUp, TrendingDown, ShieldAlert, Cpu, Newspaper, Activity, ArrowRight, BarChart2, Layers } from 'lucide-react';

export default function Dashboard({
  state,
  symbol,
  onNavigateToTab,
  onStartSimulation,
  onOpenKillModal,
  isRunning
}) {
  const equity = state?.equity || 100000;
  const dayPnl = state?.day_pnl || 0;
  const position = state?.position;
  const tradesCount = state?.portfolio?.total_trades || (state?.sell_markers?.length || 0);

  const trend = state?.latest_agents?.trend || { signal: 'HOLD', score: 0.0, reason: 'Awaiting market open indicators' };
  const news = state?.latest_agents?.news || { classification: 'NEUTRAL', sentiment: '+0.00', reason: 'Scanning morning headlines' };
  const contrarian = state?.latest_agents?.contrarian || { signal: 'HOLD', score: 0.0, reason: 'Checking statistical range' };
  const council = state?.latest_decision || { action: 'HOLD', regime: state?.current_regime || 'UNCLEAR', reason: 'Awaiting trade setup' };

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      {/* 1. Executive Banner */}
      <div className="bg-gradient-to-r from-[#0f141f] via-[#121926] to-[#0f141f] border border-[#1f293d] rounded-2xl p-6 shadow-xl flex flex-col lg:flex-row justify-between items-start lg:items-center gap-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-[#00c896] to-emerald-400 flex items-center justify-center font-black text-slate-950 text-base shadow-lg shadow-emerald-950/50">
              PP
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-black text-white tracking-wide">ProfitPilot AI Terminal</h1>
                <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-emerald-500/20 text-[#00c896] border border-emerald-500/30">
                  Groww Institutional V2
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Multi-Agent Autonomous Intraday Paper-Trading Terminal with 10 Quantitative Strategies & Council Consensus.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onNavigateToTab('terminal')}
            className="px-5 py-2.5 rounded-xl bg-[#00c896] hover:bg-emerald-400 text-black font-extrabold text-xs shadow-lg shadow-emerald-950/40 transition-all flex items-center gap-2 active:scale-95"
          >
            <BarChart2 className="w-4 h-4" />
            <span>Launch Trading Terminal</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => onNavigateToTab('strategies')}
            className="px-4 py-2.5 rounded-xl bg-[#161f30] hover:bg-slate-700 text-white font-bold text-xs border border-[#1f293d] transition-all flex items-center gap-2"
          >
            <Layers className="w-4 h-4 text-emerald-400" />
            <span>Configure Strategies</span>
          </button>
        </div>
      </div>

      {/* 2. Key Metrics Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Paper Capital */}
        <div className="bg-[#0f141f] border border-[#1f293d] rounded-xl p-4 shadow-sm">
          <span className="text-slate-400 text-xs font-semibold uppercase">Total Portfolio Capital</span>
          <div className="text-2xl font-mono font-black text-white mt-1">
            ₹{equity.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <span className="text-[11px] text-emerald-400 font-mono mt-1 block">Virtual Paper Account</span>
        </div>

        {/* Day P&L */}
        <div className="bg-[#0f141f] border border-[#1f293d] rounded-xl p-4 shadow-sm">
          <span className="text-slate-400 text-xs font-semibold uppercase">Today's Realized P&L</span>
          <div className={`text-2xl font-mono font-black mt-1 ${dayPnl >= 0 ? 'text-[#00c896]' : 'text-rose-400'}`}>
            {dayPnl >= 0 ? '+₹' : '-₹'}{Math.abs(dayPnl).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <span className="text-[11px] text-slate-400 font-mono mt-1 block">Charges modeled</span>
        </div>

        {/* Active Position */}
        <div className="bg-[#0f141f] border border-[#1f293d] rounded-xl p-4 shadow-sm">
          <span className="text-slate-400 text-xs font-semibold uppercase">Open Intraday Position</span>
          <div className="text-lg font-mono font-bold text-white mt-1 truncate">
            {position ? `${position.side} ${position.qty} @ ₹${position.entry_price}` : 'FLAT (0 Open)'}
          </div>
          <span className={`text-[11px] font-mono mt-1 block ${position ? 'text-emerald-400 font-bold' : 'text-slate-500'}`}>
            {position ? `Stop: ₹${position.stop_loss} | Tgt: ₹${position.target}` : 'Awaiting Council Signal'}
          </span>
        </div>

        {/* Total Trades Executed */}
        <div className="bg-[#0f141f] border border-[#1f293d] rounded-xl p-4 shadow-sm">
          <span className="text-slate-400 text-xs font-semibold uppercase">Trades Closed Today</span>
          <div className="text-2xl font-mono font-black text-sky-400 mt-1">
            {tradesCount} trades
          </div>
          <span className="text-[11px] text-slate-400 font-mono mt-1 block">Max limit: 6 trades/day</span>
        </div>
      </div>

      {/* 3. Multi-Agent Consensus Radar */}
      <div className="bg-[#0f141f] border border-[#1f293d] rounded-2xl p-5 shadow-lg space-y-4">
        <div className="flex justify-between items-center border-b border-[#1f293d] pb-3">
          <div className="flex items-center gap-2">
            <Cpu className="w-5 h-5 text-emerald-400" />
            <h2 className="text-base font-bold text-white">Multi-Agent Cooperating Matrix</h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            Replay Status: {state?.simulated_time || '09:15'} IST | Regime: <strong>{state?.current_regime || 'UNCLEAR'}</strong>
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          {/* Agent 1 */}
          <div className="bg-[#121926] border border-[#1f293d] rounded-xl p-4 space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-bold text-slate-200">Agent 1: Trend & Breakout</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-black ${
                trend.signal === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500' :
                trend.signal === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-500' : 'bg-slate-800 text-slate-400'
              }`}>
                {trend.signal || 'HOLD'}
              </span>
            </div>
            <div className="text-slate-400 font-mono text-[11px]">
              Conviction: <strong className="text-white">{trend.score !== undefined ? `${trend.score > 0 ? '+' : ''}${trend.score.toFixed(2)}` : '0.00'}</strong>
            </div>
            <p className="text-[11px] text-slate-400 line-clamp-2 italic">"{trend.reason || 'Scanning setup'}"</p>
          </div>

          {/* Agent 2 */}
          <div className="bg-[#121926] border border-[#1f293d] rounded-xl p-4 space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-bold text-slate-200">Agent 2: News Intelligence</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-black ${
                news.veto_buy ? 'bg-rose-950 text-rose-400 border border-rose-500' : 'bg-sky-950 text-sky-400 border border-sky-500'
              }`}>
                {news.veto_buy ? 'VETO' : (news.classification || 'NEUTRAL')}
              </span>
            </div>
            <div className="text-slate-400 font-mono text-[11px]">
              Sentiment: <strong className="text-white">{news.sentiment || '+0.00'}</strong>
            </div>
            <p className="text-[11px] text-slate-400 line-clamp-2 italic">"{news.reason || 'Monitoring news feeds'}"</p>
          </div>

          {/* Agent 3 */}
          <div className="bg-[#121926] border border-[#1f293d] rounded-xl p-4 space-y-2">
            <div className="flex justify-between items-center">
              <span className="font-bold text-slate-200">Agent 3: Mean Reversion</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-black ${
                contrarian.signal === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500' :
                contrarian.signal === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-500' : 'bg-slate-800 text-slate-400'
              }`}>
                {contrarian.signal || 'HOLD'}
              </span>
            </div>
            <div className="text-slate-400 font-mono text-[11px]">
              Conviction: <strong className="text-white">{contrarian.score !== undefined ? `${contrarian.score > 0 ? '+' : ''}${contrarian.score.toFixed(2)}` : '0.00'}</strong>
            </div>
            <p className="text-[11px] text-slate-400 line-clamp-2 italic">"{contrarian.reason || 'Checking statistical range'}"</p>
          </div>

          {/* Council */}
          <div className="bg-[#141b29] border border-blue-500/40 rounded-xl p-4 space-y-2 shadow-sm">
            <div className="flex justify-between items-center">
              <span className="font-bold text-white">Council Consensus Gate</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-black ${
                council.action === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500' :
                council.action === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-500' : 'bg-slate-800 text-slate-300'
              }`}>
                {council.action || 'HOLD'}
              </span>
            </div>
            <div className="text-slate-400 font-mono text-[11px]">
              Regime: <strong className="text-purple-400">{state?.current_regime || 'UNCLEAR'}</strong>
            </div>
            <p className="text-[11px] text-slate-300 line-clamp-2 italic">"{council.reason || 'Waiting for consensus threshold'}"</p>
          </div>
        </div>
      </div>

      {/* 4. Quick Action Modules */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Quantitative Backtesting Lab Shortcut */}
        <div
          onClick={() => onNavigateToTab('backtest')}
          className="bg-[#0f141f] border border-[#1f293d] rounded-2xl p-5 hover:border-[#00c896]/50 cursor-pointer transition-all shadow-md group"
        >
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-sm font-bold text-white group-hover:text-[#00c896] transition-colors">
              Quantitative Backtesting Lab
            </h3>
            <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-[#00c896] transition-colors" />
          </div>
          <p className="text-xs text-slate-400">
            Run multi-day backtests across 10 strategies with Sharpe ratio, profit factor, max drawdown, and equity curves.
          </p>
        </div>

        {/* Strategy Library Shortcut */}
        <div
          onClick={() => onNavigateToTab('strategies')}
          className="bg-[#0f141f] border border-[#1f293d] rounded-2xl p-5 hover:border-[#00c896]/50 cursor-pointer transition-all shadow-md group"
        >
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-sm font-bold text-white group-hover:text-[#00c896] transition-colors">
              Strategy Library (10 Active)
            </h3>
            <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-[#00c896] transition-colors" />
          </div>
          <p className="text-xs text-slate-400">
            Inspect entry/exit formulas, parameters, and assign strategies dynamically to Agent 1 and Agent 3.
          </p>
        </div>

        {/* Risk Management Shortcut */}
        <div
          onClick={() => onNavigateToTab('risk')}
          className="bg-[#0f141f] border border-[#1f293d] rounded-2xl p-5 hover:border-[#00c896]/50 cursor-pointer transition-all shadow-md group"
        >
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-sm font-bold text-white group-hover:text-[#00c896] transition-colors">
              Risk Management Controls
            </h3>
            <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-[#00c896] transition-colors" />
          </div>
          <p className="text-xs text-slate-400">
            Independent stop-loss guards, position sizing rules, daily loss limits, and emergency kill switch controls.
          </p>
        </div>
      </div>
    </div>
  );
}

