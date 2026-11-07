import React, { useState } from 'react';
import { api } from '../services/api';

export default function DemoDrawer({ isOpen, onClose, symbol = 'RELIANCE.NS', onEventNotify }) {
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const trigger = async (label, actionFn) => {
    setLoading(true);
    try {
      await actionFn();
      if (onEventNotify) onEventNotify(`Triggered: ${label}`);
    } catch (err) {
      console.error(err);
      if (onEventNotify) onEventNotify(`Failed: ${label}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-80 bg-[#0f172a] border-l border-[#1e293b] p-5 shadow-2xl flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <div className="flex items-center gap-2">
            <span className="text-xl">🧪</span>
            <div>
              <h3 className="font-bold text-sm text-cyan-400">JUDGE DEMO CONTROLS</h3>
              <p className="text-[10px] text-slate-400">Live Guardrail Adversarial Injection</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white text-lg font-bold p-1"
          >
            ✕
          </button>
        </div>

        <p className="text-xs text-slate-300 mb-4 leading-relaxed">
          Inject real-time stresses and adversarial anomalies into the pipeline to inspect how guardrails respond on screen:
        </p>

        <div className="space-y-3">
          {/* 1. Flash Crash */}
          <button
            disabled={loading}
            onClick={() => trigger('Flash Crash (-8%)', () => api.injectShock(symbol, 'flash_crash', { pct: 0.08 }))}
            className="w-full text-left p-3 rounded-lg bg-red-950/40 hover:bg-red-900/50 border border-red-700/60 text-xs transition"
          >
            <div className="font-bold text-red-300 flex items-center justify-between">
              <span>⚡ Flash Crash (-8%)</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-900 text-red-200">Price Shock</span>
            </div>
            <div className="text-[10px] text-slate-400 mt-1">
              Triggers sudden gap down. Verifies stop-loss exit without panic buying.
            </div>
          </button>

          {/* 2. Price Spike */}
          <button
            disabled={loading}
            onClick={() => trigger('Price Spike (+6%)', () => api.injectShock(symbol, 'spike', { pct: 0.06 }))}
            className="w-full text-left p-3 rounded-lg bg-emerald-950/40 hover:bg-emerald-900/50 border border-emerald-700/60 text-xs transition"
          >
            <div className="font-bold text-emerald-300 flex items-center justify-between">
              <span>🚀 Parabolic Spike (+6%)</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-900 text-emerald-200">FOMO Trap</span>
            </div>
            <div className="text-[10px] text-slate-400 mt-1">
              Sudden vertical pump. Contrarian agent warns over-extension.
            </div>
          </button>

          {/* 3. Stale Price Feed */}
          <button
            disabled={loading}
            onClick={() => trigger('Stale Price Feed', () => api.injectShock(symbol, 'stale', { delay_seconds: 90 }))}
            className="w-full text-left p-3 rounded-lg bg-purple-950/40 hover:bg-purple-900/50 border border-purple-700/60 text-xs transition"
          >
            <div className="font-bold text-purple-300 flex items-center justify-between">
              <span>⏳ Inject Stale Feed</span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-900 text-purple-200">Reliability</span>
            </div>
            <div className="text-[10px] text-slate-400 mt-1">
              Sets price age &gt; 60s. Enforces NO_TRADE guardrail veto.
            </div>
          </button>

          {/* 4. Clear Shocks */}
          <button
            disabled={loading}
            onClick={() => trigger('Clear Shocks', () => api.injectShock(symbol, 'clear'))}
            className="w-full text-left p-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-300 transition"
          >
            <div className="font-semibold text-slate-200">🔄 Clear Injected Shocks</div>
            <div className="text-[10px] text-slate-400">Restore normal simulated price drift.</div>
          </button>
        </div>
      </div>

      {/* Reset Portfolio */}
      <div className="pt-4 border-t border-slate-800">
        <button
          disabled={loading}
          onClick={() => trigger('Reset Portfolio to ₹100,000', () => api.resetAll())}
          className="w-full py-2.5 rounded-lg bg-cyan-950 hover:bg-cyan-900 border border-cyan-700 text-cyan-300 font-bold text-xs"
        >
          🧹 Reset Portfolio to ₹1,00,000 Cash
        </button>
      </div>
    </div>
  );
}

