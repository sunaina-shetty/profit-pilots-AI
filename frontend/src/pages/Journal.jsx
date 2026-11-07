import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

export default function Journal() {
  const [entries, setEntries] = useState([]);
  const [filterSymbol, setFilterSymbol] = useState('');
  const [filterAction, setFilterAction] = useState('ALL');
  const [expandedId, setExpandedId] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadEntries();
  }, [filterSymbol]);

  const loadEntries = async () => {
    setLoading(true);
    try {
      const res = await api.getJournalEntries(50, filterSymbol);
      setEntries(res.data.entries || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const filteredEntries = entries.filter((e) => {
    if (filterAction === 'ALL') return true;
    const action = e.decision?.action || 'HOLD';
    return action === filterAction;
  });

  return (
    <div className="space-y-6">
      {/* Header & Filter Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span>📜</span> PLAIN-LANGUAGE DECISION AUDIT JOURNAL
          </h2>
          <p className="text-xs text-slate-400">
            Every decision, order, hold, and risk rejection is recorded with full auditability
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Symbol Filter */}
          <select
            value={filterSymbol}
            onChange={(e) => setFilterSymbol(e.target.value)}
            className="bg-[#1e293b] border border-[#334155] rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
          >
            <option value="">All Symbols</option>
            <option value="RELIANCE.NS">RELIANCE.NS</option>
            <option value="TCS.NS">TCS.NS</option>
            <option value="INFY.NS">INFY.NS</option>
            <option value="AAPL">AAPL</option>
            <option value="MSFT">MSFT</option>
            <option value="TSLA">TSLA</option>
          </select>

          {/* Action Filter */}
          <select
            value={filterAction}
            onChange={(e) => setFilterAction(e.target.value)}
            className="bg-[#1e293b] border border-[#334155] rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none"
          >
            <option value="ALL">All Actions</option>
            <option value="BUY">BUY Orders</option>
            <option value="SELL">SELL / Exits</option>
            <option value="HOLD">HOLD Decisions</option>
          </select>

          <button
            onClick={loadEntries}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-300"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* Entries Timeline List */}
      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-12 text-slate-500 text-sm">Loading audit journal...</div>
        ) : filteredEntries.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-sm cockpit-card p-6">
            No journal entries matching selected filters.
          </div>
        ) : (
          filteredEntries.map((entry, index) => {
            const id = entry._id || index;
            const action = entry.decision?.action || 'HOLD';
            const risk = entry.risk_verdict || {};
            const isExpanded = expandedId === id;

            return (
              <div
                key={id}
                className="cockpit-card p-4 transition border border-[#1f293d] hover:border-slate-600"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <span className={`px-2.5 py-0.5 rounded text-xs font-bold ${
                      action === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-600' :
                      action === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-600' :
                      'bg-slate-800 text-slate-300'
                    }`}>
                      {action}
                    </span>
                    <span className="font-mono text-cyan-300 font-bold text-xs">{entry.symbol}</span>
                    <span className="font-mono text-slate-400 text-xs">₹{entry.price?.toFixed(2)}</span>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-[11px] text-slate-400 font-mono">
                      {new Date(entry.timestamp * 1000).toLocaleString()}
                    </span>
                    <button
                      onClick={() => setExpandedId(isExpanded ? null : id)}
                      className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold px-2 py-1 rounded bg-slate-800"
                    >
                      {isExpanded ? 'Hide Details ▲' : 'Why? Expand ▼'}
                    </button>
                  </div>
                </div>

                {/* Plain-Language Narrative Summary */}
                <p className="mt-2 text-xs text-slate-200 leading-relaxed font-sans">
                  {entry.plain_text}
                </p>

                {/* Expandable "Why?" Breakdown */}
                {isExpanded && (
                  <div className="mt-4 pt-3 border-t border-slate-800 space-y-3 bg-[#0b0f19] p-3 rounded-lg text-xs">
                    <div className="font-bold text-cyan-300 uppercase tracking-wider text-[11px]">
                      🔍 Explainability & Audit Trail
                    </div>

                    {/* Agent Votes Breakdown */}
                    {entry.decision?.agent_votes && (
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                        {Object.entries(entry.decision.agent_votes).map(([agentKey, val]) => (
                          <div key={agentKey} className="bg-[#111827] p-2.5 rounded border border-slate-800">
                            <div className="flex justify-between items-center capitalize font-semibold text-slate-300 mb-1">
                              <span>{agentKey}</span>
                              <span className="font-mono text-cyan-400">{val.vote}</span>
                            </div>
                            <div className="text-[10px] text-slate-400">
                              Confidence: {Math.round((val.confidence || 0) * 100)}%
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Risk Manager Verdict Details */}
                    <div className="bg-[#111827] p-2.5 rounded border border-slate-800 flex justify-between items-center">
                      <div>
                        <span className="text-slate-400 text-[11px]">Risk Manager Verdict:</span>
                        <span className={`ml-2 font-bold ${risk.approved ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {risk.approved ? 'APPROVED' : 'VETOED'}
                        </span>
                        <p className="text-[11px] text-slate-300 mt-0.5">{risk.reason}</p>
                      </div>
                      {risk.qty > 0 && (
                        <div className="text-right font-mono text-xs">
                          <div>Sized: <span className="text-white font-bold">{risk.qty} shares</span></div>
                          <div className="text-rose-400">SL: ₹{risk.stop_loss}</div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}

