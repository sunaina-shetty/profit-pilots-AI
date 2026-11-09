import React, { useState, useEffect } from 'react';
import { Sliders, CheckCircle2, TrendingUp, Zap, HelpCircle, ArrowRight, ShieldCheck, Settings2 } from 'lucide-react';

export default function StrategyLibrary({ onAssignStrategy, activeAgent1StratId, activeAgent3StratId }) {
  const [strategies, setStrategies] = useState([]);
  const [selectedStrat, setSelectedStrat] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [customParams, setCustomParams] = useState({});
  const [saveSuccess, setSaveSuccess] = useState('');

  const loadStrategies = () => {
    fetch('/api/strategies')
      .then((r) => r.json())
      .then((d) => {
        if (d.strategies) setStrategies(d.strategies);
      })
      .catch(() => {});
  };

  useEffect(() => {
    loadStrategies();
  }, []);

  const openParamModal = (strat) => {
    setSelectedStrat(strat);
    setCustomParams({ ...(strat.params || strat.default_params || {}) });
    setModalOpen(true);
  };

  const handleSaveParams = async () => {
    if (!selectedStrat) return;
    try {
      // Determine if currently assigned to Agent 1 or Agent 3
      const patch = {};
      if (selectedStrat.id === activeAgent1StratId) {
        patch.agent1 = { params: customParams };
      }
      if (selectedStrat.id === activeAgent3StratId) {
        patch.agent3 = { params: customParams };
      }

      if (Object.keys(patch).length > 0) {
        await fetch('/api/agent-config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(patch),
        });
      }

      setSaveSuccess(`Parameters updated for ${selectedStrat.name}`);
      setTimeout(() => setSaveSuccess(''), 3000);
      setModalOpen(false);
      loadStrategies();
    } catch (e) {
      console.error(e);
    }
  };

  const getCategoryBadge = (cat) => {
    switch (cat) {
      case 'TREND':
        return 'bg-blue-950/80 text-blue-400 border-blue-500/40';
      case 'BREAKOUT':
        return 'bg-amber-950/80 text-amber-400 border-amber-500/40';
      case 'MEAN_REVERSION':
        return 'bg-purple-950/80 text-purple-400 border-purple-500/40';
      case 'MOMENTUM':
        return 'bg-teal-950/80 text-teal-400 border-teal-500/40';
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
            <span>Quantitative Strategy Catalog</span>
            <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-[#00c896] border border-emerald-500/30">
              10 Strategies Active
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-1">
            Institutional-grade technical trading strategies with configurable parameters, formulas, and multi-agent assignment.
          </p>
        </div>

        {saveSuccess && (
          <div className="px-3 py-1.5 rounded-lg bg-emerald-950/80 border border-emerald-500/50 text-emerald-300 text-xs font-semibold animate-pulse">
            ✓ {saveSuccess}
          </div>
        )}
      </div>

      {/* Strategies Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {strategies.map((st) => {
          const isAgent1Active = st.id === activeAgent1StratId;
          const isAgent3Active = st.id === activeAgent3StratId;

          return (
            <div
              key={st.id}
              className={`flex flex-col justify-between p-4 rounded-xl border transition-all ${
                isAgent1Active || isAgent3Active
                  ? 'bg-[#121a28] border-[#00c896]/60 shadow-lg shadow-emerald-950/30'
                  : 'bg-[#0f141f] border-[#1f293d] hover:border-slate-600 hover:bg-[#121824]'
              }`}
            >
              <div className="space-y-3">
                {/* Badges Bar */}
                <div className="flex items-center justify-between gap-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${getCategoryBadge(st.category)}`}>
                    {st.category}
                  </span>

                  <div className="flex items-center gap-1.5">
                    {isAgent1Active && (
                      <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-[#00c896]/20 text-[#00c896] border border-[#00c896]/40">
                        Agent 1 Active
                      </span>
                    )}
                    {isAgent3Active && (
                      <span className="px-1.5 py-0.2 rounded text-[10px] font-bold bg-purple-500/20 text-purple-400 border border-purple-500/40">
                        Agent 3 Active
                      </span>
                    )}
                  </div>
                </div>

                {/* Title */}
                <div>
                  <h3 className="text-sm font-bold text-white tracking-wide">{st.name}</h3>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                    {st.description}
                  </p>
                </div>

                {/* Formula Snippet */}
                <div className="p-2 rounded-lg bg-[#0b0e14] border border-[#1a2333] font-mono text-[10px] text-slate-300 leading-normal">
                  <span className="text-slate-500 block text-[9px] uppercase font-bold tracking-wider mb-0.5">FORMULA:</span>
                  {st.formula}
                </div>

                {/* Key Metrics */}
                <div className="grid grid-cols-2 gap-2 text-[11px] font-mono pt-1">
                  <div className="bg-[#141b29] p-2 rounded border border-[#1f293d]">
                    <span className="text-[10px] text-slate-400 block">Win Rate Target</span>
                    <span className="text-emerald-400 font-bold">{st.win_rate_target}</span>
                  </div>
                  <div className="bg-[#141b29] p-2 rounded border border-[#1f293d]">
                    <span className="text-[10px] text-slate-400 block">Risk Profile</span>
                    <span className="text-sky-400 font-bold">{st.risk_level}</span>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-4 border-t border-[#1a2333] mt-4 flex items-center justify-between gap-2">
                <button
                  onClick={() => openParamModal(st)}
                  className="p-1.5 rounded-lg bg-[#1a2333] hover:bg-slate-700 text-slate-300 text-xs flex items-center gap-1 font-semibold transition-colors"
                  title="Configure Parameters"
                >
                  <Settings2 className="w-3.5 h-3.5" />
                  <span>Params</span>
                </button>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => onAssignStrategy('agent1', st.id)}
                    className={`px-2 py-1 rounded-lg text-xs font-bold transition-all ${
                      isAgent1Active
                        ? 'bg-[#00c896] text-black font-extrabold'
                        : 'bg-[#1a2333] hover:bg-[#00c896]/20 text-slate-300 hover:text-[#00c896] border border-[#1f293d]'
                    }`}
                  >
                    Set Agent 1
                  </button>

                  <button
                    onClick={() => onAssignStrategy('agent3', st.id)}
                    className={`px-2 py-1 rounded-lg text-xs font-bold transition-all ${
                      isAgent3Active
                        ? 'bg-purple-600 text-white font-extrabold'
                        : 'bg-[#1a2333] hover:bg-purple-600/20 text-slate-300 hover:text-purple-400 border border-[#1f293d]'
                    }`}
                  >
                    Set Agent 3
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Parameter Edit Modal */}
      {modalOpen && selectedStrat && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="bg-[#121926] border border-[#1f293d] rounded-2xl w-full max-w-lg shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
              <div>
                <h3 className="font-bold text-white text-base">Configure {selectedStrat.name}</h3>
                <span className="text-xs text-slate-400">Tune strategy parameters for backtesting & execution</span>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-white p-1 rounded"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 max-h-72 overflow-y-auto">
              {Object.entries(customParams).map(([k, val]) => (
                <div key={k} className="flex items-center justify-between gap-4 p-2 rounded-lg bg-[#0f1420] border border-[#1a2333]">
                  <label className="text-xs font-medium text-slate-300 capitalize">
                    {k.replace(/_/g, ' ')}:
                  </label>
                  {typeof val === 'boolean' ? (
                    <input
                      type="checkbox"
                      checked={val}
                      onChange={(e) => setCustomParams({ ...customParams, [k]: e.target.checked })}
                      className="w-4 h-4 rounded text-[#00c896] focus:ring-0 bg-slate-900"
                    />
                  ) : (
                    <input
                      type={typeof val === 'number' ? 'number' : 'text'}
                      step="any"
                      value={val}
                      onChange={(e) => {
                        const parsed = typeof val === 'number' ? parseFloat(e.target.value) || 0 : e.target.value;
                        setCustomParams({ ...customParams, [k]: parsed });
                      }}
                      className="w-28 bg-[#161f30] text-white text-xs font-mono font-bold px-2 py-1 rounded border border-[#1f293d] text-right focus:outline-none focus:border-[#00c896]"
                    />
                  )}
                </div>
              ))}
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#1f293d]">
              <button
                onClick={() => setModalOpen(false)}
                className="px-4 py-2 rounded-lg bg-[#1a2333] text-slate-300 text-xs font-semibold hover:bg-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveParams}
                className="px-4 py-2 rounded-lg bg-[#00c896] text-black text-xs font-bold hover:bg-emerald-400 transition-colors shadow-lg shadow-emerald-950/50"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

