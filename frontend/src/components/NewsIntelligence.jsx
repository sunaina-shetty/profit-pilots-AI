import React from 'react';
import { Newspaper, ShieldAlert, CheckCircle, AlertTriangle, Clock, ExternalLink } from 'lucide-react';

export default function NewsIntelligence({ state, useMoneycontrol = true, onToggleMoneycontrol }) {
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
            <span>{useMoneycontrol ? 'Agent 2 — Moneycontrol News Intelligence' : 'Agent 2 — News Intelligence (Previous RSS Logic)'}</span>
            <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold border ${getClassificationBadge(classification)}`}>
              {useMoneycontrol && (news.signal === 'BUY' || news.status === 'YES') ? 'YES (APPROVED)' : news.signal || classification}
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            {useMoneycontrol
              ? 'Live Moneycontrol headline ingestion with Default YES status; triggers immediate HOLD or emergency SELL upon sudden adverse news shocks.'
              : 'Legacy Google News RSS headline ingestion with standard sentiment scoring, neutral baseline, and risk thresholds.'}
          </p>
        </div>

        {/* Controls: Moneycontrol Switch & Veto Status Pill */}
        <div className="flex items-center gap-3 flex-wrap">
          {/* Engine Switch Button */}
          {onToggleMoneycontrol && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#141b29] border border-[#1f293d]">
              <span className="text-[11px] font-bold text-slate-300">News Logic:</span>
              <button
                type="button"
                onClick={onToggleMoneycontrol}
                className={`px-2.5 py-1 rounded text-xs font-bold transition-all border ${
                  useMoneycontrol
                    ? 'bg-emerald-950 text-emerald-300 border-emerald-500 shadow-sm shadow-emerald-950'
                    : 'bg-slate-800 text-slate-300 border-slate-700 hover:text-white'
                }`}
                title="Toggle between Moneycontrolpy (Default YES) and Previous News Logic (Standard RSS)"
              >
                {useMoneycontrol ? '🟢 Moneycontrol: ON' : '⚪ Previous Logic: ON'}
              </button>
            </div>
          )}

          {/* Veto Status Pill */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-bold ${
            news.signal === 'SELL'
              ? 'bg-red-950 border-red-500 text-red-300 animate-pulse'
              : news.signal === 'HOLD' || vetoActive
              ? 'bg-amber-950/80 border-amber-500/50 text-amber-300'
              : 'bg-emerald-950/80 border-emerald-500/50 text-emerald-300'
          }`}>
            {news.signal === 'SELL' ? (
              <>
                <ShieldAlert className="w-4 h-4 text-rose-400" />
                <span>SUDDEN SHOCK DETECTED — EMERGENCY SELL</span>
              </>
            ) : news.signal === 'HOLD' || vetoActive ? (
              <>
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <span>VETO ACTIVE — HOLDING / ENTRIES BLOCKED</span>
              </>
            ) : (
              <>
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                <span>{useMoneycontrol ? 'DEFAULT STATUS: YES (CLEAR TO TRADE)' : 'NO VETO ACTIVE (CLEAR TO TRADE)'}</span>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Summary Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4 font-mono text-xs">
        <div className="p-4 rounded-xl bg-[#0f141f] border border-[#1f293d]">
          <span className="text-slate-400 text-[10px] block mb-1">CURRENT VERDICT</span>
          <span className={`text-xl font-extrabold ${
            news.signal === 'BUY' || (useMoneycontrol && news.status === 'YES')
              ? 'text-emerald-400'
              : news.signal === 'SELL'
              ? 'text-rose-400'
              : 'text-amber-400'
          }`}>
            {useMoneycontrol
              ? (news.signal === 'BUY' || news.status === 'YES' ? 'YES (BUY)' : news.signal === 'SELL' ? 'SELL (SHOCK)' : 'HOLD')
              : (news.signal || classification)}
          </span>
          <span className="text-[10px] text-slate-500 block mt-1">
            {useMoneycontrol ? 'Default YES mode active' : 'Standard Neutral Baseline'}
          </span>
        </div>

        <div className="p-4 rounded-xl bg-[#0f141f] border border-[#1f293d]">
          <span className="text-slate-400 text-[10px] block mb-1">NET SENTIMENT SCORE</span>
          <span className={`text-xl font-extrabold ${netSentiment >= 0.2 ? 'text-emerald-400' : netSentiment <= -0.2 ? 'text-rose-400' : 'text-slate-200'}`}>
            {netSentiment > 0 ? '+' : ''}{netSentiment.toFixed(2)}
          </span>
          <span className="text-[10px] text-slate-500 block mt-1">Scale: -1.00 (Adverse) to +1.00 (Bullish)</span>
        </div>

        <div className="p-4 rounded-xl bg-[#0f141f] border border-[#1f293d]">
          <span className="text-slate-400 text-[10px] block mb-1">DATA FEED</span>
          <span className="text-base font-extrabold text-sky-400">
            {useMoneycontrol ? 'Moneycontrol' : 'Google News RSS'}
          </span>
          <span className="text-[10px] text-slate-500 block mt-1">
            {useMoneycontrol ? 'Live Feed & RSS Wires' : 'Financial News Wire Feed'}
          </span>
        </div>

        <div className="p-4 rounded-xl bg-[#0f141f] border border-[#1f293d]">
          <span className="text-slate-400 text-[10px] block mb-1">SHOCK THRESHOLD</span>
          <span className="text-xl font-extrabold text-rose-400">
            -0.65
          </span>
          <span className="text-[10px] text-slate-500 block mt-1">Sudden crash/fraud news triggers instant SELL</span>
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

