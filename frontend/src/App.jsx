import React, { useState, useEffect, useMemo, useRef } from 'react';
import CandlestickChart from './components/CandlestickChart';
import TopMarketBar from './components/TopMarketBar';
import RightDock from './components/RightDock';
import StrategyLibrary from './components/StrategyLibrary';
import AgentConfigPanel from './components/AgentConfigPanel';
import NewsIntelligence from './components/NewsIntelligence';
import RiskManagement from './components/RiskManagement';
import PortfolioLedger from './components/PortfolioLedger';
import TradeSignalInspector from './components/TradeSignalInspector';
import KillSwitchModal from './components/KillSwitchModal';
import Dashboard from './components/Dashboard';
import MarketsOverview from './components/MarketsOverview';
import Backtesting from './components/Backtesting';
import SettingsPanel from './components/SettingsPanel';
import { translations } from './i18n';

// Format Indian Currency
function formatINR(val) {
  if (val === undefined || val === null || isNaN(val)) return '₹0.00';
  return (
    (val < 0 ? '-₹' : '₹') +
    Math.abs(val).toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })
  );
}

// Resample 5m candles into higher timeframe chunks (15m, 1h)
function resampleCandles(candles, factor) {
  if (!candles || candles.length === 0 || factor <= 1) return candles || [];
  const resampled = [];
  for (let i = 0; i < candles.length; i += factor) {
    const chunk = candles.slice(i, i + factor);
    if (chunk.length === 0) continue;
    const first = chunk[0];
    const last = chunk[chunk.length - 1];
    resampled.push({
      ...last,
      open: first.open,
      high: Math.max(...chunk.map((c) => Number(c.high) || first.open)),
      low: Math.min(...chunk.map((c) => Number(c.low) || first.open)),
      close: last.close,
      volume: chunk.reduce((acc, c) => acc + (Number(c.volume) || 0), 0),
      time: last.time,
      timestamp: last.timestamp || last.time,
      time_str: last.time_str || first.time_str
    });
  }
  return resampled;
}

