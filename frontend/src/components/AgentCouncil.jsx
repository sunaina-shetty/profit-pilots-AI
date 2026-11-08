import React from 'react';

export default function AgentCouncil({ agents = {}, decision = {} }) {
  const trend = agents.trend || { vote: 'HOLD', confidence: 0.5, reasons: ['Waiting for price stream...'] };
  const news = agents.news || { vote: 'HOLD', confidence: 0.5, reasons: ['Scanning news headlines...'] };
  const contrarian = agents.contrarian || { vote: 'HOLD', confidence: 0.5, reasons: ['Checking RSI ranges...'] };

  const getVoteBadge = (vote) => {
    if (vote === 'BUY') return <span className="badge-bull">BUY</span>;
    if (vote === 'SELL') return <span className="badge-bear">SELL</span>;
    return <span className="badge-neutral">HOLD</span>;
  };

  const renderCard = (title, icon, agent) => (
    <div className="bg-[#1e293b]/50 border border-[#334155] rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 font-semibold text-slate-200 text-xs">
          <span>{icon}</span> {title}
        </div>
        {getVoteBadge(agent.vote)}
      </div>

      {/* Confidence Bar */}
      <div>
        <div className="flex justify-between text-[10px] text-slate-400 mb-0.5">
          <span>Confidence</span>
          <span className="font-mono text-cyan-400">{Math.round((agent.confidence || 0) * 100)}%</span>
        </div>
        <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${agent.vote === 'BUY' ? 'bg-emerald-500' :
              agent.vote === 'SELL' ? 'bg-rose-500' : 'bg-cyan-500'
              }`}
            style={{ width: `${Math.round((agent.confidence || 0) * 100)}%` }}
          />
        </div>
      </div>

      {/* Key Reason */}
      <div className="text-[11px] text-slate-400 space-y-0.5 max-h-16 overflow-y-auto">
        {(agent.reasons || []).slice(0, 2).map((r, i) => (
          <div key={i} className="truncate">• {r}</div>
        ))}
      </div>
    </div>
  );

  return (
    <div className="space-y-3">
      {/* The 3 Independent Council Agents */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
        {renderCard('Trend Agent', '📈', trend)}
        {renderCard('News Sentiment', '📰', news)}
        {renderCard('Contrarian Agent', '🛡️', contrarian)}
      </div>

      {/* Consensus Decision Agent Panel */}
      <div className="bg-[#0f172a] border border-cyan-800/60 rounded-lg p-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">⚖️</span>
          <div>
            <div className="text-xs font-bold uppercase tracking-wider text-cyan-300">
              Council Consensus Decision
            </div>
            <div className="text-[11px] text-slate-400 leading-tight">
              {decision.reason || 'Aggregating independent agents into unified risk-weighted verdict...'}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="text-[10px] text-slate-400">SIZE TIER</div>
            <div className="font-mono font-bold text-xs text-amber-300">
              {decision.size_tier || 'ZERO'}
            </div>
          </div>

          <div className="text-right">
            <div className="text-[10px] text-slate-400">ACTION</div>
            <div className="text-sm font-bold">
              {getVoteBadge(decision.action || 'HOLD')}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

