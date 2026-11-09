import React, { useState, useEffect } from 'react';
import { Search, ShieldAlert, ArrowUpRight, ArrowDownRight, Activity, Clock, AlertTriangle, Layers } from 'lucide-react';

export default function TopMarketBar({
  symbol,
  onSelectSymbol,
  stocksList = [],
  state,
  isRunning,
  isKilled,
  isDone,
  onStartSimulation,
  onOpenKillModal,
  activeTab,
  setActiveTab
}) {
  const [indices, setIndices] = useState([
    { name: 'NIFTY 50', value: 24997.30, change: 10.90, change_pct: 0.04, is_up: true },
    { name: 'SENSEX', value: 81059.38, change: 59.98, change_pct: 0.07, is_up: true },
    { name: 'BANK NIFTY', value: 59490.60, change: 639.95, change_pct: 1.09, is_up: true },
    { name: 'Crude Oil', value: 8446.00, change: -108.00, change_pct: -1.26, is_up: false, currency: '₹' },
    { name: 'Natural Gas', value: 286.40, change: 1.40, change_pct: 0.49, is_up: true, currency: '₹' },
  ]);

  const [quote, setQuote] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [showDropdown, setShowDropdown] = useState(false);

  // Load top indices
  useEffect(() => {
    fetch('/api/market-indices')
      .then((r) => r.json())
      .then((data) => {
        if (data.indices && data.indices.length > 0) {
          setIndices(data.indices);
        }
      })
      .catch(() => {});
  }, []);

  // Fetch detailed stock quote whenever symbol changes
  useEffect(() => {
    if (!symbol) return;
    fetch(`/api/stock-quote?symbol=${encodeURIComponent(symbol)}`)
      .then((r) => r.json())
      .then((data) => {
        setQuote(data);
      })
      .catch(() => {
        setQuote(null);
      });
  }, [symbol]);

  const filteredStocks = stocksList.filter((s) => {
    const q = searchQuery.toLowerCase();
    return s.symbol.toLowerCase().includes(q) || s.name.toLowerCase().includes(q);
  });

  const getStatusBadge = () => {
    if (isRunning) {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-500/40 animate-pulse">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
          SIMULATION ACTIVE ({state?.simulated_time || '09:15'} • {state?.speed || '20X'})
        </span>
      );
    }
    if (isKilled) {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-950/80 text-rose-400 border border-rose-500/40">
          <span className="w-2 h-2 rounded-full bg-rose-400" />
          TERMINAL HALTED (KILLED)
        </span>
      );
    }
    if (isDone) {
      return (
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-950/80 text-sky-400 border border-sky-500/40">
          <span className="w-2 h-2 rounded-full bg-sky-400" />
          SESSION COMPLETED
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-900 text-slate-400 border border-slate-700">
        <span className="w-2 h-2 rounded-full bg-slate-500" />
        PAPER TRADING (IDLE)
      </span>
    );
  };

  return (
    <header className="bg-[#0b0e14] border-b border-[#1f293d] select-none sticky top-0 z-50">
      {/* Row 1: Logo, Ticker Tape, Search, User Controls */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[#161f30] gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#00c896] to-emerald-400 flex items-center justify-center font-black text-slate-950 text-sm shadow-md shadow-emerald-950/40">
            PP
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-base tracking-wide text-white">PROFITPILOT</span>
              <span className="text-[10px] uppercase font-bold tracking-widest px-1.5 py-0.5 rounded bg-emerald-500/20 text-[#00c896] border border-emerald-500/30">
                TERMINAL
              </span>
            </div>
          </div>
        </div>

        {/* Groww-style Indices Ticker Bar */}
        <div className="hidden lg:flex items-center gap-6 overflow-x-auto no-scrollbar py-0.5">
          {indices.map((idx, i) => (
            <div key={i} className="flex items-center gap-2 whitespace-nowrap text-xs font-medium">
              <span className="text-slate-400 font-semibold">{idx.name}</span>
              <span className="text-white font-mono font-bold">
                {idx.currency || ''}{idx.value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </span>
              <span
                className={`flex items-center text-[11px] font-semibold ${
                  idx.is_up ? 'text-[#00c896]' : 'text-[#eb5757]'
                }`}
              >
                {idx.is_up ? '+' : ''}{idx.change.toFixed(2)} ({idx.is_up ? '+' : ''}{idx.change_pct}%)
              </span>
            </div>
          ))}
        </div>

        {/* Global Search Bar */}
        <div className="relative w-64 shrink-0 hidden md:block">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search Stocks, F&O, Indices..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setShowDropdown(true);
              }}
              onFocus={() => setShowDropdown(true)}
              className="w-full bg-[#121926] text-slate-200 placeholder-slate-500 text-xs rounded-lg pl-8 pr-3 py-2 border border-[#1f293d] focus:outline-none focus:border-[#00c896] transition-colors"
            />
          </div>

          {showDropdown && searchQuery && (
            <div className="absolute left-0 right-0 top-10 bg-[#121926] border border-[#1f293d] rounded-lg shadow-2xl max-h-60 overflow-y-auto z-50">
              {filteredStocks.length > 0 ? (
                filteredStocks.map((st) => (
                  <button
                    key={st.symbol}
                    onClick={() => {
                      onSelectSymbol(st.symbol.replace('.NS', ''));
                      setSearchQuery('');
                      setShowDropdown(false);
                    }}
                    className="w-full text-left px-3 py-2 text-xs hover:bg-[#1a2333] flex items-center justify-between border-b border-[#1a2333] last:border-0"
                  >
                    <div>
                      <span className="font-bold text-white">{st.symbol.replace('.NS', '')}</span>
                      <span className="text-slate-400 ml-2 text-[11px]">{st.name}</span>
                    </div>
                    <span className="text-[10px] text-slate-500 font-mono">NSE</span>
                  </button>
                ))
              ) : (
                <div className="px-3 py-2 text-xs text-slate-500">No matching NSE instruments</div>
              )}
            </div>
          )}
        </div>

        {/* Right Controls: Balance, Kill Switch, User */}
        <div className="flex items-center gap-3 shrink-0">
          {getStatusBadge()}

          {/* Virtual Balance pill */}
          <div className="hidden sm:flex flex-col items-end px-3 py-1 rounded-lg bg-[#121926] border border-[#1f293d]">
            <span className="text-[10px] font-semibold text-slate-400 tracking-wider">PAPER CAPITAL</span>
            <span className="text-xs font-mono font-bold text-emerald-400">
              ₹{(state?.equity || 100000).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
            </span>
          </div>

          {/* Emergency Kill Switch Button */}
          <button
            onClick={onOpenKillModal}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-600/90 hover:bg-rose-500 text-white font-bold text-xs shadow-lg shadow-rose-950/50 transition-all border border-rose-400/40 active:scale-95"
            title="Emergency Kill Switch (Dual Mode: Stop New Trades vs Emergency Flatten)"
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">EMERGENCY KILL</span>
          </button>
        </div>
      </div>

      {/* Row 2: Selected Stock Metrics Bar (Section 3 Requirement) */}
      <div className="flex items-center justify-between px-4 py-1.5 bg-[#0d121c] border-b border-[#161f30] text-xs font-mono overflow-x-auto no-scrollbar gap-4">
        <div className="flex items-center gap-4 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-white font-black text-sm">{quote?.symbol || symbol}</span>
            <span className="text-slate-400 text-xs font-sans truncate max-w-[140px] sm:max-w-none">
              {quote?.name || symbol}
            </span>
            <span className="px-1.5 py-0.2 rounded text-[10px] bg-[#1e293b] text-slate-400">NSE</span>
          </div>

          {quote?.is_available ? (
            <div className="flex items-center gap-3">
              <span className="text-white font-black text-sm">
                ₹{Number(quote.current_price || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </span>
              <span className={`flex items-center text-[11px] font-bold ${
                (quote.change || 0) >= 0 ? 'text-[#00c896]' : 'text-rose-400'
              }`}>
                {(quote.change || 0) >= 0 ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                {(quote.change || 0) >= 0 ? '+' : ''}{quote.change?.toFixed(2)} ({(quote.change || 0) >= 0 ? '+' : ''}{quote.change_pct}%)
              </span>
            </div>
          ) : (
            <span className="px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-500/40 text-[10px] font-bold flex items-center gap-1">
              <AlertTriangle className="w-3 h-3" />
              DATA UNAVAILABLE
            </span>
          )}
        </div>

        {quote?.is_available && (
          <div className="hidden md:flex items-center gap-4 text-slate-400 text-[11px] shrink-0">
            <span>High: <strong className="text-slate-200">₹{Number(quote.day_high || 0).toFixed(2)}</strong></span>
            <span>Low: <strong className="text-slate-200">₹{Number(quote.day_low || 0).toFixed(2)}</strong></span>
            <span>Prev Close: <strong className="text-slate-200">₹{Number(quote.prev_close || 0).toFixed(2)}</strong></span>
            <span>Vol: <strong className="text-slate-200">{Number(quote.volume || 0).toLocaleString('en-IN')}</strong></span>
            <span className="flex items-center gap-1 text-[10px] text-emerald-400 font-sans">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              Market Open
            </span>
          </div>
        )}
      </div>

      {/* Row 3: All 10 Groww-Style Navigation Tabs */}
      <div className="flex items-center justify-between px-4 overflow-x-auto no-scrollbar bg-[#0f141f]">
        <div className="flex items-center gap-1">
          {[
            { id: 'dashboard', label: 'Dashboard' },
            { id: 'markets', label: 'Markets' },
            { id: 'terminal', label: 'Trading Terminal' },
            { id: 'strategies', label: 'Strategy Library' },
            { id: 'agents', label: 'Agent Configuration' },
            { id: 'portfolio', label: 'Portfolio' },
            { id: 'orders', label: 'Trade History' },
            { id: 'signals', label: 'Signal Inspector' },
            { id: 'risk', label: 'Risk Management' },
            { id: 'news', label: 'News Intelligence' },
            { id: 'backtest', label: 'Backtesting' },
            { id: 'settings', label: 'Settings' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-2 text-xs font-semibold whitespace-nowrap transition-all border-b-2 ${
                activeTab === tab.id
                  ? 'border-[#00c896] text-[#00c896] bg-[#00c896]/10'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Quick Stock Switcher Dropdown */}
        <div className="flex items-center gap-2 py-1 shrink-0">
          <span className="text-[11px] text-slate-400 font-medium">Quick Select:</span>
          <select
            value={symbol}
            onChange={(e) => onSelectSymbol(e.target.value)}
            className="bg-[#121926] text-white text-xs font-bold rounded px-2.5 py-1 border border-[#1f293d] focus:outline-none focus:border-[#00c896]"
          >
            {stocksList.map((st) => (
              <option key={st.symbol} value={st.symbol.replace('.NS', '')}>
                {st.display || st.symbol}
              </option>
            ))}
          </select>
        </div>
      </div>
    </header>
  );
}
