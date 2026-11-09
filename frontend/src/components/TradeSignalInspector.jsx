import React, { useState } from 'react';
import { Search, Filter, CheckCircle2, AlertTriangle, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

export default function TradeSignalInspector({ journal = [], selectedMarker = null }) {
  const [filterAction, setFilterAction] = useState('ALL'); // 'ALL' | 'BUY' | 'SELL' | 'HOLD'
  const [searchTerm, setSearchTerm] = useState('');

  const filteredJournal = journal.filter((entry) => {
    if (filterAction !== 'ALL' && entry.action !== filterAction) return false;
    if (searchTerm) {
      const q = searchTerm.toLowerCase();
      return (
        entry.time?.toLowerCase().includes(q) ||
        entry.reason?.toLowerCase().includes(q) ||
        entry.action?.toLowerCase().includes(q)
      );
    }
    return true;
  });

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 select-none font-mono">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1f293d] pb-4 font-sans">
        <div>
          <h2 className="text-xl font-extrabold text-white tracking-wide flex items-center gap-2">
            <span>Trade Signal & Agent Consensus Inspector</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
              {journal.length} Decision Logs
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Auditable bar-by-bar log detailing individual agent scores, confidence metrics, and council voting outcomes.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-2">
          <div className="flex bg-[#121926] rounded-lg p-0.5 border border-[#1f293d] text-xs">
            {['ALL', 'BUY', 'SELL', 'HOLD'].map((act) => (
              <button
                key={act}
                onClick={() => setFilterAction(act)}
                className={`px-3 py-1 rounded-md font-bold transition-all ${
                  filterAction === act
                    ? 'bg-[#1a2333] text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {act}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Selected Marker Highlight (if user clicked a chart arrow/dot) */}
      {selectedMarker && (
        <div className="p-4 rounded-xl bg-[#121a28] border border-blue-500/50 space-y-2 font-sans">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-blue-400 uppercase tracking-wider">
              Inspecting Chart Marker @ {selectedMarker.time_str || selectedMarker.time}
            </span>
            <span className={`px-2 py-0.5 rounded text-xs font-bold ${
              selectedMarker.action === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500' :
              selectedMarker.action === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-500' : 'bg-slate-800 text-slate-300'
            }`}>
              {selectedMarker.action}
            </span>
          </div>
          <div className="text-xs text-slate-200 font-mono">
            Price: ₹{(selectedMarker.price || 0).toFixed(2)} | Agent: {selectedMarker.agent_name || selectedMarker.agent_tag || 'Council'}
          </div>
          <div className="text-xs text-slate-400 italic">
            "{selectedMarker.reason || 'Decision recorded on chart'}"
          </div>
        </div>
      )}

      {/* Table of Decisions */}
      <div className="rounded-xl border border-[#1f293d] overflow-hidden bg-[#0f141f]">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#141b29] text-slate-400 text-[10px] uppercase border-b border-[#1f293d]">
            <tr>
              <th className="py-2.5 px-3">Time</th>
              <th className="py-2.5 px-3">Action</th>
              <th className="py-2.5 px-3">Council Conviction</th>
              <th className="py-2.5 px-3">Confidence</th>
              <th className="py-2.5 px-3">Agent 1 (Trend)</th>
              <th className="py-2.5 px-3">Agent 2 (News)</th>
              <th className="py-2.5 px-3">Agent 3 (Reversion)</th>
              <th className="py-2.5 px-3">Rationale</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#1a2333]">
            {filteredJournal.slice(0, 100).map((entry, idx) => {
              const act = entry.action || 'HOLD';
              return (
                <tr key={entry.id || idx} className="hover:bg-[#141b29]/60 transition-colors">
                  <td className="py-2 px-3 text-slate-300 font-bold whitespace-nowrap">{entry.time}</td>
                  <td className="py-2 px-3 whitespace-nowrap">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      act === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/40' :
                      act === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-500/40' : 'bg-slate-800 text-slate-400'
                    }`}>
                      {act}
                    </span>
                  </td>
                  <td className="py-2 px-3 whitespace-nowrap font-bold text-white">
                    {entry.score !== undefined ? `${entry.score > 0 ? '+' : ''}${entry.score.toFixed(2)}` : '0.00'}
                  </td>
                  <td className="py-2 px-3 whitespace-nowrap text-emerald-400 font-bold">
                    {(entry.confidence || 0).toFixed(0)}%
                  </td>
                  <td className="py-2 px-3 whitespace-nowrap text-blue-300">
                    {entry.orb_score !== undefined ? `${entry.orb_score > 0 ? '+' : ''}${entry.orb_score.toFixed(2)}` : '—'}
                  </td>
                  <td className="py-2 px-3 whitespace-nowrap text-sky-300">
                    {entry.news_score !== undefined ? `${entry.news_score > 0 ? '+' : ''}${entry.news_score.toFixed(2)}` : '—'}
                  </td>
                  <td className="py-2 px-3 whitespace-nowrap text-purple-300">
                    {entry.vwap_score !== undefined ? `${entry.vwap_score > 0 ? '+' : ''}${entry.vwap_score.toFixed(2)}` : '—'}
                  </td>
                  <td className="py-2 px-3 text-slate-400 text-[11px] font-sans truncate max-w-xs" title={entry.reason}>
                    {entry.reason}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

