import React, { useState } from 'react';
import { Briefcase, List, Layers, ShieldCheck, PieChart, Users, ChevronRight, ChevronLeft, ArrowUpRight, ArrowDownRight } from 'lucide-react';

export default function RightDock({
  state,
  isRunning,
  symbol,
  onSelectSymbol,
  stocksList = [],
  currentPrice = 0.0
}) {
  const [activeDockTab, setActiveDockTab] = useState('council'); // 'council' | 'positions' | 'watchlist' | 'depth' | 'holdings'
  const [isExpanded, setIsExpanded] = useState(true);

  const pos = state?.position;
  const portfolio = state?.portfolio || {};
  const council = state?.latest_agents?.council || {};
  const trend = state?.latest_agents?.trend || {};
  const news = state?.latest_agents?.news || {};
  const contrarian = state?.latest_agents?.contrarian || {};
  const decision = state?.latest_decision || {};

  const tabs = [
    { id: 'council', label: 'Council', icon: Users },
    { id: 'positions', label: 'Positions', icon: Briefcase, badge: pos ? '1' : null },
    { id: 'watchlist', label: 'Watchlist', icon: List },
    { id: 'depth', label: 'Depth', icon: Layers },
    { id: 'holdings', label: 'Ledger', icon: PieChart },
  ];

  return (
    <div className="flex h-full bg-[#0b0e14] border-l border-[#1f293d] select-none text-xs">
      {/* Expanded Content Panel */}
      {isExpanded && (
        <div className="w-80 flex flex-col h-full bg-[#0e131d] border-r border-[#1a2333] overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2.5 border-b border-[#1a2333] bg-[#121824]">
            <span className="font-bold text-white uppercase tracking-wider text-[11px] flex items-center gap-1.5">
              {tabs.find((t) => t.id === activeDockTab)?.label || 'Dock'}
            </span>
            <button
              onClick={() => setIsExpanded(false)}
              className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800"
              title="Collapse Dock"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Tab Body */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {/* 1. COUNCIL & AGENTS TAB */}
            {activeDockTab === 'council' && (
              <div className="space-y-3">
                {/* Consensus Decision Meter */}
                <div className="p-3 rounded-lg bg-[#141b29] border border-[#1f293d]">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold text-slate-300">Council Consensus</span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-black tracking-wider ${
                        decision.action === 'BUY'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/50'
                          : decision.action === 'SELL'
                          ? 'bg-rose-950 text-rose-400 border border-rose-500/50'
                          : 'bg-slate-800 text-slate-300 border border-slate-700'
                      }`}
                    >
                      {decision.action || 'HOLD'}
                    </span>
                  </div>

                  <div className="space-y-1.5 font-mono text-[11px]">
                    <div className="flex justify-between text-slate-400">
                      <span>Conviction Score:</span>
                      <span className="font-bold text-white">{(decision.score ?? 0.0) > 0 ? '+' : ''}{(decision.score ?? 0.0).toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Agreement / Confidence:</span>
                      <span className="font-bold text-emerald-400">{(decision.confidence ?? 0).toFixed(0)}%</span>
                    </div>
                    <div className="flex justify-between text-slate-400">
                      <span>Market Regime:</span>
                      <span className="font-bold text-purple-400">{state.current_regime || 'UNCLEAR'}</span>
                    </div>
                  </div>

                  {decision.rule && (
                    <div className="mt-2 text-[10px] text-slate-400 italic bg-[#0f1420] p-1.5 rounded border border-[#1a2333]">
                      "{decision.rule}"
                    </div>
                  )}
                </div>

                {/* Agent 1 Card */}
                <div className="p-2.5 rounded-lg bg-[#121824] border border-[#1a2333] space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200 text-[11px] truncate">
                      {trend.agent_name || 'Agent 1: Trend'}
                    </span>
                    <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                      trend.signal === 'BUY' ? 'text-emerald-400 bg-emerald-950/60' :
                      trend.signal === 'SELL' ? 'text-rose-400 bg-rose-950/60' : 'text-slate-400 bg-slate-800'
                    }`}>
                      {trend.signal || 'HOLD'}
                    </span>
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                    <span>Score: {trend.score !== undefined ? `${trend.score > 0 ? '+' : ''}${trend.score.toFixed(2)}` : '0.00'}</span>
                    <span>Conf: {(trend.confidence ?? 0).toFixed(0)}%</span>
                  </div>
                  {trend.reason && (
                    <div className="text-[10px] text-slate-400 line-clamp-2 leading-tight">
                      {trend.reason}
                    </div>
                  )}
                </div>

                {/* Agent 2 Card */}
                <div className="p-2.5 rounded-lg bg-[#121824] border border-[#1a2333] space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200 text-[11px]">
                      Agent 2: News Intelligence
                    </span>
                    <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                      news.veto_buy ? 'text-rose-400 bg-rose-950/60' : 'text-sky-400 bg-sky-950/60'
                    }`}>
                      {news.veto_buy ? 'VETO ACTIVE' : (news.classification || 'NEUTRAL')}
                    </span>
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                    <span>Sentiment: {news.sentiment || '+0.00'}</span>
                    <span>Headlines: {news.facts?.headlines_count || 0}</span>
                  </div>
                  {news.reason && (
                    <div className="text-[10px] text-slate-400 line-clamp-2 leading-tight">
                      {news.reason}
                    </div>
                  )}
                </div>

                {/* Agent 3 Card */}
                <div className="p-2.5 rounded-lg bg-[#121824] border border-[#1a2333] space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-200 text-[11px] truncate">
                      {contrarian.agent_name || 'Agent 3: Mean Reversion'}
                    </span>
                    <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                      contrarian.signal === 'BUY' ? 'text-emerald-400 bg-emerald-950/60' :
                      contrarian.signal === 'SELL' ? 'text-rose-400 bg-rose-950/60' : 'text-slate-400 bg-slate-800'
                    }`}>
                      {contrarian.signal || 'HOLD'}
                    </span>
                  </div>
                  <div className="flex justify-between text-[10px] text-slate-400 font-mono">
                    <span>Score: {contrarian.score !== undefined ? `${contrarian.score > 0 ? '+' : ''}${contrarian.score.toFixed(2)}` : '0.00'}</span>
                    <span>Conf: {(contrarian.confidence ?? 0).toFixed(0)}%</span>
                  </div>
                  {contrarian.reason && (
                    <div className="text-[10px] text-slate-400 line-clamp-2 leading-tight">
                      {contrarian.reason}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* 2. POSITIONS TAB */}
            {activeDockTab === 'positions' && (
              <div className="space-y-3">
                {pos ? (
                  <div className="p-3 rounded-lg bg-[#141b29] border border-emerald-500/30 space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-white text-xs">{pos.symbol}</span>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-950 text-emerald-400 border border-emerald-500/40">
                        {pos.side} • {pos.qty} QTY
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
                      <div>
                        <span className="text-slate-400 text-[10px] block">Entry Price:</span>
                        <span className="font-bold text-white">₹{pos.buy_price.toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 text-[10px] block">Current Price:</span>
                        <span className="font-bold text-white">₹{(pos.current_price || currentPrice).toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 text-[10px] block">Active Stop:</span>
                        <span className="font-bold text-rose-400">₹{(pos.stop_loss || 0).toFixed(2)}</span>
                      </div>
                      <div>
                        <span className="text-slate-400 text-[10px] block">Unrealized P&L:</span>
                        <span className={`font-bold ${(pos.profit_loss || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {(pos.profit_loss || 0) >= 0 ? '+₹' : '-₹'}{Math.abs(pos.profit_loss || 0).toFixed(2)}
                        </span>
                      </div>
                    </div>

                    <div className="pt-2 border-t border-[#1f293d] flex justify-between items-center text-[10px] text-slate-400">
                      <span>Time: {pos.buy_time}</span>
                      <span>Type: {pos.entry_type?.toUpperCase()}</span>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 text-center text-slate-500 space-y-1">
                    <Briefcase className="w-8 h-8 mx-auto text-slate-600 mb-2 opacity-50" />
                    <div className="font-semibold text-slate-400">No Open Positions</div>
                    <div className="text-[10px]">Agents are scanning for high-probability setups</div>
                  </div>
                )}
              </div>
            )}

            {/* 3. WATCHLIST TAB */}
            {activeDockTab === 'watchlist' && (
              <div className="space-y-1">
                {stocksList.map((st) => {
                  const cleanSym = st.symbol.replace('.NS', '');
                  const isCurrent = cleanSym === symbol.replace('.NS', '');
                  return (
                    <button
                      key={st.symbol}
                      onClick={() => onSelectSymbol(cleanSym)}
                      className={`w-full text-left p-2 rounded-lg transition-all flex items-center justify-between border ${
                        isCurrent
                          ? 'bg-[#00c896]/10 border-[#00c896]/40 text-white'
                          : 'bg-[#121824] border-[#1a2333] hover:bg-[#161f30] text-slate-300'
                      }`}
                    >
                      <div>
                        <div className="font-bold text-xs">{cleanSym}</div>
                        <div className="text-[10px] text-slate-400 truncate max-w-[140px]">{st.name}</div>
                      </div>
                      <div className="text-right font-mono">
                        <span className="text-[10px] text-slate-400 block">NSE EQ</span>
                        {isCurrent && <span className="text-[10px] text-[#00c896] font-bold">Active</span>}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}

            {/* 4. DEPTH TAB (Order Book Simulation) */}
            {activeDockTab === 'depth' && (
              <div className="space-y-2 font-mono text-[11px]">
                <div className="text-slate-400 text-[10px] font-bold uppercase tracking-wider mb-1">
                  Market Depth (Top 5 Bids & Asks)
                </div>
                <div className="grid grid-cols-2 gap-2 text-center text-[10px] text-slate-400 border-b border-[#1f293d] pb-1">
                  <div>BID (BUY)</div>
                  <div>ASK (SELL)</div>
                </div>

                {[0, 1, 2, 3, 4].map((idx) => {
                  const bidPrice = (currentPrice * (1.0 - 0.0005 * (idx + 1))).toFixed(2);
                  const askPrice = (currentPrice * (1.0 + 0.0005 * (idx + 1))).toFixed(2);
                  const bidQty = (250 + idx * 110) * (5 - idx);
                  const askQty = (210 + idx * 140) * (5 - idx);

                  return (
                    <div key={idx} className="grid grid-cols-2 gap-2 text-[10px]">
                      <div className="flex justify-between bg-emerald-950/20 px-1.5 py-0.5 rounded text-emerald-300">
                        <span>{bidQty}</span>
                        <span className="font-bold">₹{bidPrice}</span>
                      </div>
                      <div className="flex justify-between bg-rose-950/20 px-1.5 py-0.5 rounded text-rose-300">
                        <span className="font-bold">₹{askPrice}</span>
                        <span>{askQty}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* 5. LEDGER / HOLDINGS TAB */}
            {activeDockTab === 'holdings' && (
              <div className="space-y-2 font-mono text-xs">
                <div className="p-2.5 rounded-lg bg-[#141b29] border border-[#1f293d] space-y-1.5">
                  <div className="flex justify-between text-slate-400">
                    <span>Available Cash:</span>
                    <span className="text-white font-bold">₹{(portfolio.available_cash || state.cash || 100000).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Invested Capital:</span>
                    <span className="text-white font-bold">₹{(portfolio.invested_capital || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Total Portfolio Equity:</span>
                    <span className="text-emerald-400 font-bold">₹{(portfolio.total_equity || state.equity || 100000).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Realized P&L:</span>
                    <span className={`font-bold ${(portfolio.realized_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {(portfolio.realized_pnl || 0) >= 0 ? '+₹' : '-₹'}{Math.abs(portfolio.realized_pnl || 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between text-slate-400">
                    <span>Trade Fees (Bot Fee Removed):</span>
                    <span className="text-emerald-400 font-bold">₹0.00</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Dock Sidebar Icons Strip (Always visible) */}
      <div className="w-12 flex flex-col items-center py-2 gap-3 bg-[#0b0e14]">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-2 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title={isExpanded ? 'Collapse Dock' : 'Expand Dock'}
        >
          {isExpanded ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>

        <div className="w-6 border-b border-[#1f293d]" />

        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeDockTab === tab.id && isExpanded;
          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveDockTab(tab.id);
                setIsExpanded(true);
              }}
              className={`relative p-2 rounded-lg transition-all flex flex-col items-center gap-0.5 ${
                isActive
                  ? 'bg-[#00c896]/20 text-[#00c896] border border-[#00c896]/40'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-[#161f30]'
              }`}
              title={tab.label}
            >
              <Icon className="w-4 h-4" />
              <span className="text-[9px] font-semibold tracking-tighter">{tab.label.slice(0, 4)}</span>
              {tab.badge && (
                <span className="absolute -top-1 -right-1 w-3.5 h-3.5 rounded-full bg-emerald-500 text-black text-[9px] font-bold flex items-center justify-center">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

