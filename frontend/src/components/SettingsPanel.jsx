import React, { useState } from 'react';
import { Settings, Shield, Sliders, Volume2, Moon, RefreshCw, Key, Lock, CheckCircle2, AlertTriangle } from 'lucide-react';

export default function SettingsPanel({ state, onResetConfig }) {
  const [theme, setTheme] = useState('dark');
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [candleThickness, setCandleThickness] = useState('medium');
  const [broker, setBroker] = useState('paper');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [totpSecret, setTotpSecret] = useState('');
  const [showSavedToast, setShowSavedToast] = useState(false);

  const handleSave = () => {
    setShowSavedToast(true);
    setTimeout(() => setShowSavedToast(false), 3000);
  };

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="bg-[#0f141f] border border-[#1f293d] rounded-2xl p-5 shadow-lg flex justify-between items-center">
        <div>
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-emerald-400" />
            <h1 className="text-xl font-bold text-white tracking-wide">Terminal & Execution Settings</h1>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Configure terminal preferences, broker integrations, audio notifications, and safety parameters.
          </p>
        </div>

        {showSavedToast && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-950 text-emerald-300 border border-emerald-500/40 text-xs font-semibold animate-fade-in">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span>Preferences Saved</span>
          </div>
        )}
      </div>

      {/* 1. Execution Mode Configuration */}
      <div className="bg-[#0f141f] border border-[#1f293d] rounded-2xl p-5 shadow-lg space-y-4">
        <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
          <Shield className="w-4 h-4 text-[#00c896]" />
          Broker Execution Mode
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Paper Trading Mode Card */}
          <div
            onClick={() => setBroker('paper')}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              broker === 'paper'
                ? 'bg-emerald-950/20 border-emerald-500/50 shadow-md shadow-emerald-950/30'
                : 'bg-[#121926] border-[#1f293d] opacity-75'
            }`}
          >
            <div className="flex justify-between items-center mb-2">
              <span className="font-bold text-white text-sm">Paper Trading (Default)</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-black bg-emerald-500/20 text-[#00c896] border border-emerald-500/30">
                ACTIVE MODE
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Executes all algorithmic trades in simulated paper money with exact book reconciliation, realistic bid/ask slippage, and real NSE regulatory fees.
            </p>
          </div>

          {/* Live Broker Mode Card (Locked) */}
          <div
            onClick={() => alert('Live broker trading is locked in safety mode. Please configure verified broker credentials below first.')}
            className="p-4 rounded-xl border border-[#1f293d] bg-[#121926] cursor-not-allowed opacity-60"
          >
            <div className="flex justify-between items-center mb-2">
              <span className="font-bold text-slate-300 text-sm">Live Broker Execution</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-400 border border-amber-500/30 flex items-center gap-1">
                <Lock className="w-3 h-3" />
                AUTH REQUIRED
              </span>
            </div>
            <p className="text-xs text-slate-500">
              Direct routing to live broker accounts (Zerodha Kite, Upstox, Angel One). Requires explicit OAuth authorization and API key setup.
            </p>
          </div>
        </div>

        {/* Live Broker Credentials Form */}
        <div className="mt-4 p-4 rounded-xl bg-[#121926] border border-[#1f293d] space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-slate-300">
            <Key className="w-4 h-4 text-amber-400" />
            <span>Broker API Integration (Optional)</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div>
              <label className="block text-slate-400 mb-1">API Key / App Key</label>
              <input
                type="text"
                placeholder="e.g. k7b9x024y..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-[#00c896]"
              />
            </div>

            <div>
              <label className="block text-slate-400 mb-1">API Secret</label>
              <input
                type="password"
                placeholder="••••••••••••••••"
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-[#00c896]"
              />
            </div>

            <div>
              <label className="block text-slate-400 mb-1">TOTP Auth Secret</label>
              <input
                type="password"
                placeholder="••••••••"
                value={totpSecret}
                onChange={(e) => setTotpSecret(e.target.value)}
                className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-[#00c896]"
              />
            </div>
          </div>

          <div className="flex justify-between items-center pt-2">
            <span className="text-[11px] text-slate-500 italic">
              * Keys are kept local to your machine and never transmitted to external 3rd-party servers.
            </span>
            <button
              onClick={handleSave}
              className="px-4 py-1.5 rounded-lg bg-[#00c896] hover:bg-emerald-400 text-black font-extrabold text-xs shadow-md transition-all active:scale-95"
            >
              Save Credentials
            </button>
          </div>
        </div>
      </div>

      {/* 2. Visual & Audio Preferences */}
      <div className="bg-[#0f141f] border border-[#1f293d] rounded-2xl p-5 shadow-lg space-y-4">
        <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
          <Sliders className="w-4 h-4 text-sky-400" />
          Terminal Interface & Audio Preferences
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div>
            <label className="block text-slate-400 mb-1 font-semibold">Color Scheme</label>
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-2 text-white font-bold focus:outline-none focus:border-[#00c896]"
            >
              <option value="dark">Groww Dark Terminal (Recommended)</option>
              <option value="midnight">Midnight Charcoal</option>
              <option value="oled">High-Contrast OLED Black</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-400 mb-1 font-semibold">Audio Trade Execution Chimes</label>
            <button
              onClick={() => setSoundEnabled(!soundEnabled)}
              className={`w-full py-2 px-3 rounded-lg border flex items-center justify-between font-bold transition-all ${
                soundEnabled
                  ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-400'
                  : 'bg-[#161f30] border-[#1f293d] text-slate-400'
              }`}
            >
              <span>{soundEnabled ? 'Chimes Active' : 'Muted'}</span>
              <Volume2 className="w-4 h-4" />
            </button>
          </div>

          <div>
            <label className="block text-slate-400 mb-1 font-semibold">Candlestick Proportions</label>
            <select
              value={candleThickness}
              onChange={(e) => setCandleThickness(e.target.value)}
              className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-2 text-white font-bold focus:outline-none focus:border-[#00c896]"
            >
              <option value="slim">Slim High-Density (Groww Style)</option>
              <option value="medium">Standard Proportions</option>
              <option value="thick">Wide Bars</option>
            </select>
          </div>
        </div>
      </div>

      {/* 3. System Reset & Safety Actions */}
      <div className="bg-[#0f141f] border border-[#1f293d] rounded-2xl p-5 shadow-lg space-y-3">
        <h2 className="text-sm font-bold text-rose-400 uppercase tracking-wider flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          Maintenance & Factory Defaults
        </h2>
        <p className="text-xs text-slate-400">
          Reset all agent configurations, strategy parameter overrides, and paper trading local journal history.
        </p>

        <div className="pt-2">
          <button
            onClick={() => {
              if (window.confirm('Reset all agent configurations and strategy parameters to factory defaults?')) {
                onResetConfig && onResetConfig();
              }
            }}
            className="px-4 py-2 rounded-lg bg-[#161f30] hover:bg-rose-950 hover:text-rose-300 border border-[#1f293d] hover:border-rose-500/40 text-slate-300 font-bold text-xs transition-all flex items-center gap-2"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset Agent & Strategy Defaults</span>
          </button>
        </div>
      </div>
    </div>
  );
}

