import React, { useState, useEffect } from 'react';
import { Sliders, Save, RotateCcw, Shield, Newspaper, TrendingUp, Zap, HelpCircle } from 'lucide-react';

export default function AgentConfigPanel({ onConfigUpdated }) {
  const [config, setConfig] = useState(null);
  const [strategies, setStrategies] = useState([]);
  const [isSaving, setIsSaving] = useState(false);
  const [statusMsg, setStatusMsg] = useState({ type: '', text: '' });

  const loadData = async () => {
    try {
      const [resCfg, resStrats] = await Promise.all([
        fetch('/api/agent-config').then((r) => r.json()),
        fetch('/api/strategies').then((r) => r.json())
      ]);
      setConfig(resCfg);
      if (resStrats.strategies) setStrategies(resStrats.strategies);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSave = async () => {
    if (!config) return;
    setIsSaving(true);
    setStatusMsg({ type: '', text: '' });
    try {
      const res = await fetch('/api/agent-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      const data = await res.json();
      if (res.ok) {
        setConfig(data.config);
        setStatusMsg({ type: 'success', text: 'Configuration saved and active for subsequent candles.' });
        if (onConfigUpdated) onConfigUpdated(data.config);
      } else {
        setStatusMsg({ type: 'error', text: data.error || 'Failed to save configuration.' });
      }
    } catch (e) {
      setStatusMsg({ type: 'error', text: String(e) });
    } finally {
      setIsSaving(false);
      setTimeout(() => setStatusMsg({ type: '', text: '' }), 4000);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset all agent and strategy configurations to factory defaults?')) return;
    try {
      const res = await fetch('/api/agent-config/reset', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        setConfig(data.config);
        setStatusMsg({ type: 'success', text: 'Configuration reset to default settings.' });
        if (onConfigUpdated) onConfigUpdated(data.config);
      }
    } catch (e) {
      setStatusMsg({ type: 'error', text: String(e) });
    }
  };

  if (!config) {
    return <div className="p-8 text-center text-slate-500 text-xs">Loading Agent Configuration...</div>;
  }

  const agent1 = config.agent1 || {};
  const agent2 = config.agent2 || {};
  const agent3 = config.agent3 || {};
  const council = config.council || {};
  const risk = config.risk || {};

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6 select-none">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#1f293d] pb-4">
        <div>
          <h2 className="text-xl font-extrabold text-white tracking-wide flex items-center gap-2">
            <span>Multi-Agent System Configuration</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
              Live Modifiable
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Independently assign technical strategies, risk boundaries, news sentiment sensitivity, and council weights.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {statusMsg.text && (
            <span className={`text-xs px-3 py-1 rounded-lg font-semibold ${
              statusMsg.type === 'success' ? 'bg-emerald-950 text-emerald-300 border border-emerald-500/40' : 'bg-rose-950 text-rose-300 border border-rose-500/40'
            }`}>
              {statusMsg.text}
            </span>
          )}

          <button
            onClick={handleReset}
            className="px-3 py-1.5 rounded-lg bg-[#1a2333] hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Defaults</span>
          </button>

          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-1.5 rounded-lg bg-[#00c896] hover:bg-emerald-400 text-black text-xs font-bold flex items-center gap-1.5 shadow-lg shadow-emerald-950/40 transition-colors"
          >
            <Save className="w-3.5 h-3.5" />
            <span>{isSaving ? 'Saving...' : 'Save Configuration'}</span>
          </button>
        </div>
      </div>

      {/* Grid of 4 Main Cards: Agent 1, Agent 2, Agent 3, Council & Risk */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1: Agent 1 (Trend / Breakout) */}
        <div className="p-5 rounded-2xl bg-[#0f141f] border border-[#1f293d] space-y-4">
          <div className="flex items-center justify-between border-b border-[#1a2333] pb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-xs">
                A1
              </div>
              <div>
                <h3 className="font-bold text-white text-sm">Agent 1 — Trend & Breakout</h3>
                <span className="text-[10px] text-slate-400">Generates directional trend and breakout signals</span>
              </div>
            </div>
            <label className="flex items-center gap-1.5 text-xs text-slate-300 font-semibold cursor-pointer">
              <input
                type="checkbox"
                checked={agent1.enabled}
                onChange={(e) => setConfig({
                  ...config,
                  agent1: { ...agent1, enabled: e.target.checked }
                })}
                className="w-4 h-4 rounded text-[#00c896] bg-slate-900 border-slate-700"
              />
              <span>Enabled</span>
            </label>
          </div>

          <div className="space-y-3 text-xs">
            {/* Strategy Select */}
            <div>
              <label className="block text-slate-400 font-medium mb-1">Active Quantitative Strategy:</label>
              <select
                value={agent1.strategy_id}
                onChange={(e) => setConfig({
                  ...config,
                  agent1: { ...agent1, strategy_id: e.target.value }
                })}
                className="w-full bg-[#121926] text-white font-bold rounded-lg px-3 py-2 border border-[#1f293d] focus:outline-none focus:border-[#00c896]"
              >
                {strategies.map((st) => (
                  <option key={st.id} value={st.id}>
                    {st.name} ({st.category})
                  </option>
                ))}
              </select>
            </div>

            {/* Weight Slider */}
            <div>
              <div className="flex justify-between text-slate-400 font-medium mb-1">
                <span>Council Weight:</span>
                <span className="font-bold text-blue-400 font-mono">{(agent1.weight * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={agent1.weight}
                onChange={(e) => setConfig({
                  ...config,
                  agent1: { ...agent1, weight: parseFloat(e.target.value) }
                })}
                className="w-full accent-blue-500"
              />
            </div>
          </div>
        </div>

        {/* Card 2: Agent 2 (News Intelligence) */}
        <div className="p-5 rounded-2xl bg-[#0f141f] border border-[#1f293d] space-y-4">
          <div className="flex items-center justify-between border-b border-[#1a2333] pb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-sky-500/20 text-sky-400 flex items-center justify-center font-bold text-xs">
                A2
              </div>
              <div>
                <h3 className="font-bold text-white text-sm">Agent 2 — News Intelligence</h3>
                <span className="text-[10px] text-slate-400">Scans live headlines, sentiment & event risk</span>
              </div>
            </div>
            <label className="flex items-center gap-1.5 text-xs text-slate-300 font-semibold cursor-pointer">
              <input
                type="checkbox"
                checked={agent2.enabled}
                onChange={(e) => setConfig({
                  ...config,
                  agent2: { ...agent2, enabled: e.target.checked }
                })}
                className="w-4 h-4 rounded text-[#00c896] bg-slate-900 border-slate-700"
              />
              <span>Enabled</span>
            </label>
          </div>

          <div className="space-y-3 text-xs">
            {/* Negative Veto Threshold */}
            <div>
              <div className="flex justify-between text-slate-400 font-medium mb-1">
                <span>Negative Veto Threshold (Blocks Long Entries):</span>
                <span className="font-bold text-rose-400 font-mono">{agent2.negative_veto_threshold}</span>
              </div>
              <input
                type="range"
                min="-1.0"
                max="-0.1"
                step="0.05"
                value={agent2.negative_veto_threshold}
                onChange={(e) => setConfig({
                  ...config,
                  agent2: { ...agent2, negative_veto_threshold: parseFloat(e.target.value) }
                })}
                className="w-full accent-rose-500"
              />
            </div>

            {/* Critical Event Checkbox */}
            <div className="flex items-center justify-between p-2 rounded-lg bg-[#141b29] border border-[#1f293d]">
              <span className="text-slate-300">Veto on Critical Events (Fraud, Probe, SEBI Raid):</span>
              <input
                type="checkbox"
                checked={agent2.veto_on_critical_event ?? true}
                onChange={(e) => setConfig({
                  ...config,
                  agent2: { ...agent2, veto_on_critical_event: e.target.checked }
                })}
                className="w-4 h-4 rounded text-[#00c896] bg-slate-900"
              />
            </div>

            {/* Weight Slider */}
            <div>
              <div className="flex justify-between text-slate-400 font-medium mb-1">
                <span>Council Weight:</span>
                <span className="font-bold text-sky-400 font-mono">{(agent2.weight * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={agent2.weight}
                onChange={(e) => setConfig({
                  ...config,
                  agent2: { ...agent2, weight: parseFloat(e.target.value) }
                })}
                className="w-full accent-sky-500"
              />
            </div>
          </div>
        </div>

        {/* Card 3: Agent 3 (Mean Reversion / Contrarian) */}
        <div className="p-5 rounded-2xl bg-[#0f141f] border border-[#1f293d] space-y-4">
          <div className="flex items-center justify-between border-b border-[#1a2333] pb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-purple-500/20 text-purple-400 flex items-center justify-center font-bold text-xs">
                A3
              </div>
              <div>
                <h3 className="font-bold text-white text-sm">Agent 3 — Mean Reversion & Reversal</h3>
                <span className="text-[10px] text-slate-400">Captures oversold bounces and statistical reversions</span>
              </div>
            </div>
            <label className="flex items-center gap-1.5 text-xs text-slate-300 font-semibold cursor-pointer">
              <input
                type="checkbox"
                checked={agent3.enabled}
                onChange={(e) => setConfig({
                  ...config,
                  agent3: { ...agent3, enabled: e.target.checked }
                })}
                className="w-4 h-4 rounded text-[#00c896] bg-slate-900 border-slate-700"
              />
              <span>Enabled</span>
            </label>
          </div>

          <div className="space-y-3 text-xs">
            {/* Strategy Select */}
            <div>
              <label className="block text-slate-400 font-medium mb-1">Active Quantitative Strategy:</label>
              <select
                value={agent3.strategy_id}
                onChange={(e) => setConfig({
                  ...config,
                  agent3: { ...agent3, strategy_id: e.target.value }
                })}
                className="w-full bg-[#121926] text-white font-bold rounded-lg px-3 py-2 border border-[#1f293d] focus:outline-none focus:border-[#00c896]"
              >
                {strategies.map((st) => (
                  <option key={st.id} value={st.id}>
                    {st.name} ({st.category})
                  </option>
                ))}
              </select>
            </div>

            {/* Weight Slider */}
            <div>
              <div className="flex justify-between text-slate-400 font-medium mb-1">
                <span>Council Weight:</span>
                <span className="font-bold text-purple-400 font-mono">{(agent3.weight * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={agent3.weight}
                onChange={(e) => setConfig({
                  ...config,
                  agent3: { ...agent3, weight: parseFloat(e.target.value) }
                })}
                className="w-full accent-purple-500"
              />
            </div>
          </div>
        </div>

        {/* Card 4: Council & Risk Management */}
        <div className="p-5 rounded-2xl bg-[#0f141f] border border-[#1f293d] space-y-4">
          <div className="flex items-center justify-between border-b border-[#1a2333] pb-3">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-emerald-500/20 text-[#00c896] flex items-center justify-center font-bold text-xs">
                CG
              </div>
              <div>
                <h3 className="font-bold text-white text-sm">Council Consensus & Risk Parameters</h3>
                <span className="text-[10px] text-slate-400">Position sizing, circuit breakers & thresholds</span>
              </div>
            </div>
          </div>

          <div className="space-y-3 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-slate-400 font-medium block mb-1">Buy Trigger Score:</label>
                <input
                  type="number"
                  step="0.05"
                  value={council.buy_trigger_score}
                  onChange={(e) => setConfig({
                    ...config,
                    council: { ...council, buy_trigger_score: parseFloat(e.target.value) }
                  })}
                  className="w-full bg-[#121926] text-white font-mono font-bold rounded-lg px-2.5 py-1.5 border border-[#1f293d]"
                />
              </div>

              <div>
                <label className="text-slate-400 font-medium block mb-1">Min Confidence %:</label>
                <input
                  type="number"
                  step="5"
                  value={council.min_confidence}
                  onChange={(e) => setConfig({
                    ...config,
                    council: { ...council, min_confidence: parseFloat(e.target.value) }
                  })}
                  className="w-full bg-[#121926] text-white font-mono font-bold rounded-lg px-2.5 py-1.5 border border-[#1f293d]"
                />
              </div>

              <div>
                <label className="text-slate-400 font-medium block mb-1">Risk Per Trade %:</label>
                <input
                  type="number"
                  step="0.1"
                  value={risk.risk_per_trade_pct}
                  onChange={(e) => setConfig({
                    ...config,
                    risk: { ...risk, risk_per_trade_pct: parseFloat(e.target.value) }
                  })}
                  className="w-full bg-[#121926] text-white font-mono font-bold rounded-lg px-2.5 py-1.5 border border-[#1f293d]"
                />
              </div>

              <div>
                <label className="text-slate-400 font-medium block mb-1">ATR Stop Multiplier:</label>
                <input
                  type="number"
                  step="0.1"
                  value={risk.atr_stop_multiplier}
                  onChange={(e) => setConfig({
                    ...config,
                    risk: { ...risk, atr_stop_multiplier: parseFloat(e.target.value) }
                  })}
                  className="w-full bg-[#121926] text-white font-mono font-bold rounded-lg px-2.5 py-1.5 border border-[#1f293d]"
                />
              </div>
            </div>

            <div className="flex items-center justify-between p-2 rounded-lg bg-[#141b29] border border-[#1f293d]">
              <span className="text-slate-300">Regime-Adaptive Dynamic Weighting:</span>
              <input
                type="checkbox"
                checked={council.regime_adaptive_weights ?? true}
                onChange={(e) => setConfig({
                  ...config,
                  council: { ...council, regime_adaptive_weights: e.target.checked }
                })}
                className="w-4 h-4 rounded text-[#00c896] bg-slate-900"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

