import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

const RISK_RULES_CHECKLIST = [
  { id: 1, name: "Kill Switch Hardware Lock", desc: "Instantly blocks all orders if state is ON; zero AI dependencies" },
  { id: 2, name: "System State Check", desc: "Blocks execution if system state is HALTED or KILLED" },
  { id: 3, name: "Price Feed Freshness Gate", desc: "Flags NO_TRADE if tick age exceeds 60 seconds" },
  { id: 4, name: "News Staleness Gate", desc: "Flags NO_TRADE if headlines are older than 300 seconds" },
  { id: 5, name: "Daily Loss Limit Ceiling", desc: "Halts trading once daily realized+unrealized drawdown reaches 2% SOD equity" },
  { id: 6, name: "Mandatory Stop-Loss Guard", desc: "Every order must provide an explicit non-zero stop loss" },
  { id: 7, name: "Stop-Loss Logical Orientation", desc: "SL must be strictly below entry for BUY, strictly above for SELL" },
  { id: 8, name: "Stop-Loss Distance Bounds", desc: "Distance must be between 0.1% and 10.0% of entry price" },
  { id: 9, name: "Max Open Positions Cap", desc: "Strict portfolio limit: maximum 3 open positions simultaneously" },
  { id: 10, name: "Liquid Cash Availability", desc: "Total trade value including fees must not exceed available cash balance" },
  { id: 11, name: "Single Position Exposure Ceiling", desc: "No single position may exceed 30% of total portfolio equity" },
  { id: 12, name: "1% Risk-Based Position Sizing", desc: "Quantity calculated strictly as: (1% of Equity) / (Entry - StopLoss)" },
  { id: 13, name: "Valid Instrument & Direction", desc: "Symbol must be in approved universe and action must be BUY/SELL" },
  { id: 14, name: "Minimum Viable Sizing", desc: "Quantity must resolve to at least 1 whole share" },
  { id: 15, name: "Consensus Size Tier Multiplier", desc: "FULL tier = 100% allowed risk; HALF tier = 50% allowed risk" },
  { id: 16, name: "Cryptographic HMAC Approval Token", desc: "Issues SHA256-signed token required by mock exchange to execute" }
];

export default function RiskManager() {
  const [limits, setLimits] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLimits();
    const interval = setInterval(loadLimits, 4000);
    return () => clearInterval(interval);
  }, []);

  const loadLimits = async () => {
    try {
      const res = await api.getLimits();
      setLimits(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleResetLimit = async () => {
    try {
      await api.resetAll();
      loadLimits();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <span>🛡️</span> INDEPENDENT RISK GUARDIAN
          </h2>
          <p className="text-xs text-slate-400">
            Rules-only engine • Zero AI/LLM imports • Final veto power over execution
          </p>
        </div>

        <button
          onClick={handleResetLimit}
          className="px-3.5 py-1.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 border border-cyan-700 text-cyan-300 text-xs font-bold"
        >
          Reset SOD Equity & Limits
        </button>
      </div>

      {/* Metrics Summary Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="cockpit-card p-4">
          <div className="text-[11px] text-slate-400 uppercase">Risk Per Trade</div>
          <div className="text-2xl font-bold font-mono text-cyan-400 mt-1">1.0%</div>
          <div className="text-[10px] text-slate-500 mt-0.5">Exact position quantity formula</div>
        </div>

        <div className="cockpit-card p-4">
          <div className="text-[11px] text-slate-400 uppercase">Daily Loss Ceiling</div>
          <div className="text-2xl font-bold font-mono text-amber-400 mt-1">
            2.0% <span className="text-xs text-slate-400">(₹{limits?.daily_loss_limit_amount || 2000})</span>
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Current used: {limits?.loss_used_pct || 0}%</div>
        </div>

        <div className="cockpit-card p-4">
          <div className="text-[11px] text-slate-400 uppercase">Max Positions</div>
          <div className="text-2xl font-bold font-mono text-white mt-1">
            {limits?.open_positions_count || 0} / {limits?.max_open_positions || 3}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Strict concentration guard</div>
        </div>

        <div className="cockpit-card p-4">
          <div className="text-[11px] text-slate-400 uppercase">Kill Switch State</div>
          <div className={`text-2xl font-bold font-mono mt-1 ${
            limits?.kill_switch === 'ON' ? 'text-red-400' : 'text-emerald-400'
          }`}>
            {limits?.kill_switch === 'ON' ? 'ENGAGED' : 'ARMED (OFF)'}
          </div>
          <div className="text-[10px] text-slate-500 mt-0.5">Hardware circuit state in SQL</div>
        </div>
      </div>

      {/* 16 Deterministic Rules Checklist */}
      <div className="cockpit-card p-5">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
          <div>
            <h3 className="text-sm font-bold text-slate-200">
              16 DETERMINISTIC SAFETY RULES (NON-NEGOTIABLE GUARDRAILS)
            </h3>
            <p className="text-[11px] text-slate-400">
              Every proposed order is checked against all 16 rules sequentially. Any single failure triggers an immediate veto.
            </p>
          </div>
          <span className="badge-bull">16/16 ACTIVE</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {RISK_RULES_CHECKLIST.map((rule) => (
            <div
              key={rule.id}
              className="p-3 rounded-lg bg-[#0f172a] border border-[#1e293b] flex items-start gap-3"
            >
              <div className="w-5 h-5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-700/60 flex items-center justify-center text-xs font-bold mt-0.5 shrink-0">
                ✓
              </div>
              <div>
                <div className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                  <span className="text-slate-500 font-mono text-[10px]">#{rule.id}</span>
                  {rule.name}
                </div>
                <div className="text-[11px] text-slate-400 mt-0.5">
                  {rule.desc}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Cryptographic Token Protocol Explanation */}
      <div className="cockpit-card p-5">
        <div className="text-sm font-bold text-slate-200 mb-2 flex items-center gap-2">
          <span>🔐</span> ZERO-TRUST APPROVAL TOKEN PROTOCOL
        </div>
        <p className="text-xs text-slate-300 leading-relaxed mb-3">
          To prevent AI hallucinations, prompt injections, or unauthorized API orders from reaching the exchange, the exchange strictly rejects any order without a cryptographic HMAC-SHA256 signature signed by this Risk Service. The token embeds the exact symbol, side, quantity, and stop-loss with an expiration timestamp.
        </p>
        <div className="bg-[#0b0f19] p-3 rounded font-mono text-[11px] text-cyan-400 border border-slate-800 overflow-x-auto">
          HMAC_SHA256(secret, symbol + side + qty + stop_loss + nonce) ➔ Signed Token ➔ Verified by Exchange
        </div>
      </div>
    </div>
  );
}

