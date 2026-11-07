import React, { useState } from 'react';
import PriceChart from '../components/PriceChart';
import AgentCouncil from '../components/AgentCouncil';
import LossLimitMeter from '../components/LossLimitMeter';
import KillSwitchModal from '../components/KillSwitchModal';
import DemoDrawer from '../components/DemoDrawer';
import { api } from '../services/api';

export default function Cockpit({
  symbol,
  setSymbol,
  ticks = [],
  agents = {},
  decision = {},
  portfolio = {},
  systemState = 'RUNNING',
  killSwitch = 'OFF',
  journalFeed = [],
  loopRunning = false,
  onToggleLoop,
  onStepTrade,
  onResetLimit,
  onKillSwitchChange
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const [modalAction, setModalAction] = useState('ENGAGE');
  const [demoDrawerOpen, setDemoDrawerOpen] = useState(false);

  const isKilled = killSwitch === 'ON' || systemState === 'KILLED';
  const positions = portfolio.positions || [];
  const currPrice = ticks.length ? ticks[ticks.length - 1].price : 2850.0;
  const lastStopLoss = decision.suggested_stop > 0 ? decision.suggested_stop : null;

  const openKillModal = (action) => {
    setModalAction(action);
    setModalOpen(true);
  };

  const handleConfirmKillSwitch = () => {
    onKillSwitchChange(modalAction);
  };

  return (
    <div className="space-y-4">
      {/* Flight Deck Controls Bar */}
      <div className="bg-[#111827] border border-[#1f293d] rounded-xl p-3 flex flex-wrap items-center justify-between gap-3">
        {/* Symbol & Market Mode */}
        <div className="flex items-center gap-3">
          <div>
            <label className="text-[10px] text-slate-400 font-semibold block uppercase">Symbol</label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="bg-[#1e293b] border border-[#334155] rounded-lg px-3 py-1.5 text-xs font-bold text-cyan-300 focus:outline-none focus:border-cyan-500"
            >
              <option value="RELIANCE.NS">RELIANCE (NSE India)</option>
              <option value="TCS.NS">TCS (NSE India)</option>
              <option value="INFY.NS">INFOSYS (NSE India)</option>
              <option value="AAPL">AAPL (Apple Inc)</option>
              <option value="MSFT">MSFT (Microsoft)</option>
              <option value="TSLA">TSLA (Tesla Inc)</option>
            </select>
          </div>

          <div className="border-l border-slate-700 pl-3">
            <div className="text-[10px] text-slate-400">LAST PRICE</div>
            <div className="font-mono font-bold text-base text-white">
              ₹{currPrice?.toFixed(2)}
            </div>
          </div>
        </div>

        {/* Execution & Demo Action Buttons */}
        <div className="flex items-center gap-2">
          {/* Loop Start / Stop */}
          <button
            onClick={onToggleLoop}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-bold flex items-center gap-1.5 shadow-md transition ${
              loopRunning
                ? 'bg-amber-600 hover:bg-amber-500 text-white'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white'
            }`}
          >
            <span>{loopRunning ? '⏸️' : '▶️'}</span>
            <span>{loopRunning ? 'Pause Loop' : 'Start Auto Loop'}</span>
          </button>

          {/* Manual Step */}
          <button
            onClick={onStepTrade}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-600 text-xs font-semibold text-slate-200"
          >
            Step Cycle ⏭️
          </button>

          {/* Demo Drawer Trigger */}
          <button
            onClick={() => setDemoDrawerOpen(true)}
            className="px-3 py-1.5 rounded-lg bg-purple-950/80 hover:bg-purple-900 border border-purple-600/60 text-purple-300 text-xs font-bold flex items-center gap-1"
          >
            <span>🧪</span> Demo Shocks
          </button>

          {/* Emergency Kill Switch Button */}
          {isKilled ? (
            <button
              onClick={() => openKillModal('DISENGAGE')}
              className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow-lg shadow-emerald-950 animate-bounce"
            >
              🔄 RESUME TRADING
            </button>
          ) : (
            <button
              onClick={() => openKillModal('ENGAGE')}
              className="px-4 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-bold shadow-lg shadow-red-950 flex items-center gap-1.5"
            >
              <span>🛑</span> EMERGENCY KILL SWITCH
            </button>
          )}
        </div>
      </div>

      {/* Main Grid: Price Chart (Left 7) + Agent Council (Right 5) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Price Chart & Loss Limit Meter */}
        <div className="lg:col-span-7 space-y-4">
          <div className="cockpit-card p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-slate-200">LIVE COCKPIT EXECUTION CHART</span>
                <span className="text-[11px] text-cyan-400 font-mono">[{symbol}]</span>
              </div>
              <div className="text-[11px] text-slate-400">
                Rolling 50 Ticks • Real-time Mark-to-Market
              </div>
            </div>

            <PriceChart ticks={ticks} symbol={symbol} lastStopLoss={lastStopLoss} />
          </div>

          {/* Daily Loss Limit Meter */}
          <LossLimitMeter
            usedPct={portfolio.loss_limit_used_pct || 0}
            limitAmount={portfolio.loss_limit_amount || 2000}
            dayPnl={portfolio.day_pnl || 0}
            onResetLimit={onResetLimit}
          />
        </div>

        {/* Right Column: Agent Council & Position Desk */}
        <div className="lg:col-span-5 space-y-4">
          {/* Agent Council Cards */}
          <div className="cockpit-card p-4">
            <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
              <div className="font-bold text-sm text-slate-200 flex items-center gap-1.5">
                <span>🤖</span> AGENT COUNCIL & CONSENSUS
              </div>
              <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono">
                PS-02 3-AGENT ARCHITECTURE
              </span>
            </div>

            <AgentCouncil agents={agents} decision={decision} />
          </div>

          {/* Open Positions & Portfolio Status */}
          <div className="cockpit-card p-4">
            <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
              <div className="font-bold text-sm text-slate-200 flex items-center gap-1.5">
                <span>💼</span> ACTIVE POSITIONS ({positions.length}/3)
              </div>
              <div className="text-xs text-slate-400">
                Cash: <span className="font-mono text-white font-bold">₹{(portfolio.cash || 100000).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
              </div>
            </div>

            {positions.length === 0 ? (
              <div className="text-center py-6 text-slate-500 text-xs">
                <div>🛡️ No open positions</div>
                <div className="text-[10px] mt-0.5">Capital 100% liquid & protected in cash.</div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="text-[10px] text-slate-400 border-b border-slate-800 uppercase">
                    <tr>
                      <th className="pb-1.5">Symbol</th>
                      <th className="pb-1.5">Qty</th>
                      <th className="pb-1.5">Entry</th>
                      <th className="pb-1.5">Stop Loss</th>
                      <th className="pb-1.5 text-right">PnL</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                    {positions.map((p, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/30">
                        <td className="py-2 text-cyan-300 font-bold">{p.symbol}</td>
                        <td className="py-2 text-white">{p.qty}</td>
                        <td className="py-2 text-slate-300">₹{p.avg_entry_price}</td>
                        <td className="py-2 text-rose-400">₹{p.stop_loss}</td>
                        <td className={`py-2 text-right font-bold ${p.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {p.unrealized_pnl >= 0 ? '+' : ''}₹{p.unrealized_pnl?.toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom Section: Live Scrolling Plain-Language Journal Feed */}
      <div className="cockpit-card p-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-base">📜</span>
            <span className="font-bold text-sm text-slate-200">REAL-TIME AUDIT JOURNAL FEED</span>
            <span className="text-[10px] text-slate-400">(Every decision transparently explained)</span>
          </div>
          <span className="text-[10px] font-mono text-cyan-400 animate-pulse">STREAMING LIVE</span>
        </div>

        <div className="space-y-2 max-h-48 overflow-y-auto pr-2">
          {journalFeed.length === 0 ? (
            <div className="text-xs text-slate-500 py-3 text-center">
              Awaiting first trading loop event...
            </div>
          ) : (
            journalFeed.slice(0, 10).map((entry, idx) => (
              <div
                key={idx}
                className="p-2.5 rounded bg-[#0f172a] border border-[#1e293b] text-xs flex items-start gap-2.5 hover:border-slate-700 transition"
              >
                <span className="text-slate-500 font-mono text-[10px] whitespace-nowrap mt-0.5">
                  {new Date(entry.ts * 1000).toLocaleTimeString()}
                </span>
                <p className="text-slate-200 text-[11px] leading-relaxed">
                  {entry.text}
                </p>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Kill Switch Confirmation Modal */}
      <KillSwitchModal
        isOpen={modalOpen}
        action={modalAction}
        onClose={() => setModalOpen(false)}
        onConfirm={handleConfirmKillSwitch}
      />

      {/* Demo Controls Drawer */}
      <DemoDrawer
        isOpen={demoDrawerOpen}
        symbol={symbol}
        onClose={() => setDemoDrawerOpen(false)}
      />
    </div>
  );
}

