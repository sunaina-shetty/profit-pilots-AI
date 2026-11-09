import React, { useState } from 'react';
import { TrendingUp, TrendingDown, Clock, Search, ExternalLink, Activity, ArrowUpRight, ArrowDownRight } from 'lucide-react';

export default function MarketsOverview({ stocksList = [], onSelectStockForTerminal }) {
  const [search, setSearch] = useState('');

  const INDICES = [
    { name: 'NIFTY 50', value: 24997.30, change: 10.90, change_pct: 0.04, high: 25042.80, low: 24945.10, is_up: true },
    { name: 'SENSEX', value: 81059.38, change: 59.98, change_pct: 0.07, high: 81210.50, low: 80920.30, is_up: true },
    { name: 'BANK NIFTY', value: 59490.60, change: 639.95, change_pct: 1.09, high: 59610.00, low: 58980.20, is_up: true },
    { name: 'NIFTY IT', value: 42180.40, change: -145.20, change_pct: -0.34, high: 42450.00, low: 42090.10, is_up: false },
    { name: 'NIFTY AUTO', value: 26110.80, change: 180.50, change_pct: 0.70, high: 26230.00, low: 25950.00, is_up: true },
    { name: 'Crude Oil', value: 8446.00, change: -108.00, change_pct: -1.26, high: 8590.00, low: 8420.00, is_up: false, currency: '₹' },
    { name: 'Natural Gas', value: 286.40, change: 1.40, change_pct: 0.49, high: 291.50, low: 283.00, is_up: true, currency: '₹' },
    { name: 'Gold (10g)', value: 78450.00, change: 290.00, change_pct: 0.37, high: 78600.00, low: 78200.00, is_up: true, currency: '₹' },
  ];

  const SECTORS = [
    { name: 'Banking & Financials', change: '+1.09%', is_up: true, weight: '36.8%' },
    { name: 'Information Technology', change: '-0.34%', is_up: false, weight: '13.4%' },
    { name: 'Oil & Gas / Energy', change: '-0.52%', is_up: false, weight: '11.2%' },
    { name: 'Automobile', change: '+0.70%', is_up: true, weight: '7.5%' },
    { name: 'FMCG & Consumer', change: '+0.15%', is_up: true, weight: '8.1%' },
    { name: 'Metals & Mining', change: '+1.45%', is_up: true, weight: '3.9%' },
    { name: 'Pharmaceuticals', change: '+0.28%', is_up: true, weight: '3.8%' },
  ];

  const filteredStocks = stocksList.filter((s) => {
    const q = search.toLowerCase();
    return s.symbol.toLowerCase().includes(q) || s.name.toLowerCase().includes(q);
  });

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      {/* Market Status Banner */}
      <div className="bg-[#0f141f] border border-[#1f293d] rounded-2xl p-5 shadow-lg flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h1 className="text-xl font-bold text-white tracking-wide">National Stock Exchange (NSE) Market Radar</h1>
            <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-emerald-500/20 text-[#00c896] border border-emerald-500/30">
              Live Session (09:15 - 15:30 IST)
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Real-time multi-asset indices, benchmark equity performance, and automated strategy-eligible stock universe.
          </p>
        </div>

        <div className="flex items-center gap-3 text-xs font-mono bg-[#161f30] px-4 py-2 rounded-xl border border-[#1f293d]">
          <Clock className="w-4 h-4 text-emerald-400" />
          <span className="text-slate-300">Intraday Trading Hours: <strong>09:15 - 15:30 IST</strong></span>
        </div>
      </div>

      {/* Major Indices Grid */}
      <div>
        <h2 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-3">Major Benchmark Indices</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {INDICES.map((idx) => (
            <div key={idx.name} className="bg-[#0f141f] border border-[#1f293d] rounded-xl p-4 shadow-sm hover:border-[#2f3e5c] transition-all">
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-slate-300">{idx.name}</span>
                <span className={`flex items-center text-[11px] font-bold ${idx.is_up ? 'text-[#00c896]' : 'text-rose-400'}`}>
                  {idx.is_up ? <ArrowUpRight className="w-3.5 h-3.5" /> : <ArrowDownRight className="w-3.5 h-3.5" />}
                  {idx.is_up ? '+' : ''}{idx.change_pct}%
                </span>
              </div>
              <div className="text-lg font-mono font-black text-white mt-2">
                {idx.currency || ''}{idx.value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-2 pt-2 border-t border-[#1a2333]">
                <span>L: {idx.low.toLocaleString('en-IN')}</span>
                <span>H: {idx.high.toLocaleString('en-IN')}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Sector Performance Bar */}
      <div className="bg-[#0f141f] border border-[#1f293d] rounded-2xl p-5 shadow-lg">
        <h2 className="text-sm font-bold text-slate-300 uppercase tracking-wider mb-3">Key Sector Heatmap</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-2">
          {SECTORS.map((sec) => (
            <div key={sec.name} className="bg-[#121926] border border-[#1f293d] rounded-lg p-2.5 text-center">
              <span className="text-[10px] text-slate-400 font-semibold block truncate" title={sec.name}>{sec.name}</span>
              <span className={`text-xs font-mono font-bold block mt-1 ${sec.is_up ? 'text-[#00c896]' : 'text-rose-400'}`}>
                {sec.change}
              </span>
              <span className="text-[9px] text-slate-500 font-mono">Weight: {sec.weight}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Available Stock Universe Table */}
      <div className="bg-[#0f141f] border border-[#1f293d] rounded-2xl p-5 shadow-lg space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">Trading Strategy Stock Universe</h2>
            <span className="text-xs text-slate-400">High-liquidity NSE instruments eligible for multi-agent algorithmic execution</span>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-2.5 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search instrument..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-[#161f30] text-slate-200 placeholder-slate-500 text-xs rounded-lg pl-8 pr-3 py-2 border border-[#1f293d] focus:outline-none focus:border-[#00c896]"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-[#161f30] text-slate-400 uppercase text-[10px]">
              <tr>
                <th className="p-3">Symbol</th>
                <th className="p-3">Company Name</th>
                <th className="p-3">Exchange</th>
                <th className="p-3">Type</th>
                <th className="p-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1f293d]">
              {filteredStocks.map((st) => (
                <tr key={st.symbol} className="hover:bg-[#121926]/50 transition-colors">
                  <td className="p-3 font-bold text-white flex items-center gap-2">
                    <span className="w-6 h-6 rounded bg-emerald-500/10 text-[#00c896] border border-emerald-500/30 flex items-center justify-center text-[10px] font-black">
                      {st.symbol.slice(0, 2)}
                    </span>
                    {st.symbol.replace('.NS', '')}
                  </td>
                  <td className="p-3 text-slate-300 font-sans">{st.name}</td>
                  <td className="p-3 text-slate-400">NSE EQ</td>
                  <td className="p-3">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[#1e293b] text-slate-300 border border-slate-700">
                      INTRADAY
                    </span>
                  </td>
                  <td className="p-3 text-right">
                    <button
                      onClick={() => onSelectStockForTerminal(st.symbol.replace('.NS', ''))}
                      className="px-3 py-1.5 rounded-lg bg-[#00c896]/10 hover:bg-[#00c896] text-[#00c896] hover:text-black font-extrabold text-[11px] border border-[#00c896]/30 hover:border-[#00c896] transition-all inline-flex items-center gap-1.5 active:scale-95"
                    >
                      <span>Open in Terminal</span>
                      <ExternalLink className="w-3 h-3" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

