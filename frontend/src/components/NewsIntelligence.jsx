import React from 'react';
import { Newspaper, ShieldAlert, CheckCircle, AlertTriangle, Clock, ExternalLink } from 'lucide-react';

export default function NewsIntelligence({ state }) {
  const news = state?.latest_agents?.news || {};
  const headlines = news.headlines || [];
  const classification = news.classification || 'NEUTRAL';
  const netSentiment = news.facts?.net_sentiment || 0.0;
  const vetoActive = news.veto_buy || news.veto_short;

  const getClassificationBadge = (cls) => {
    switch (cls) {
      case 'POSITIVE':
        return 'bg-emerald-950/80 text-emerald-400 border-emerald-500/40';
      case 'NEGATIVE':
        return 'bg-rose-950/80 text-rose-400 border-rose-500/40';
      case 'HIGH VOLATILITY':
        return 'bg-amber-950/80 text-amber-400 border-amber-500/40';
      case 'CRITICAL EVENT':
        return 'bg-red-950 text-red-400 border-red-500 animate-pulse';
      case 'INSUFFICIENT DATA':
        return 'bg-slate-800 text-slate-400 border-slate-700';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 select-none">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#1f293d] pb-4">
        <div>
          <h2 className="text-xl font-extrabold text-white tracking-wide flex items-center gap-2">
            <span>Agent 2 — News Intelligence & Event Risk</span>
            <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${getClassificationBadge(classification)}`}>
              {classification}
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Real-time financial headline ingestion, sentiment scoring, and critical tail-risk veto protection.
          </p>
        </div>

        {/* Veto Status Pill */}
        <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-bold ${
          vetoActive
            ? 'bg-rose-950/80 border-rose-500/50 text-rose-300 animate-pulse'
            : 'bg-emerald-950/80 border-emerald-500/50 text-emerald-300'
        }`}>
          {vetoActive ? <ShieldAlert className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
          <span>{vetoActive ? 'COUNCIL VETO ACTIVE (ENTRIES BLOCKED)' : 'NO VETO ACTIVE (CLEAR TO TRADE)'}</span>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
        <div className="p-4 rounded-xl bg-[#0f141f] border border-[#1f293d]">
          <span className="text-slate-400 text-[10px] block mb-1">NET SENTIMENT SCORE</span>
          <span className={`text-xl font-extrabold ${netSentiment >= 0.2 ? 'text-emerald-400' : netSentiment <= -0.2 ? 'text-rose-400' : 'text-slate-200'}`}>
            {netSentiment > 0 ? '+' : ''}{netSentiment.toFixed(2)}
          </span>
          <span className="text-[10px] text-slate-500 block mt-1">Scale: -1.00 (Extremely Bearish) to +1.00 (Extremely Bullish)</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0f141f] border border-[#1f293d]">
          <span className="text-slate-400 text-[10px] block mb-1">HEADLINES ANALYZED</span>
          <span className="text-xl font-extrabold text-white">
            {news.facts?.headlines_count || headlines.length}
          </span>
          <span className="text-[10px] text-slate-500 block mt-1">Ingested from Google News RSS</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0f141f] border border-[#1f293d]">
          <span className="text-slate-400 text-[10px] block mb-1">VETO THRESHOLD</span>
          <span className="text-xl font-extrabold text-rose-400">
            -0.50
          </span>
          <span className="text-[10px] text-slate-500 block mt-1">Any score below -0.50 vetoes long orders</span>
        </div>
      </div>

      {/* Headlines Stream */}
      <div className="space-y-3">
        <h3 className="font-bold text-white text-sm">Real-Time Ingested Headlines</h3>

        {headlines.length > 0 ? (
          <div className="space-y-2">
            {headlines.map((item, idx) => (
              <div
                key={idx}
                className="p-3.5 rounded-xl bg-[#0f141f] border border-[#1f293d] hover:border-slate-700 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
              >
                <div className="space-y-1">
                  <div className="font-semibold text-slate-200 text-sm leading-snug">
                    {item.title}
                  </div>
                  <div className="flex items-center gap-3 text-[11px] text-slate-400 font-mono">
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {item.time_str || '09:00'} IST
                    </span>
                    <span>Age: {item.age_minutes}m ago</span>
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getClassificationBadge(item.classification)}`}>
                    {item.classification}
                  </span>
                  <span className={`font-mono font-bold text-xs ${item.sentiment >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {item.sentiment > 0 ? '+' : ''}{item.sentiment.toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-12 text-center text-slate-500 rounded-xl bg-[#0f141f] border border-[#1f293d] space-y-2">
            <Newspaper className="w-8 h-8 mx-auto text-slate-600 opacity-50" />
            <div className="font-bold text-slate-300">No Fresh News Published Prior to Current Candle</div>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              Agent 2 operates in "INSUFFICIENT DATA" mode with 0.00 sentiment. No artificial fake headlines are ever fabricated.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