export default function App() {
  const [lang, setLang] = useState('en');
  const t = useMemo(() => translations[lang] || translations.en, [lang]);

  // Terminal Navigation Tab
  const [activeTab, setActiveTab] = useState('terminal'); // 'terminal' | 'strategies' | 'agents' | 'portfolio' | 'orders' | 'signals' | 'news' | 'risk'

  // User Inputs
  const [marketMode, setMarketMode] = useState('SIMULATION'); // 'SIMULATION' | 'LIVE'
  const [symbol, setSymbol] = useState('TCS');
  const [customSymbol, setCustomSymbol] = useState('');
  const [amount, setAmount] = useState(100000);
  const [stopLossPct, setStopLossPct] = useState(1.0);
  const [selectedDate, setSelectedDate] = useState('');
  const [stocksList, setStocksList] = useState([]);
  const [timeframe, setTimeframe] = useState('5m'); // '5m' | '15m' | '1h' | '1d' | '1w' | '1mo'
  const [simulationSpeed, setSimulationSpeed] = useState('20x'); // '1x' | '5x' | '10x' | '20x' | '50x'

  // Server state
  const [state, setState] = useState({
    status: 'IDLE',
    symbol: 'TCS.NS',
    data_source: 'IDLE',
    simulated_time: '09:15',
    equity: 100000,
    cash: 100000,
    day_pnl: 0,
    position: null,
    active_stop_loss: null,
    closes_so_far: [],
    buy_markers: [],
    sell_markers: [],
    trade_connections: [],
    latest_agents: {},
    latest_decision: {},
    journal: [],
    summary: null,
    portfolio: null,
    agent_config: null
  });

  // UI state
  const [showKillModal, setShowKillModal] = useState(false);
  const [selectedTradeMarker, setSelectedTradeMarker] = useState(null);
  const [apiError, setApiError] = useState(null);

  // Chart Indicators
  const [showVwap, setShowVwap] = useState(true);
  const [showOrbHigh, setShowOrbHigh] = useState(true);
  const [showOrbLow, setShowOrbLow] = useState(true);
  const [showStopLoss, setShowStopLoss] = useState(true);
  const [showHoldSignals, setShowHoldSignals] = useState(false);

  // Preview candle data loaded before START
  const [previewCandles, setPreviewCandles] = useState([]);
  const [previewInfo, setPreviewInfo] = useState(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);

  const activeSymbol = (symbol === 'CUSTOM' ? customSymbol : symbol) || 'TCS';

  // Load stocks dropdown & agent configuration once
  useEffect(() => {
    fetch('/api/stocks')
      .then((r) => r.json())
      .then((data) => {
        if (data.stocks) setStocksList(data.stocks);
      })
      .catch((err) => console.error('Failed to load stock list:', err));

    fetch('/api/agent-config')
      .then((r) => r.json())
      .then((data) => {
        if (data) setState((prev) => ({ ...prev, agent_config: data }));
      })
      .catch(() => {});
  }, []);

  const useMoneycontrol = state.agent_config?.agent2?.use_moneycontrol ?? true;

  const handleToggleMoneycontrolNews = async (enable) => {
    try {
      const resp = await fetch('/api/news-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ use_moneycontrol: enable })
      });
      const data = await resp.json();
      if (data.config) {
        setState((prev) => ({ ...prev, agent_config: data.config }));
      }
    } catch (err) {
      console.warn('Failed to toggle news config:', err);
    }
  };

  // Fetch pre-START session preview candles whenever symbol or date changes
  useEffect(() => {
    if (state.status === 'RUNNING') return;

    let isCancelled = false;
    setIsLoadingPreview(true);
    setApiError(null);

    const targetDateParam = selectedDate ? `&date=${selectedDate}` : '';
    const tfParam = `&timeframe=${encodeURIComponent(timeframe)}`;
    fetch(`/api/candles?symbol=${encodeURIComponent(activeSymbol)}${targetDateParam}${tfParam}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (isCancelled) return;
        if (data.status === 'success' && Array.isArray(data.candles)) {
          setPreviewCandles(data.candles);
          setPreviewInfo(data);
        } else {
          setPreviewCandles([]);
          setPreviewInfo(null);
        }
      })
      .catch((err) => {
        if (!isCancelled) {
          console.warn('[App] Could not load preview candles:', err);
          setPreviewCandles([]);
          setPreviewInfo(null);
        }
      })
      .finally(() => {
        if (!isCancelled) setIsLoadingPreview(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [activeSymbol, selectedDate, timeframe, state.status]);

  // Real-time EventSource SSE + Fallback Polling (dynamic for Live vs Simulation)
  useEffect(() => {
    let eventSource = null;
    const streamUrl = marketMode === 'LIVE' ? '/api/live/stream' : '/api/stream';
    try {
      eventSource = new EventSource(streamUrl);
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setState(data);
          setApiError(null);
        } catch (e) {}
      };
      eventSource.onerror = () => {};
    } catch (e) {}

    const pollUrl = marketMode === 'LIVE' ? '/api/live/state' : '/api/state';
    const poll = () => {
      fetch(pollUrl)
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then((data) => {
          setState(data);
          setApiError(null);
        })
        .catch(() => {});
    };

    poll();
    const interval = setInterval(poll, marketMode === 'LIVE' ? 1200 : 1000);

    return () => {
      if (eventSource) eventSource.close();
      clearInterval(interval);
    };
  }, [marketMode]);

  const handleToggleMarketMode = async (mode) => {
    setMarketMode(mode);
    setApiError(null);
    if (mode === 'LIVE') {
      try {
        const resp = await fetch('/api/live/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol: activeSymbol })
        });
        const data = await resp.json();
        if (data.state) setState(data.state);
      } catch (err) {
        console.warn('Failed to start live stream:', err);
      }
    }
  };

  const handleSymbolChange = async (newSym) => {
    setSymbol(newSym);
    if (newSym !== 'CUSTOM') setCustomSymbol('');
    if (marketMode === 'LIVE') {
      try {
        const clean = newSym === 'CUSTOM' ? customSymbol : newSym;
        const resp = await fetch('/api/live/switch', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ symbol: clean })
        });
        const data = await resp.json();
        if (data.state) setState(data.state);
      } catch (err) {
        console.warn('Failed to switch live symbol:', err);
      }
    }
  };

  const handleLiveOrder = async (side) => {
    try {
      const resp = await fetch('/api/live/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ side, qty: 10 })
      });
      const data = await resp.json();
      if (data.state) setState(data.state);
    } catch (err) {
      setApiError(String(err));
    }
  };

  const handleSpeedChange = async (newSpeed) => {
    setSimulationSpeed(newSpeed);
    if (state.status === 'RUNNING') {
      try {
        await fetch('/api/speed', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ speed: newSpeed })
        });
      } catch (err) {
        console.warn('Failed to dynamically update speed:', err);
      }
    }
  };

  const handleStart = async () => {
    setApiError(null);
    try {
      const resp = await fetch('/api/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: activeSymbol,
          amount: Number(amount),
          stop_loss_pct: Number(stopLossPct),
          date: selectedDate || undefined,
          speed: simulationSpeed
        })
      });
      const data = await resp.json();
      if (!resp.ok) {
        setApiError(data.error || 'Failed to start simulation');
      } else {
        setState(data.state);
      }
    } catch (err) {
      setApiError(String(err));
    }
  };

  const handleConfirmKill = async (mode = 'flatten') => {
    setShowKillModal(false);
    try {
      const resp = await fetch('/api/kill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode })
      });
      const data = await resp.json();
      if (data.state) setState(data.state);
    } catch (err) {
      setApiError(String(err));
    }
  };

  const handleAssignStrategy = async (agentKey, strategyId) => {
    try {
      const patch = { [agentKey]: { strategy_id: strategyId } };
      const res = await fetch('/api/agent-config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch)
      });
      const data = await res.json();
      if (data.config) {
        setState((prev) => ({ ...prev, agent_config: data.config }));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleResetConfig = async () => {
    try {
      const res = await fetch('/api/agent-config/reset', { method: 'POST' });
      const data = await res.json();
      if (data.config) {
        setState((prev) => ({ ...prev, agent_config: data.config }));
      }
    } catch (err) {
      console.error(err);
    }
  };

  const isRunning = state.status === 'RUNNING';
  const isKilled = state.status === 'KILLED';
  const isDone = state.status === 'DONE';

  const isSimulationActive = isRunning || isKilled || isDone;
  const displayCandles = useMemo(() => {
    if (marketMode === 'LIVE') {
      const liveBars = (state.candles && state.candles.length > 0) ? state.candles : (state.closes_so_far || []);
      if (liveBars.length > 0) {
        if (timeframe === '5m') return liveBars;
        if (timeframe === '15m') return resampleCandles(liveBars, 3);
        if (timeframe === '1h') return resampleCandles(liveBars, 12);
        return liveBars;
      }
      return previewCandles || [];
    }
    if (!isSimulationActive) return previewCandles || [];
    const base = state.closes_so_far || [];
    if (timeframe === '5m') return base;
    if (timeframe === '15m') return resampleCandles(base, 3);
    if (timeframe === '1h') return resampleCandles(base, 12);
    // For 1d, 1w, 1mo, if preview candles exist, reflect current simulated close
    if (previewCandles && previewCandles.length > 0) {
      if (base.length > 0) {
        const lastBase = base[base.length - 1];
        const lastPrev = previewCandles[previewCandles.length - 1];
        const updatedLast = {
          ...lastPrev,
          close: lastBase.close,
          high: Math.max(lastPrev.high, lastBase.high),
          low: Math.min(lastPrev.low, lastBase.low),
        };
        return [...previewCandles.slice(0, -1), updatedLast];
      }
      return previewCandles;
    }
    return base;
  }, [marketMode, state.candles, isSimulationActive, state.closes_so_far, previewCandles, timeframe]);
  const currentTimestamp = marketMode === 'LIVE' && state.candles && state.candles.length > 0
    ? state.candles[state.candles.length - 1].timestamp
    : (isSimulationActive && state.closes_so_far && state.closes_so_far.length > 0
      ? state.closes_so_far[state.closes_so_far.length - 1].timestamp
      : (previewCandles.length > 0 ? previewCandles[0].timestamp : null));
  const currentSimTime = marketMode === 'LIVE'
    ? (state.last_update || 'LIVE')
    : (isSimulationActive ? state.simulated_time : (previewInfo?.first_candle_time || '09:15'));

  // Strategy Agents State
  const trend = state.latest_agents?.trend || {
    status: isRunning ? 'ANALYSING' : 'HOLD',
    signal: 'HOLD',
    confidence: 0.5,
    reason: 'Awaiting market open indicators',
    last_evaluation_time: '09:15',
    facts: {}
  };
  const news = state.latest_agents?.news || {
    status: 'HOLD',
    signal: 'HOLD',
    confidence: 0.5,
    reason: 'Scanning morning headlines',
    last_evaluation_time: '09:15',
    facts: {}
  };
  const contrarian = state.latest_agents?.contrarian || {
    status: 'HOLD',
    signal: 'HOLD',
    confidence: 0.5,
    reason: 'Checking statistical range',
    last_evaluation_time: '09:15',
    facts: {}
  };
  const council = state.latest_agents?.council || {
    status: state.latest_decision?.action === 'BUY' ? 'BUY' : 'HOLD',
    final_decision: state.latest_decision?.action || 'HOLD',
    approved: state.latest_decision?.approved ?? false,
    approved_quantity: 0,
    approved_stop_loss: 0.0,
    rejection_reason: state.latest_decision?.rejection_reason || '',
    regime: state.current_regime || 'UNCLEAR',
    last_evaluation_time: state.simulated_time || '09:15',
    rule: state.latest_decision?.rule || ''
  };

  // Extract subtle HOLD markers from journal for chart
  const holdMarkers = useMemo(() => {
    if (!showHoldSignals || !state.journal) return [];
    return state.journal
      .filter((j) => j.is_hold || j.action === 'HOLD')
      .map((j) => {
        const matchingCandle = displayCandles.find((c) => c.time === j.time || c.time_str === j.time);
        return {
          id: j.id,
          time: matchingCandle ? matchingCandle.timestamp : j.time,
          timestamp: matchingCandle ? matchingCandle.timestamp : null,
          time_str: j.time,
          price: j.price || (matchingCandle ? matchingCandle.close : 0),
          action: 'HOLD',
          reason: j.reason
        };
      });
  }, [state.journal, displayCandles, showHoldSignals]);

  // Current market price
  const currentPrice = state.current_price || (displayCandles.length > 0 ? displayCandles[displayCandles.length - 1].close : 0.0);

  return (
    <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col font-sans select-none">
      {/* 1. TOP GROWW-INSPIRED MARKET BAR */}
      <TopMarketBar
        symbol={activeSymbol}
        onSelectSymbol={handleSymbolChange}
        stocksList={stocksList}
        state={state}
        isRunning={isRunning}
        isKilled={isKilled}
        isDone={isDone}
        onStartSimulation={handleStart}
        onOpenKillModal={() => setShowKillModal(true)}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        marketMode={marketMode}
        onToggleMarketMode={handleToggleMarketMode}
      />

      {/* 2. MAIN WORKSPACE CONTENT BASED ON ACTIVE TAB */}
      <main className="flex-1 overflow-x-hidden">
        {/* 1. DASHBOARD OVERVIEW TAB */}
        {activeTab === 'dashboard' && (
          <Dashboard
            state={state}
            symbol={activeSymbol}
            onNavigateToTab={(tabId) => setActiveTab(tabId)}
            onStartSimulation={handleStart}
            onOpenKillModal={() => setShowKillModal(true)}
            isRunning={isRunning}
          />
        )}

        {/* 2. MARKETS OVERVIEW TAB */}
        {activeTab === 'markets' && (
          <MarketsOverview
            stocksList={stocksList}
            onSelectStockForTerminal={(sym) => {
              handleSymbolChange(sym);
              setActiveTab('terminal');
            }}
          />
        )}

        {activeTab === 'terminal' && (
          <div className="flex flex-col lg:flex-row h-full">
            {/* Left Area: Controls + Chart + Agent Cards */}
            <div className="flex-1 p-3 sm:p-5 space-y-4 overflow-y-auto">
              {/* Controls Bar (Adaptive for Live Market vs Simulation) */}
              <section className="bg-[#0f141f] border border-[#1f293d] rounded-xl p-3 sm:p-4 shadow-md">
                {marketMode === 'LIVE' ? (
                  /* LIVE MARKET CONTROLS */
                  <div className="flex flex-wrap items-end justify-between gap-3 sm:gap-4">
                    <div className="flex flex-wrap items-end gap-3 sm:gap-4 flex-1">
                      {/* Stock Symbol Dropdown for Live Market */}
                      <div className="min-w-[180px]">
                        <label className="block text-[11px] font-semibold text-rose-400 uppercase mb-1 flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-ping" />
                          <span>Live Stock Symbol</span>
                        </label>
                        <select
                          value={symbol}
                          onChange={(e) => handleSymbolChange(e.target.value)}
                          className="w-full bg-[#161f30] border border-rose-500/40 rounded-lg px-3 py-1.5 text-xs font-bold text-white focus:outline-none focus:border-rose-400"
                        >
                          {stocksList.map((s) => (
                            <option key={s.symbol} value={s.symbol.replace('.NS', '')}>
                              {s.display}
                            </option>
                          ))}
                          <option value="CUSTOM">Custom Symbol...</option>
                        </select>
                      </div>

                      {symbol === 'CUSTOM' && (
                        <div className="w-32">
                          <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                            Symbol
                          </label>
                          <input
                            type="text"
                            placeholder="e.g. INFY"
                            value={customSymbol}
                            onChange={(e) => {
                              setCustomSymbol(e.target.value.toUpperCase());
                              handleSymbolChange(e.target.value.toUpperCase());
                            }}
                            className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-1.5 text-xs font-bold text-white uppercase focus:outline-none focus:border-[#00c896]"
                          />
                        </div>
                      )}

                      {/* Live Data Injection Status Badge */}
                      <div className="px-3 py-1.5 rounded-lg bg-rose-950/60 border border-rose-500/40 flex items-center gap-2">
                        <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse shadow-sm shadow-rose-500" />
                        <div>
                          <span className="text-[10px] font-bold text-rose-300 block uppercase tracking-wider">
                            Live Stream Ingestion
                          </span>
                          <span className="text-xs font-mono font-bold text-white">
                            {state.last_update || state.simulated_time || 'ACTIVE'} IST
                          </span>
                        </div>
                      </div>

                      {/* Instant Paper Trade Buttons (Zero Bot Fee) */}
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleLiveOrder('BUY')}
                          className="px-4 py-2 rounded-lg bg-[#00c896] hover:bg-emerald-400 text-black font-extrabold text-xs shadow-lg shadow-emerald-950/40 transition-all active:scale-95 flex items-center gap-1.5"
                          title="Execute instant live paper BUY order (0 bot fee)"
                        >
                          <span>▲ BUY (10 Qty)</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => handleLiveOrder('SELL')}
                          className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white font-extrabold text-xs shadow-lg shadow-rose-950/40 transition-all active:scale-95 flex items-center gap-1.5"
                          title="Execute instant live paper SELL/FLATTEN order (0 bot fee)"
                        >
                          <span>▼ SELL / FLATTEN</span>
                        </button>
                      </div>
                    </div>

                    <button
                      type="button"
                      onClick={() => handleToggleMarketMode('SIMULATION')}
                      className="px-3 py-1.5 rounded-lg bg-[#141b29] hover:bg-slate-800 text-slate-300 text-xs font-bold border border-[#1f293d] transition-all flex items-center gap-1"
                    >
                      <span>✈️ Switch to Simulation</span>
                    </button>
                  </div>
                ) : (
                  /* SIMULATION CONTROLS */
                  <div className="flex flex-wrap items-end gap-3 sm:gap-4">
                    {/* Stock Symbol Dropdown */}
                    <div className="flex-1 min-w-[170px]">
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        {t.symbolLabel}
                      </label>
                      <select
                        disabled={isRunning}
                        value={symbol}
                        onChange={(e) => setSymbol(e.target.value)}
                        className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-1.5 text-xs font-bold text-white focus:outline-none focus:border-[#00c896] disabled:opacity-50"
                      >
                        {stocksList.map((s) => (
                          <option key={s.symbol} value={s.symbol.replace('.NS', '')}>
                            {s.display}
                          </option>
                        ))}
                        <option value="CUSTOM">Custom Symbol...</option>
                      </select>
                    </div>

                    {/* Custom Symbol Input if selected */}
                    {symbol === 'CUSTOM' && (
                      <div className="w-32">
                        <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                          Symbol
                        </label>
                        <input
                          type="text"
                          disabled={isRunning}
                          placeholder="e.g. INFY"
                          value={customSymbol}
                          onChange={(e) => setCustomSymbol(e.target.value.toUpperCase())}
                          className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-1.5 text-xs font-bold text-white uppercase focus:outline-none focus:border-[#00c896]"
                        />
                      </div>
                    )}

                    {/* Investment Amount */}
                    <div className="w-36">
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        {t.amountLabel}
                      </label>
                      <input
                        type="number"
                        disabled={isRunning}
                        step="10000"
                        min="10000"
                        max="100000000"
                        value={amount}
                        onChange={(e) => setAmount(Number(e.target.value))}
                        className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-1.5 text-xs font-mono font-bold text-white focus:outline-none focus:border-[#00c896] disabled:opacity-50"
                      />
                    </div>

                    {/* Stop-Loss % */}
                    <div className="w-36">
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        {t.stopLossLabel}
                      </label>
                      <input
                        type="number"
                        disabled={isRunning}
                        step="0.1"
                        min="0.3"
                        max="5.0"
                        value={stopLossPct}
                        onChange={(e) => setStopLossPct(Number(e.target.value))}
                        className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-1.5 text-xs font-mono font-bold text-white focus:outline-none focus:border-[#00c896] disabled:opacity-50"
                      />
                    </div>

                    {/* Trading Day Date Picker */}
                    <div className="w-36">
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        {t.dateLabel}
                      </label>
                      <input
                        type="date"
                        disabled={isRunning}
                        value={selectedDate}
                        onChange={(e) => setSelectedDate(e.target.value)}
                        className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-1.5 text-xs font-mono font-bold text-white focus:outline-none focus:border-[#00c896] disabled:opacity-50"
                      />
                    </div>

                    {/* Simulation Speed Pill Buttons (with prominent 20x) */}
                    <div className="flex flex-col">
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                        Speed
                      </label>
                      <div className="flex items-center bg-[#161f30] border border-[#1f293d] rounded-lg p-0.5 gap-0.5">
                        {[
                          { id: '1x', label: '1x' },
                          { id: '5x', label: '5x' },
                          { id: '10x', label: '10x' },
                          { id: '20x', label: '20x' },
                          { id: '50x', label: '50x' }
                        ].map((sp) => {
                          const isActive = simulationSpeed.toLowerCase() === sp.id.toLowerCase();
                          const is20x = sp.id === '20x';
                          return (
                            <button
                              key={sp.id}
                              type="button"
                              onClick={() => handleSpeedChange(sp.id)}
                              className={`px-2 py-1 rounded text-xs font-extrabold transition-all flex items-center gap-0.5 ${
                                isActive
                                  ? 'bg-amber-400 text-slate-950 shadow-sm shadow-amber-950 font-black'
                                  : is20x
                                  ? 'text-amber-400 font-bold hover:bg-[#1f293d]'
                                  : 'text-slate-400 hover:text-white hover:bg-[#1f293d]'
                              }`}
                              title={`Run simulation at ${sp.label} speed`}
                            >
                              {is20x && <span className="text-[10px]">⚡</span>}
                              <span>{sp.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* START SIMULATION BUTTON */}
                    <button
                      disabled={isRunning}
                      onClick={handleStart}
                      className="px-5 py-2 rounded-lg bg-[#00c896] hover:bg-emerald-400 disabled:opacity-40 disabled:hover:bg-[#00c896] text-black font-extrabold text-xs shadow-lg shadow-emerald-950/40 transition-all active:scale-95 flex items-center gap-1.5"
                    >
                      <span>▶ {t.btnStart}</span>
                    </button>

                    {/* STOP ALL (KILL) BUTTON */}
                    <button
                      disabled={!isRunning}
                      onClick={() => setShowKillModal(true)}
                      className="px-4 py-2 rounded-lg bg-rose-600/90 hover:bg-rose-500 disabled:opacity-30 disabled:hover:bg-rose-600 text-white font-extrabold text-xs shadow-lg shadow-rose-950/40 transition-all active:scale-95 flex items-center gap-1.5"
                    >
                      <span>🛑 {t.btnKill}</span>
                    </button>
                  </div>
                )}

                {apiError && (
                  <div className="mt-3 p-2 bg-rose-950/90 border border-rose-600 text-rose-300 text-xs rounded-lg font-mono">
                    ⚠️ {apiError}
                  </div>
                )}
              </section>

              {/* Candlestick Chart with fx Indicators Dropdown */}
              <section className="bg-[#0f141f] border border-[#1f293d] rounded-xl p-3 sm:p-4 shadow-md space-y-3">
                <CandlestickChart
                  candles={displayCandles}
                  buyMarkers={state.buy_markers || []}
                  sellMarkers={state.sell_markers || []}
                  holdMarkers={holdMarkers}
                  tradeConnections={state.trade_connections || []}
                  activeStopLoss={state.active_stop_loss}
                  currentSimulatedTime={currentSimTime}
                  currentTimestamp={currentTimestamp}
                  isReplaying={isRunning}
                  onSelectMarker={(m) => setSelectedTradeMarker(m)}
                  t={t}
                  showVwap={showVwap}
                  setShowVwap={setShowVwap}
                  showOrbHigh={showOrbHigh}
                  setShowOrbHigh={setShowOrbHigh}
                  showOrbLow={showOrbLow}
                  setShowOrbLow={setShowOrbLow}
                  showStopLoss={showStopLoss}
                  setShowStopLoss={setShowStopLoss}
                  showHoldSignals={showHoldSignals}
                  setShowHoldSignals={setShowHoldSignals}
                  selectedTimeframe={timeframe}
                  onSelectTimeframe={(tf) => setTimeframe(tf)}
                  simulationSpeed={simulationSpeed}
                  onSelectSpeed={handleSpeedChange}
                  isLiveMode={marketMode === 'LIVE'}
                  onExecuteOrder={handleLiveOrder}
                />
              </section>

              {/* 4 Agent Cards (Agent 1, Agent 2 Moneycontrol News, Agent 3, Council Consensus Gate) */}
              <section className="bg-[#0f141f] border border-[#1f293d] rounded-xl p-3 sm:p-4 shadow-md space-y-3">
                <div className="flex items-center justify-between border-b border-[#1a2333] pb-2 text-xs">
                  <div className="font-bold text-white flex items-center gap-2">
                    <span>Multi-Agent Consensus Matrix</span>
                    <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-[#00c896] border border-emerald-500/30">
                      Cooperating Intraday Team
                    </span>
                  </div>
                  <span className="text-slate-400 font-mono text-[11px]">
                    {marketMode === 'LIVE' ? 'Live Stream Bar' : 'Replay Bar'}: {currentSimTime} IST
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                  {/* Agent 1 Card */}
                  <div className="p-3 rounded-lg bg-[#121824] border border-[#1a2333] space-y-1.5">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-slate-200 text-xs truncate">
                        {trend.agent_name || 'Agent 1: Trend'}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        trend.signal === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500' :
                        trend.signal === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-500' : 'bg-slate-800 text-slate-400'
                      }`}>
                        {trend.signal || 'HOLD'}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono flex justify-between">
                      <span>Conviction:</span>
                      <span className="text-white font-bold">{trend.score !== undefined ? `${trend.score > 0 ? '+' : ''}${Number(trend.score).toFixed(2)}` : '0.00'}</span>
                    </div>
                    <div className="text-[10px] text-slate-400 line-clamp-2 italic">
                      "{trend.reason || 'Scanning setup'}"
                    </div>
                  </div>

                  {/* Agent 2 Card: Switchable Moneycontrol (Default YES) vs Previous RSS Logic */}
                  <div className="p-3 rounded-lg bg-[#121824] border border-[#1a2333] space-y-1.5">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-slate-200 text-xs truncate">
                        {useMoneycontrol ? 'Agent 2: Moneycontrol' : 'Agent 2: News (RSS)'}
                      </span>
                      <button
                        type="button"
                        onClick={() => handleToggleMoneycontrolNews(!useMoneycontrol)}
                        className={`px-1.5 py-0.5 rounded text-[9px] font-extrabold transition-all border ${
                          useMoneycontrol
                            ? 'bg-emerald-950 text-emerald-400 border-emerald-500 shadow-sm'
                            : 'bg-slate-800 text-slate-300 border-slate-700 hover:text-white'
                        }`}
                        title="Click to toggle between Moneycontrol (Default YES) and Previous RSS logic"
                      >
                        {useMoneycontrol ? '⚡ MC: ON' : '🌐 RSS: ON'}
                      </button>
                    </div>

                    <div className="flex justify-between items-center pt-0.5">
                      <span className="text-[10px] text-slate-400">Verdict:</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        useMoneycontrol
                          ? (news.signal === 'BUY' || news.status === 'YES'
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-500'
                            : news.signal === 'SELL'
                            ? 'bg-rose-950 text-rose-400 border border-rose-500 animate-pulse'
                            : 'bg-amber-950 text-amber-400 border border-amber-500')
                          : (news.signal === 'BUY'
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-500'
                            : news.signal === 'SELL'
                            ? 'bg-rose-950 text-rose-400 border border-rose-500'
                            : 'bg-slate-800 text-slate-400')
                      }`}>
                        {useMoneycontrol
                          ? (news.signal === 'BUY' || news.status === 'YES'
                            ? 'YES (APPROVED)'
                            : news.signal === 'SELL'
                            ? 'SELL (SHOCK)'
                            : 'HOLD (ADVERSE)')
                          : (news.signal || news.classification || 'HOLD')}
                      </span>
                    </div>

                    <div className="text-[11px] text-slate-400 font-mono flex justify-between">
                      <span>{useMoneycontrol ? 'Verdict / Conf:' : 'Sentiment:'}</span>
                      <span className="text-white font-bold">
                        {useMoneycontrol
                          ? `${news.status || news.signal || 'YES'} • ${news.confidence || 65}%`
                          : (news.sentiment || `${(news.score || 0) > 0 ? '+' : ''}${Number(news.score || 0).toFixed(2)}`)}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-400 line-clamp-2 italic">
                      "{news.reason || news.headline || (useMoneycontrol ? 'Moneycontrol Feed: Positive / Steady. Default YES active.' : 'Scanning standard RSS wires.')}"
                    </div>
                  </div>

                  {/* Agent 3 Card */}
                  <div className="p-3 rounded-lg bg-[#121824] border border-[#1a2333] space-y-1.5">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-slate-200 text-xs truncate">
                        {contrarian.agent_name || 'Agent 3: Reversion'}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                        contrarian.signal === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500' :
                        contrarian.signal === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-500' : 'bg-slate-800 text-slate-400'
                      }`}>
                        {contrarian.signal || 'HOLD'}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono flex justify-between">
                      <span>Conviction:</span>
                      <span className="text-white font-bold">{contrarian.score !== undefined ? `${contrarian.score > 0 ? '+' : ''}${contrarian.score.toFixed(2)}` : '0.00'}</span>
                    </div>
                    <div className="text-[10px] text-slate-400 line-clamp-2 italic">
                      "{contrarian.reason || 'Checking statistical range'}"
                    </div>
                  </div>

                  {/* Council Consensus Card */}
                  <div className="p-3 rounded-lg bg-[#141b29] border border-blue-500/40 space-y-1.5 shadow-sm">
                    <div className="flex justify-between items-center">
                      <span className="font-bold text-white text-xs">
                        Council Consensus
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-black ${
                        council.final_decision === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500' :
                        council.final_decision === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-500' : 'bg-slate-800 text-slate-300'
                      }`}>
                        {council.final_decision || 'HOLD'}
                      </span>
                    </div>
                    <div className="text-[11px] text-slate-400 font-mono flex justify-between">
                      <span>Regime / Order:</span>
                      <span className="text-purple-400 font-bold">{state.current_regime || 'UNCLEAR'}</span>
                    </div>
                    <div className="text-[10px] text-slate-300 line-clamp-2 italic">
                      "{council.rule || 'Waiting for consensus threshold'}"
                    </div>
                  </div>
                </div>
              </section>
            </div>

            {/* Right Area: Groww Dock */}
            <RightDock
              state={state}
              isRunning={isRunning}
              symbol={activeSymbol}
              onSelectSymbol={(sym) => {
                setSymbol(sym);
                setCustomSymbol('');
              }}
              stocksList={stocksList}
              currentPrice={currentPrice}
            />
          </div>
        )}

        {/* 3. STRATEGY LIBRARY TAB */}
        {activeTab === 'strategies' && (
          <StrategyLibrary
            onAssignStrategy={handleAssignStrategy}
            activeAgent1StratId={state.agent_config?.agent1?.strategy_id || 'strat_orb'}
            activeAgent3StratId={state.agent_config?.agent3?.strategy_id || 'strat_bb_rsi_reversal'}
          />
        )}

        {/* 4. AGENT CONFIGURATION TAB */}
        {activeTab === 'agents' && (
          <AgentConfigPanel
            onConfigUpdated={(newCfg) => {
              setState((prev) => ({ ...prev, agent_config: newCfg }));
            }}
          />
        )}

        {/* 5. PORTFOLIO & LEDGER TAB */}
        {activeTab === 'portfolio' && (
          <PortfolioLedger state={state} />
        )}

        {/* 6. ORDERS & TRADE HISTORY TAB */}
        {activeTab === 'orders' && (
          <PortfolioLedger state={state} />
        )}

        {/* 7. SIGNAL INSPECTOR TAB */}
        {activeTab === 'signals' && (
          <TradeSignalInspector journal={state.journal || []} selectedMarker={selectedTradeMarker} />
        )}

        {/* 8. NEWS INTELLIGENCE TAB */}
        {activeTab === 'news' && (
          <NewsIntelligence
            state={state}
            useMoneycontrol={useMoneycontrol}
            onToggleMoneycontrol={() => handleToggleMoneycontrolNews(!useMoneycontrol)}
          />
        )}

        {/* 9. RISK MANAGEMENT TAB */}
        {activeTab === 'risk' && (
          <RiskManagement state={state} />
        )}

        {/* 10. QUANTITATIVE BACKTESTING LAB TAB */}
        {activeTab === 'backtest' && (
          <Backtesting
            stocksList={stocksList}
            onSelectSymbol={(sym) => {
              setSymbol(sym);
              setCustomSymbol('');
            }}
            onOpenTerminalWithSymbol={(sym) => {
              setSymbol(sym);
              setCustomSymbol('');
              setActiveTab('terminal');
            }}
          />
        )}

        {/* 11. TERMINAL SETTINGS & PREFERENCES TAB */}
        {activeTab === 'settings' && (
          <SettingsPanel
            state={state}
            onResetConfig={handleResetConfig}
          />
        )}
      </main>

      {/* EMERGENCY KILL SWITCH DUAL-MODE MODAL */}
      <KillSwitchModal
        isOpen={showKillModal}
        onClose={() => setShowKillModal(false)}
        onConfirmKill={handleConfirmKill}
      />

      {/* SELECTED TRADE MARKER DETAIL MODAL (WHEN USER CLICKS ARROW ON CHART) */}
      {selectedTradeMarker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#111827] border border-[#1f293d] rounded-2xl max-w-md w-full p-5 shadow-2xl font-mono text-xs space-y-3">
            <div className="flex items-center justify-between border-b border-[#1f293d] pb-2 font-sans">
              <div className="flex items-center gap-2">
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                  selectedTradeMarker.action === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-500' : 'bg-rose-950 text-rose-400 border border-rose-500'
                }`}>
                  {selectedTradeMarker.action}
                </span>
                <span className="font-bold text-white text-sm">Execution Details</span>
              </div>
              <button
                onClick={() => setSelectedTradeMarker(null)}
                className="text-slate-400 hover:text-white p-1 rounded"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between bg-[#161f30] p-2 rounded">
                <span className="text-slate-400">Responsible Agent:</span>
                <span className="text-white font-bold">{selectedTradeMarker.agent_name || selectedTradeMarker.agent_tag || 'Council'}</span>
              </div>
              <div className="flex justify-between bg-[#161f30] p-2 rounded">
                <span className="text-slate-400">Execution Time:</span>
                <span className="text-white font-bold">{selectedTradeMarker.time_str || selectedTradeMarker.time} IST</span>
              </div>
              <div className="flex justify-between bg-[#161f30] p-2 rounded">
                <span className="text-slate-400">Execution Price:</span>
                <span className="text-emerald-400 font-bold">₹{Number(selectedTradeMarker.price || 0).toFixed(2)}</span>
              </div>
              {selectedTradeMarker.qty && (
                <div className="flex justify-between bg-[#161f30] p-2 rounded">
                  <span className="text-slate-400">Quantity Filled:</span>
                  <span className="text-white font-bold">{selectedTradeMarker.qty} shares</span>
                </div>
              )}
              {selectedTradeMarker.pnl !== null && selectedTradeMarker.pnl !== undefined && (
                <div className="flex justify-between bg-[#161f30] p-2 rounded">
                  <span className="text-slate-400">Net Realized P&L:</span>
                  <span className={`font-bold ${selectedTradeMarker.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {selectedTradeMarker.pnl >= 0 ? '+' : ''}{formatINR(selectedTradeMarker.pnl)}
                  </span>
                </div>
              )}
              <div className="bg-[#161f30] p-2 rounded text-[11px] text-slate-300">
                <span className="text-slate-400 block mb-0.5">Execution Reason:</span>
                {selectedTradeMarker.reason || 'Council Consensus execution'}
              </div>
            </div>

            <div className="text-right pt-2 border-t border-[#1f293d]">
              <button
                onClick={() => setSelectedTradeMarker(null)}
                className="px-4 py-1.5 rounded-lg bg-[#1a2333] hover:bg-slate-700 text-slate-200 text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
