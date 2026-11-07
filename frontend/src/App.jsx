import React, { useState, useEffect, useRef } from 'react';
import Banner from './components/Banner';
import Cockpit from './pages/Cockpit';
import RiskManager from './pages/RiskManager';
import Journal from './pages/Journal';
import Backtest from './pages/Backtest';
import ChaosLab from './pages/ChaosLab';
import { api } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('cockpit');
  const [symbol, setSymbol] = useState('RELIANCE.NS');

  // Live streaming states
  const [ticks, setTicks] = useState([]);
  const [agents, setAgents] = useState({});
  const [decision, setDecision] = useState({});
  const [portfolio, setPortfolio] = useState({
    cash: 100000.0,
    equity: 100000.0,
    day_pnl: 0.0,
    positions: [],
    loss_limit_used_pct: 0.0,
    loss_limit_amount: 2000.0
  });
  const [systemState, setSystemState] = useState('RUNNING');
  const [killSwitch, setKillSwitch] = useState('OFF');
  const [journalFeed, setJournalFeed] = useState([]);
  const [loopRunning, setLoopRunning] = useState(false);

  // References for latest decision context to attach to chart dots
  const latestDecisionRef = useRef(null);

  useEffect(() => {
    // 1. Subscribe to Gateway SSE Stream
    const unsubscribe = api.subscribeSSE((eventName, data) => {
      if (eventName === 'price_tick') {
        setTicks((prev) => {
          const nowStr = new Date(data.ts * 1000).toLocaleTimeString([], { hour12: false, minute: '2-digit', second: '2-digit' });
          const tickObj = {
            timeStr: nowStr,
            price: data.price,
            isStale: data.is_stale,
            action: latestDecisionRef.current?.action || 'HOLD',
            sizeTier: latestDecisionRef.current?.size_tier,
            reason: latestDecisionRef.current?.reason,
            votes: latestDecisionRef.current?.votes
          };
          const next = [...prev, tickObj];
          return next.slice(-45); // Keep rolling 45 bars
        });
      } else if (eventName === 'agent_votes') {
        setAgents(data);
      } else if (eventName === 'decision') {
        setDecision(data);
        latestDecisionRef.current = {
          action: data.action,
          size_tier: data.size_tier,
          reason: data.reason,
          votes: data.agent_votes
        };
      } else if (eventName === 'portfolio') {
        setPortfolio(data);
      } else if (eventName === 'system_state') {
        setSystemState(data.state);
        if (data.kill_switch) setKillSwitch(data.kill_switch);
      } else if (eventName === 'journal_entry') {
        setJournalFeed((prev) => [data, ...prev].slice(0, 30));
      }
    });

    // 2. Fetch Initial Status
    api.getLoopStatus()
      .then((res) => {
        setLoopRunning(res.data.loop_running);
        if (res.data.active_symbol) setSymbol(res.data.active_symbol);
      })
      .catch((err) => console.log('Gateway connecting...', err));

    return () => unsubscribe();
  }, []);

  const handleToggleLoop = async () => {
    try {
      if (loopRunning) {
        await api.stopLoop();
        setLoopRunning(false);
      } else {
        await api.startLoop(symbol, 4.0);
        setLoopRunning(true);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleStepTrade = async () => {
    try {
      await api.stepTrade(symbol);
    } catch (err) {
      console.error(err);
    }
  };

  const handleKillSwitchChange = async (action) => {
    try {
      await api.triggerKillSwitch(action);
      setKillSwitch(action === 'ENGAGE' ? 'ON' : 'OFF');
      setSystemState(action === 'ENGAGE' ? 'KILLED' : 'RUNNING');
    } catch (err) {
      console.error(err);
    }
  };

  const handleResetLimit = async () => {
    try {
      await api.resetAll();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-gray-100 flex flex-col font-sans">
      {/* Persistent Top Cockpit Banner */}
      <Banner
        systemState={systemState}
        killSwitch={killSwitch}
        dayPnl={portfolio.day_pnl}
        equity={portfolio.equity}
        cash={portfolio.cash}
      />

      {/* Navigation Bar */}
      <nav className="bg-[#111827] border-b border-[#1f293d] px-4 py-2 flex items-center justify-between text-xs sticky top-[57px] z-30">
        <div className="flex items-center gap-1 sm:gap-2">
          <button
            onClick={() => setActiveTab('cockpit')}
            className={`px-3 py-1.5 rounded-lg font-bold transition flex items-center gap-1.5 ${
              activeTab === 'cockpit'
                ? 'bg-cyan-950 text-cyan-400 border border-cyan-700'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>✈️</span> Live Cockpit
          </button>

          <button
            onClick={() => setActiveTab('risk')}
            className={`px-3 py-1.5 rounded-lg font-bold transition flex items-center gap-1.5 ${
              activeTab === 'risk'
                ? 'bg-cyan-950 text-cyan-400 border border-cyan-700'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>🛡️</span> Risk Manager
          </button>

          <button
            onClick={() => setActiveTab('journal')}
            className={`px-3 py-1.5 rounded-lg font-bold transition flex items-center gap-1.5 ${
              activeTab === 'journal'
                ? 'bg-cyan-950 text-cyan-400 border border-cyan-700'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>📜</span> Audit Journal
          </button>

          <button
            onClick={() => setActiveTab('backtest')}
            className={`px-3 py-1.5 rounded-lg font-bold transition flex items-center gap-1.5 ${
              activeTab === 'backtest'
                ? 'bg-cyan-950 text-cyan-400 border border-cyan-700'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>📊</span> Backtest
          </button>

          <button
            onClick={() => setActiveTab('chaos')}
            className={`px-3 py-1.5 rounded-lg font-bold transition flex items-center gap-1.5 ${
              activeTab === 'chaos'
                ? 'bg-purple-950 text-purple-400 border border-purple-700'
                : 'text-slate-400 hover:text-white hover:bg-slate-800'
            }`}
          >
            <span>🧪</span> Chaos Lab
          </button>
        </div>

        <div className="hidden md:flex items-center gap-3 text-[11px] text-slate-400">
          <span>Problem Statement: <strong className="text-cyan-300">PS-02</strong></span>
          <span>•</span>
          <span>Team: <strong className="text-cyan-300">Profit Pilots</strong></span>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="flex-1 p-4 max-w-7xl w-full mx-auto">
        {activeTab === 'cockpit' && (
          <Cockpit
            symbol={symbol}
            setSymbol={setSymbol}
            ticks={ticks}
            agents={agents}
            decision={decision}
            portfolio={portfolio}
            systemState={systemState}
            killSwitch={killSwitch}
            journalFeed={journalFeed}
            loopRunning={loopRunning}
            onToggleLoop={handleToggleLoop}
            onStepTrade={handleStepTrade}
            onResetLimit={handleResetLimit}
            onKillSwitchChange={handleKillSwitchChange}
          />
        )}

        {activeTab === 'risk' && <RiskManager />}
        {activeTab === 'journal' && <Journal />}
        {activeTab === 'backtest' && <Backtest />}
        {activeTab === 'chaos' && <ChaosLab />}
      </main>

      {/* Footer */}
      <footer className="border-t border-[#1f293d] bg-[#0f172a] py-3 text-center text-xs text-slate-500">
        ProfitPilot AI — Autonomous Intraday Paper Trading Agent • Built by Team Profit Pilots for PS-02 • Virtual Funds Only
      </footer>
    </div>
  );
}

