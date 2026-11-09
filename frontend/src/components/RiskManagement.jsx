import React from 'react';
import { ShieldCheck, AlertOctagon, Scale, DollarSign, Activity, Percent } from 'lucide-react';

export default function RiskManagement({ state }) {
  const portfolio = state?.portfolio || {};
  const brokerCash = state?.cash || 100000;
  const equity = state?.equity || 100000;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 select-none">
      {/* Header */}
      <div className="border-b border-[#1f293d] pb-4">
        <h2 className="text-xl font-extrabold text-white tracking-wide flex items-center gap-2">
          <span>Institutional Risk Management & Guardrails</span>
          <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-[#00c896] border border-emerald-500/30">
            Enforced by Broker
          </span>
        </h2>
        <p className="text-xs text-slate-400 mt-1">
          Quantitative rules governing capital preservation, volatility-adjusted position sizing, and automated circuit breakers.
        </p>
      </div>

      {/* Grid of 4 Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs">
        {/* Card 1: Position Sizing & Stop Loss */}
        <div className="p-5 rounded-2xl bg-[#0f141f] border border-[#1f293d] space-y-3">
          <div className="flex items-center gap-2 text-sm font-bold text-white border-b border-[#1a2333] pb-2">
            <Scale className="w-4 h-4 text-[#00c896]" />
            <span>Volatility-Adaptive Position Sizing</span>
          </div>

          <div className="space-y-2 text-slate-300 font-mono text-[11px]">
            <div className="p-2.5 rounded-lg bg-[#0b0e14] border border-[#1a2333] text-slate-300">
              <span className="text-slate-500 block text-[9px] uppercase font-bold mb-0.5">FORMULA:</span>
              Size = floor((Capital × 0.5% Risk Budget) / Stop Distance)
            </div>

            <div className="flex justify-between py-1 border-b border-[#161f30]">
              <span className="text-slate-400">Fixed Risk Budget:</span>
              <span className="text-white font-bold">0.5% of Total Equity per trade</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#161f30]">
              <span className="text-slate-400">Stop Distance:</span>
              <span className="text-white font-bold">max(1.5 × ATR(14), 0.3% price)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#161f30]">
              <span className="text-slate-400">Stop Loss Guardrail Cap:</span>
              <span className="text-white font-bold">1.0% maximum risk distance</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Position Capital Exposure Cap:</span>
              <span className="text-white font-bold">50% max capital per position</span>
            </div>
          </div>
        </div>

        {/* Card 2: Profit Targets & Breakeven Trailing */}
        <div className="p-5 rounded-2xl bg-[#0f141f] border border-[#1f293d] space-y-3">
          <div className="flex items-center gap-2 text-sm font-bold text-white border-b border-[#1a2333] pb-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            <span>Target & Breakeven Execution</span>
          </div>

          <div className="space-y-2 text-slate-300 font-mono text-[11px]">
            <div className="p-2.5 rounded-lg bg-[#0b0e14] border border-[#1a2333] text-slate-300">
              <span className="text-slate-500 block text-[9px] uppercase font-bold mb-0.5">TARGET LOGIC:</span>
              Take-Profit at +1.5R. Breakeven Stop moved to Entry Price at +1.0R.
            </div>

            <div className="flex justify-between py-1 border-b border-[#161f30]">
              <span className="text-slate-400">Take-Profit Multiple:</span>
              <span className="text-emerald-400 font-bold">1.5 × Initial Stop Distance (+1.5R)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#161f30]">
              <span className="text-slate-400">Breakeven Activation:</span>
              <span className="text-sky-400 font-bold">+1.0R Unrealized Profit</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#161f30]">
              <span className="text-slate-400">Intraday Square-Off:</span>
              <span className="text-amber-400 font-bold">15:15 IST (Auto-Close Market Order)</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Cooldown Between Trades:</span>
              <span className="text-white font-bold">3 bars (15 minutes)</span>
            </div>
          </div>
        </div>

        {/* Card 3: Circuit Breakers */}
        <div className="p-5 rounded-2xl bg-[#0f141f] border border-[#1f293d] space-y-3">
          <div className="flex items-center gap-2 text-sm font-bold text-white border-b border-[#1a2333] pb-2">
            <AlertOctagon className="w-4 h-4 text-rose-400" />
            <span>Emergency Circuit Breakers</span>
          </div>

          <div className="space-y-2 text-slate-300 font-mono text-[11px]">
            <div className="flex justify-between py-1 border-b border-[#161f30]">
              <span className="text-slate-400">Daily Max Loss Limit:</span>
              <span className="text-rose-400 font-bold">-2.0% of Starting Capital (₹2,000)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#161f30]">
              <span className="text-slate-400">Max Trades per Session:</span>
              <span className="text-white font-bold">6 trades per day</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#161f30]">
              <span className="text-slate-400">Circuit Breaker Action:</span>
              <span className="text-rose-400 font-bold">Hard Halt: No further entries allowed</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">Kill Switch Modes:</span>
              <span className="text-white font-bold">Stop New Trades OR Emergency Flatten</span>
            </div>
          </div>
        </div>

        {/* Card 4: Fee & Regulatory Accounting */}
        <div className="p-5 rounded-2xl bg-[#0f141f] border border-[#1f293d] space-y-3">
          <div className="flex items-center gap-2 text-sm font-bold text-white border-b border-[#1a2333] pb-2">
            <DollarSign className="w-4 h-4 text-amber-400" />
            <span>NSE Brokerage & Tax Model</span>
          </div>

          <div className="space-y-2 text-slate-300 font-mono text-[11px]">
            <div className="flex justify-between py-1 border-b border-[#161f30]">
              <span className="text-slate-400">Brokerage:</span>
              <span className="text-white font-bold">0.03% (capped at ₹20 per executed order)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#161f30]">
              <span className="text-slate-400">Securities Transaction Tax (STT):</span>
              <span className="text-white font-bold">0.025% on sell turnover</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#161f30]">
              <span className="text-slate-400">Exchange Transaction Charges:</span>
              <span className="text-white font-bold">0.003% of turnover</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-400">GST (18%):</span>
              <span className="text-white font-bold">18% on (Brokerage + Exchange Charges)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

