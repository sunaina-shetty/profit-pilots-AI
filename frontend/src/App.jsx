import React, { useState, useEffect, useMemo, useRef } from 'react';
import CandlestickChart from './components/CandlestickChart';
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

// Live Agent status badge helper: ANALYSING | BUY SIGNAL | SELL SIGNAL | HOLD | BLOCKED | ORDER APPROVED | EXECUTED
function getAgentStatusBadge(status, fallbackSignal) {
  const s = (status || fallbackSignal || 'ANALYSING').toUpperCase();
  if (s === 'BUY' || s === 'BUY SIGNAL') {
    return { bg: 'bg-emerald-950 text-emerald-300 border-emerald-500 shadow-sm shadow-emerald-950', dot: 'bg-emerald-400 animate-pulse', label: 'BUY SIGNAL' };
  }
  if (s === 'SELL' || s === 'SELL SIGNAL') {
    return { bg: 'bg-rose-950 text-rose-300 border-rose-500 shadow-sm shadow-rose-950', dot: 'bg-rose-400 animate-pulse', label: 'SELL SIGNAL' };
  }
  if (s === 'EXECUTED' || s === 'ORDER APPROVED') {
    return { bg: 'bg-teal-950 text-teal-300 border-teal-500', dot: 'bg-teal-400', label: s };
  }
  if (s === 'BLOCKED') {
    return { bg: 'bg-amber-950/90 text-amber-300 border-amber-600', dot: 'bg-amber-400', label: 'BLOCKED' };
  }
  if (s === 'CONFIRMED') {
    return { bg: 'bg-blue-950 text-sky-300 border-sky-500', dot: 'bg-sky-400', label: 'CONFIRMED' };
  }
  if (s === 'ANALYSING') {
    return { bg: 'bg-slate-900 text-blue-300 border-blue-600', dot: 'bg-blue-400 animate-ping', label: 'ANALYSING' };
  }
  return { bg: 'bg-slate-800 text-slate-300 border-slate-700', dot: 'bg-slate-500', label: 'HOLD' };
}

export default function App() {
  // Local language state (en: English, kn: Kannada, hi: Hindi)
  const [lang, setLang] = useState('en');
  const t = useMemo(() => translations[lang] || translations.en, [lang]);

  // User Inputs
  const [symbol, setSymbol] = useState('TCS');
  const [customSymbol, setCustomSymbol] = useState('');
  const [amount, setAmount] = useState(100000);
  const [stopLossPct, setStopLossPct] = useState(1.0);
  const [selectedDate, setSelectedDate] = useState('');
  const [stocksList, setStocksList] = useState([]);

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
    portfolio: null
  });

  // UI state & Beginner Toggles
  const [hideHolds, setHideHolds] = useState(false);
  const [showKillModal, setShowKillModal] = useState(false);
  const [selectedTradeMarker, setSelectedTradeMarker] = useState(null);
  const [apiError, setApiError] = useState(null);
  const [showLedgerDetails, setShowLedgerDetails] = useState(true);

  // Chart Indicator Toggles (Requirement C: HOLD signals off by default to eliminate clutter)
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

  // Load stocks dropdown once
  useEffect(() => {
    fetch('/api/stocks')
      .then((r) => r.json())
      .then((data) => {
        if (data.stocks) setStocksList(data.stocks);
      })
      .catch((err) => console.log('Could not load stocks list:', err));
  }, []);

  // Load historical 5-minute candles before START
  useEffect(() => {
    if (state.status === 'RUNNING') return;

    let cancelled = false;
    setIsLoadingPreview(true);
    const dateParam = selectedDate ? `&date=${encodeURIComponent(selectedDate)}` : '';
    fetch(`/api/candles?symbol=${encodeURIComponent(activeSymbol)}${dateParam}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data) => {
        if (cancelled) return;
        if (data.candles && Array.isArray(data.candles)) {
          setPreviewCandles(data.candles);
          setPreviewInfo(data);
          setApiError(null);
        }
        setIsLoadingPreview(false);
      })
      .catch((err) => {
        if (cancelled) return;
        setIsLoadingPreview(false);
        console.warn('Could not load preview candles:', err);
      });

    return () => {
      cancelled = true;
    };
  }, [activeSymbol, selectedDate, state.status]);

  // Connect to SSE stream for live real-time updates + Polling fallback
  useEffect(() => {
    let eventSource = null;
    try {
      eventSource = new EventSource('/api/stream');
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setState(data);
          setApiError(null);
        } catch (e) {}
      };
      eventSource.onerror = () => {};
    } catch (e) {}

    // 1-second fallback polling
    const poll = () => {
      fetch('/api/state')
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
    const interval = setInterval(poll, 1000);

    return () => {
      if (eventSource) eventSource.close();
      clearInterval(interval);
    };
  }, []);

  // Monitor processed candles for diagnostic logging
  const lastProcessedTimeRef = useRef(null);
  useEffect(() => {
    if (state.status === 'RUNNING' && state.simulated_time && state.simulated_time !== lastProcessedTimeRef.current) {
      lastProcessedTimeRef.current = state.simulated_time;
      console.log('[App] Candle processed at', state.simulated_time, 'Close: ₹' + (state.current_price?.toFixed(2) || '0.00'));
    }
  }, [state.simulated_time, state.status, state.current_price]);

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
          date: selectedDate || undefined
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

  const handleConfirmKill = async () => {
    setShowKillModal(false);
    try {
      const resp = await fetch('/api/kill', { method: 'POST' });
      const data = await resp.json();
      if (data.state) setState(data.state);
    } catch (err) {
      setApiError(String(err));
    }
  };

  const isRunning = state.status === 'RUNNING';
  const isKilled = state.status === 'KILLED';
  const isDone = state.status === 'DONE';

  const isSimulationActive = isRunning || isKilled || isDone;
  const displayCandles = isSimulationActive ? (state.closes_so_far || []) : previewCandles;
  const currentTimestamp = isSimulationActive && state.closes_so_far && state.closes_so_far.length > 0
    ? state.closes_so_far[state.closes_so_far.length - 1].timestamp
    : (previewCandles.length > 0 ? previewCandles[0].timestamp : null);
  const currentSimTime = isSimulationActive ? state.simulated_time : (previewInfo?.first_candle_time || '09:15');

  // Actual Strategy Agents State (Requirement D & E)
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

  // Derive Beginner Dashboard Summary from Real Engine State
  const currentRecommendation = (state.latest_decision?.action || 'HOLD').toUpperCase();
  const overallConfidence = Math.max(
    Math.round((trend.confidence || 0.5) * 100),
    Math.round((news.confidence || 0.5) * 100),
    Math.round((contrarian.confidence || 0.5) * 100)
  );

  // Market Direction (Going Up, Going Down, Moving Sideways)
  let marketDirectionLabel = t.directionSideways;
  let marketDirectionColor = 'text-blue-400 bg-blue-950/80 border-blue-700';
  let marketDirectionIcon = '↔';

  if (state.current_regime === 'TREND') {
    if (state.current_price && displayCandles.length > 0 && state.current_price >= displayCandles[0].open) {
      marketDirectionLabel = t.directionUp;
      marketDirectionColor = 'text-emerald-400 bg-emerald-950/80 border-emerald-600';
      marketDirectionIcon = '↗';
    } else {
      marketDirectionLabel = t.directionDown;
      marketDirectionColor = 'text-rose-400 bg-rose-950/80 border-rose-600';
      marketDirectionIcon = '↘';
    }
  } else if (state.current_regime === 'RANGE') {
    marketDirectionLabel = t.directionSideways;
    marketDirectionColor = 'text-purple-400 bg-purple-950/80 border-purple-700';
    marketDirectionIcon = '↔';
  } else if (!isRunning && state.status === 'IDLE') {
    marketDirectionLabel = t.directionUnclear;
    marketDirectionColor = 'text-slate-400 bg-slate-800 border-slate-700';
    marketDirectionIcon = '🔍';
  }

  // Extract subtle HOLD markers from journal for chart when enabled
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

  const filteredJournal = (state.journal || []).filter((j) => {
    if (hideHolds && (j.is_hold || j.action === 'HOLD')) return false;
    return true;
  });

  // Live Portfolio Ledger
  const portfolio = state.portfolio || {
    available_cash: state.cash,
    invested_capital: state.position ? state.position.qty * state.position.buy_price : 0.0,
    open_positions: state.position ? 1 : 0,
    average_entry_price: state.position ? state.position.buy_price : 0.0,
    current_market_price: state.current_price || 0.0,
    unrealized_pnl: state.position ? state.position.profit_loss : 0.0,
    realized_pnl: state.summary ? state.summary.net_pnl : (state.day_pnl - (state.position ? state.position.profit_loss : 0)),
    total_fees: state.summary ? state.summary.total_fees : (state.position ? (state.position.buy_fees || 0) : 0),
    total_equity: state.equity,
    daily_return_pct: ((state.equity - amount) / (amount || 1)) * 100
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 p-3 sm:p-5 flex flex-col gap-4 max-w-[1440px] mx-auto font-sans">
      {/* 1. TOP HEADER ROW WITH LANGUAGE SELECTOR */}
      <header className="bg-[#111827] border border-[#1f293d] rounded-xl px-4 py-3 flex flex-wrap items-center justify-between gap-3 shadow-md">
        <div className="flex items-center gap-3">
          <span className="text-2xl">✈️</span>
          <div>
            <div className="font-extrabold tracking-wider text-cyan-400 text-base leading-tight">
              {t.appName} <span className="text-xs px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">AI</span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono tracking-tight">
              {t.appSubtitle}
            </div>
          </div>

          <div className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-950/70 border border-amber-600/40 text-amber-300 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
            {t.paperTradingBanner}
          </div>
        </div>

        {/* Live Metrics & Language Selector */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-xs">
          {/* Status Badge */}
          <div className="flex items-center gap-1.5 bg-[#1f293d]/80 px-2.5 py-1 rounded-lg border border-slate-700">
            <span className="text-slate-400">{t.status}</span>
            {isRunning ? (
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span> {t.statusRunning}
              </span>
            ) : isKilled ? (
              <span className="text-rose-400 font-bold">🛑 {t.statusStopped}</span>
            ) : isDone ? (
              <span className="text-cyan-400 font-bold">🏁 {t.statusCompleted}</span>
            ) : (
              <span className="text-slate-400 font-bold">{t.statusIdle}</span>
            )}
          </div>

          {/* Clock */}
          <div className="bg-[#1f293d]/80 px-2.5 py-1 rounded-lg border border-slate-700 text-slate-300 font-mono">
            <span className="text-slate-400">{t.istClock} </span>
            <span className="text-cyan-300 font-bold">{state.simulated_time || '09:15'}</span>
          </div>

          {/* Total Capital */}
          <div className="bg-[#1f293d]/80 px-2.5 py-1 rounded-lg border border-slate-700">
            <span className="text-slate-400">{t.equity} </span>
            <span className="text-white font-bold">{formatINR(state.equity)}</span>
          </div>

          {/* Profit / Loss */}
          <div className="bg-[#1f293d]/80 px-2.5 py-1 rounded-lg border border-slate-700">
            <span className="text-slate-400">{t.pnl} </span>
            <span className={`font-bold ${state.day_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {state.day_pnl >= 0 ? '+' : ''}{formatINR(state.day_pnl)}
            </span>
          </div>

          {/* Language Selector (English, ಕನ್ನಡ, हिन्दी) */}
          <div className="flex items-center rounded-lg bg-[#1f293d] border border-cyan-800 p-0.5">
            <button
              data-testid="lang-en"
              onClick={() => setLang('en')}
              className={`px-2 py-0.5 rounded text-[11px] font-bold transition ${
                lang === 'en' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              English
            </button>
            <button
              data-testid="lang-kn"
              onClick={() => setLang('kn')}
              className={`px-2 py-0.5 rounded text-[11px] font-bold transition ${
                lang === 'kn' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              ಕನ್ನಡ
            </button>
            <button
              data-testid="lang-hi"
              onClick={() => setLang('hi')}
              className={`px-2 py-0.5 rounded text-[11px] font-bold transition ${
                lang === 'hi' ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              हिन्दी
            </button>
          </div>
        </div>
      </header>

      {/* 2. CONTROLS ROW */}
      <section className="bg-[#111827] border border-[#1f293d] rounded-xl p-3 sm:p-4 shadow-md">
        <div className="flex flex-wrap items-end gap-3 sm:gap-4">
          {/* Stock Symbol Dropdown */}
          <div className="flex-1 min-w-[180px]">
            <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
              {t.symbolLabel}
            </label>
            <select
              disabled={isRunning}
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="w-full bg-[#1e293b] border border-[#334155] rounded-lg px-3 py-1.5 text-xs font-bold text-cyan-300 focus:outline-none focus:border-cyan-500 disabled:opacity-50"
            >
              {stocksList.map((s) => (
                <option key={s.symbol} value={s.symbol.replace('.NS', '')}>
                  {s.display}
                </option>
              ))}
              <option value="CUSTOM">-- Custom Symbol --</option>
            </select>
          </div>

          {/* Custom Symbol Input (if selected) */}
          {symbol === 'CUSTOM' && (
            <div className="w-32">
              <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
                {t.customSymbolLabel}
              </label>
              <input
                type="text"
                disabled={isRunning}
                placeholder="e.g. BEL"
                value={customSymbol}
                onChange={(e) => setCustomSymbol(e.target.value.toUpperCase())}
                className="w-full bg-[#1e293b] border border-[#334155] rounded-lg px-3 py-1.5 text-xs text-white uppercase focus:outline-none focus:border-cyan-500"
              />
            </div>
          )}

          {/* Amount in INR */}
          <div className="w-36">
            <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
              {t.amountLabel}
            </label>
            <input
              type="number"
              disabled={isRunning}
              min="10000"
              max="100000000"
              step="5000"
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              className="w-full bg-[#1e293b] border border-[#334155] rounded-lg px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500 disabled:opacity-50"
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
              min="0.3"
              max="5.0"
              step="0.1"
              value={stopLossPct}
              onChange={(e) => setStopLossPct(Number(e.target.value))}
              className="w-full bg-[#1e293b] border border-[#334155] rounded-lg px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-cyan-500 disabled:opacity-50"
            />
          </div>

          {/* Optional Date Picker */}
          <div className="w-36">
            <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
              {t.dateLabel}
            </label>
            <input
              type="date"
              disabled={isRunning}
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-full bg-[#1e293b] border border-[#334155] rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-300 focus:outline-none focus:border-cyan-500 disabled:opacity-50"
            />
          </div>

          {/* Action Buttons: START & KILL */}
          <div className="flex items-center gap-2">
            <button
              data-testid="btn-start"
              onClick={handleStart}
              disabled={isRunning}
              className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-bold text-xs shadow-md shadow-emerald-950 transition flex items-center gap-1.5"
            >
              <span>▶️</span> {t.btnStart}
            </button>

            <button
              data-testid="btn-kill"
              onClick={() => setShowKillModal(true)}
              disabled={!isRunning}
              className="px-5 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 disabled:opacity-40 text-white font-bold text-xs shadow-md shadow-rose-950 transition flex items-center gap-1.5"
            >
              <span>🛑</span> {t.btnKill}
            </button>
          </div>
        </div>

        {/* API Error Notification */}
        {apiError && (
          <div className="mt-2.5 text-xs text-rose-300 bg-rose-950/60 border border-rose-800 rounded-lg p-2 font-mono">
            ⚠️ {apiError}
          </div>
        )}

        {/* Synthetic Data Warning Banner */}
        {((state.data_source && state.data_source.includes('SYNTHETIC')) || state.is_real_data === false) && state.status !== 'IDLE' && (
          <div className="mt-2.5 text-xs font-bold text-rose-200 bg-rose-950/90 border border-rose-600 rounded-lg p-2.5 flex items-center gap-2 tracking-wide">
            <span>🚨</span> {t.syntheticWarning}
          </div>
        )}

        {/* Real Data Verified Banner */}
        {state.is_real_data === true && state.status !== 'IDLE' && (
          <div className="mt-2 text-xs font-mono text-emerald-300 bg-emerald-950/70 border border-emerald-600 rounded-lg p-2 flex items-center gap-2">
            <span>✅</span> {t.realDataVerified}
          </div>
        )}
      </section>

      {/* 3. SIMPLIFIED SUMMARY BANNER */}
      <section className="bg-gradient-to-r from-[#0f172a] via-[#131d33] to-[#0f172a] border border-[#1f293d] rounded-xl p-3 sm:p-4 shadow-md">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div>
              <div className="text-[10px] text-slate-400 uppercase font-semibold">{t.currentPrice}</div>
              <div className="text-xl sm:text-2xl font-black text-white tracking-tight flex items-center gap-2">
                <span>{state.current_price ? `₹${state.current_price.toFixed(2)}` : '₹0.00'}</span>
                <span className={`text-[11px] px-2 py-0.5 rounded-full font-bold border flex items-center gap-1 ${marketDirectionColor}`}>
                  <span>{marketDirectionIcon}</span>
                  <span>{marketDirectionLabel}</span>
                </span>
              </div>
            </div>
            <div className="hidden sm:block h-8 w-[1px] bg-slate-800"></div>
            <div className="hidden sm:block">
              <div className="text-[10px] text-slate-400 uppercase font-semibold">{t.currentRecommendation}</div>
              <div className="flex items-center gap-2 mt-0.5">
                {currentRecommendation === 'BUY' ? (
                  <span className="px-2.5 py-0.5 rounded-lg bg-emerald-950 border border-emerald-500 text-emerald-300 font-black text-xs">
                    ▲ {t.actionBuy}
                  </span>
                ) : currentRecommendation === 'SELL' ? (
                  <span className="px-2.5 py-0.5 rounded-lg bg-rose-950 border border-rose-500 text-rose-300 font-black text-xs">
                    ▼ {t.actionSell}
                  </span>
                ) : (
                  <span className="px-2.5 py-0.5 rounded-lg bg-amber-950/80 border border-amber-600 text-amber-300 font-bold text-xs">
                    ⏸ {t.actionHold}
                  </span>
                )}
                <span className="text-cyan-400 font-bold font-mono text-[11px]">({overallConfidence}% {t.confidence})</span>
              </div>
            </div>
          </div>

          <div className="text-xs text-slate-300 max-w-xl">
            <span className="font-bold text-cyan-400">💡 {t.suggestedAction} </span>
            <span className="text-slate-300">
              {currentRecommendation === 'BUY' ? t.buyActionText : currentRecommendation === 'SELL' ? t.sellActionText : t.holdActionText}
            </span>
            <span className="text-slate-400 block text-[11px] mt-0.5 truncate">
              {state.latest_decision?.rule || trend.reason || t.holdReasonText}
            </span>
          </div>
        </div>
      </section>

      {/* 4. MAIN CONTINUOUS CANDLESTICK CHART */}
      <section className="bg-[#111827] border border-[#1f293d] rounded-xl p-3 sm:p-4 shadow-md">
        <div className="flex flex-wrap items-center justify-between mb-2 gap-2">
          <div>
            <div className="font-bold text-xs sm:text-sm text-slate-200">
              {t.chartTitle}
            </div>
            <div className="text-[10px] text-slate-400">
              {t.chartSubtitle} • Slim 5m candles with automatic execution arrows
            </div>
          </div>
          <div className="text-xs font-mono text-cyan-300">
            {activeSymbol} • {state.current_price ? `₹${state.current_price.toFixed(2)}` : '₹0.00'}
          </div>
        </div>

        {/* Candlestick Chart with Proportional Thin Candles & Prominent Markers */}
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
        />
      </section>

      {/* 5. REQUIREMENT D & E: DEDICATED LIVE MULTI-AGENT ACTIVITY SECTION */}
      <section className="bg-[#111827] border border-[#1f293d] rounded-xl p-4 shadow-md">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-base">🤖</span>
            <h3 className="font-bold text-xs sm:text-sm text-white tracking-wide">
              LIVE MULTI-AGENT ACTIVITY (3 COOPERATING AGENTS + COUNCIL CONSENSUS GATE)
            </h3>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Latest Replay Bar: <strong className="text-cyan-300">{state.simulated_time || '09:15'} IST</strong>
          </span>
        </div>

        {/* 4 Multi-Agent Cards Grid with Distinct Visual Identities */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* AGENT 1: ORB + VWAP TREND (Teal/Green Identity) */}
          <div className="rounded-xl border border-teal-600/60 bg-gradient-to-b from-[#0a2323] to-[#0f172a] p-3.5 flex flex-col justify-between shadow-md">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-extrabold text-xs text-teal-300 flex items-center gap-1.5">
                  <span>📈</span> AGENT 1: ORB TREND
                </span>
                {(() => {
                  const b = getAgentStatusBadge(trend.status, trend.signal);
                  return (
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border flex items-center gap-1 ${b.bg}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${b.dot}`}></span>
                      {b.label}
                    </span>
                  );
                })()}
              </div>

              {/* Specific Agent 1 Facts */}
              <div className="space-y-1 text-[11px] font-mono mb-2">
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Decision:</span>
                  <strong className={trend.signal === 'BUY' ? 'text-emerald-400' : 'text-slate-300'}>
                    {trend.signal || 'HOLD'} ({Math.round((trend.confidence || 0) * 100)}%)
                  </strong>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Opening Range:</span>
                  <span className="text-amber-300">H: ₹{trend.facts?.orb_high?.toFixed(2) || '—'} | L: ₹{trend.facts?.orb_low?.toFixed(2) || '—'}</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">VWAP Baseline:</span>
                  <span className="text-purple-300">₹{trend.facts?.vwap?.toFixed(2) || '—'}</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Breakout Gate:</span>
                  <span className={trend.facts?.close > trend.facts?.orb_high ? 'text-emerald-400 font-bold' : 'text-slate-400'}>
                    {trend.facts?.close > trend.facts?.orb_high ? 'Breakout Active' : 'Inside Range'}
                  </span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Entry Permitted:</span>
                  <span className={trend.facts?.in_play && !trend.facts?.orb_entry_done ? 'text-teal-300 font-bold' : 'text-slate-500'}>
                    {trend.facts?.in_play ? (trend.facts?.orb_entry_done ? 'Max 1/day Used' : 'Permitted') : 'Volume < 1.5x'}
                  </span>
                </div>
              </div>
            </div>

            <div className="border-t border-teal-900/50 pt-2 mt-1">
              <span className="text-[9px] uppercase tracking-wider text-teal-400 font-bold block mb-0.5">Decision Reason</span>
              <p className="text-[11px] text-slate-200 leading-snug line-clamp-3">
                {trend.reason || 'Scanning for opening range breakout setup'}
              </p>
            </div>
          </div>

          {/* AGENT 2: NEWS SENTIMENT (Blue Identity) */}
          <div className="rounded-xl border border-sky-600/60 bg-gradient-to-b from-[#0a1e38] to-[#0f172a] p-3.5 flex flex-col justify-between shadow-md">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-extrabold text-xs text-sky-300 flex items-center gap-1.5">
                  <span>📰</span> AGENT 2: NEWS SENTIMENT
                </span>
                {(() => {
                  const b = getAgentStatusBadge(news.status, news.signal);
                  return (
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border flex items-center gap-1 ${b.bg}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${b.dot}`}></span>
                      {b.label}
                    </span>
                  );
                })()}
              </div>

              {/* Specific Agent 2 Facts */}
              <div className="space-y-1 text-[11px] font-mono mb-2">
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Sentiment Score:</span>
                  <strong className={Number(news.sentiment || 0) >= 0 ? 'text-sky-300' : 'text-rose-400'}>
                    {news.sentiment || '0.00'}
                  </strong>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Headlines Analysed:</span>
                  <span className="text-white font-bold">{news.facts?.headlines_count || 0} headlines</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">In-Play Confirmation:</span>
                  <span className={news.in_play ? 'text-emerald-400 font-bold' : 'text-slate-400'}>
                    {news.in_play ? 'Confirmed (In Play)' : 'Neutral Volume'}
                  </span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Negative News VETO:</span>
                  <span className={news.veto_status && news.veto_status.includes('VETO') ? 'text-rose-400 font-bold animate-pulse' : 'text-slate-400'}>
                    {news.veto_status || 'None (Clear)'}
                  </span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Execution Role:</span>
                  <span className="text-slate-400 font-bold">Confirmation / Veto Only</span>
                </div>
              </div>
            </div>

            <div className="border-t border-sky-900/50 pt-2 mt-1">
              <span className="text-[9px] uppercase tracking-wider text-sky-400 font-bold block mb-0.5">Sentiment Reason</span>
              <p className="text-[11px] text-slate-200 leading-snug line-clamp-3">
                {news.reason || 'Scanning financial headlines and corporate feeds'}
              </p>
            </div>
          </div>

          {/* AGENT 3: VWAP MEAN REVERSION (Purple Identity) */}
          <div className="rounded-xl border border-purple-600/60 bg-gradient-to-b from-[#190e33] to-[#0f172a] p-3.5 flex flex-col justify-between shadow-md">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-extrabold text-xs text-purple-300 flex items-center gap-1.5">
                  <span>🛡️</span> AGENT 3: VWAP REVERSION
                </span>
                {(() => {
                  const b = getAgentStatusBadge(contrarian.status, contrarian.signal);
                  return (
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border flex items-center gap-1 ${b.bg}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${b.dot}`}></span>
                      {b.label}
                    </span>
                  );
                })()}
              </div>

              {/* Specific Agent 3 Facts */}
              <div className="space-y-1 text-[11px] font-mono mb-2">
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Regime Eligibility:</span>
                  <strong className={state.current_regime === 'RANGE' ? 'text-emerald-400' : 'text-slate-400'}>
                    {state.current_regime === 'RANGE' ? 'Eligible (RANGE Day)' : `Ineligible (${state.current_regime || 'UNCLEAR'})`}
                  </strong>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">VWAP Baseline:</span>
                  <span className="text-purple-300">₹{contrarian.facts?.vwap?.toFixed(2) || '—'}</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Sigma Bands (±2σ):</span>
                  <span className="text-cyan-300">σ = ₹{contrarian.facts?.sigma?.toFixed(2) || '0.00'}</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">RSI (14-period):</span>
                  <span className={contrarian.facts?.rsi < 35 ? 'text-emerald-400 font-bold' : 'text-slate-300'}>
                    {contrarian.facts?.rsi ? contrarian.facts.rsi.toFixed(1) : '—'} {contrarian.facts?.rsi < 35 ? '(Oversold)' : ''}
                  </span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Reversal Candle:</span>
                  <span className="text-slate-300">{contrarian.facts?.bars_count >= 12 ? 'Evaluated' : 'Need >= 12 Bars'}</span>
                </div>
              </div>
            </div>

            <div className="border-t border-purple-900/50 pt-2 mt-1">
              <span className="text-[9px] uppercase tracking-wider text-purple-400 font-bold block mb-0.5">Reversion Reason</span>
              <p className="text-[11px] text-slate-200 leading-snug line-clamp-3">
                {contrarian.reason || 'Checking statistical deviation and oversold conditions'}
              </p>
            </div>
          </div>

          {/* COUNCIL CONSENSUS & RISK GUARDIAN (Gold/Amber Identity) */}
          <div className="rounded-xl border border-amber-600/60 bg-gradient-to-b from-[#251909] to-[#0f172a] p-3.5 flex flex-col justify-between shadow-md">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="font-extrabold text-xs text-amber-300 flex items-center gap-1.5">
                  <span>⚖️</span> COUNCIL CONSENSUS GATE
                </span>
                {(() => {
                  const b = getAgentStatusBadge(council.status, council.final_decision);
                  return (
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold border flex items-center gap-1 ${b.bg}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${b.dot}`}></span>
                      {b.label}
                    </span>
                  );
                })()}
              </div>

              {/* Council Consensus Facts */}
              <div className="space-y-1 text-[11px] font-mono mb-2">
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Market Regime:</span>
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                    council.regime === 'TREND' ? 'bg-teal-950 text-teal-300 border border-teal-700' :
                    council.regime === 'RANGE' ? 'bg-purple-950 text-purple-300 border border-purple-700' :
                    'bg-slate-800 text-slate-400 border border-slate-700'
                  }`}>
                    {council.regime || 'UNCLEAR'}
                  </span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Order Approved:</span>
                  <strong className={council.approved ? 'text-emerald-400' : 'text-slate-400'}>
                    {council.approved ? `YES (${council.approved_quantity} shares)` : 'NO'}
                  </strong>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Risk Stop-Loss:</span>
                  <span className="text-rose-400 font-bold">
                    {council.approved_stop_loss > 0 ? `₹${council.approved_stop_loss.toFixed(2)}` : `${stopLossPct}% Guardrail`}
                  </span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Daily Loss Gate:</span>
                  <span className="text-emerald-400 font-bold">&lt; 2.0% Circuit Protected</span>
                </div>
                <div className="flex justify-between text-slate-300">
                  <span className="text-slate-400">Cost Filter:</span>
                  <span className="text-slate-300">3x Round-Trip Required</span>
                </div>
              </div>
            </div>

            <div className="border-t border-amber-900/50 pt-2 mt-1">
              <span className="text-[9px] uppercase tracking-wider text-amber-400 font-bold block mb-0.5">Consensus Rule / Rejection</span>
              <p className="text-[11px] text-slate-200 leading-snug line-clamp-3">
                {council.rejection_reason ? `Rejected: ${council.rejection_reason}` : (council.rule || 'Awaiting agent consensus criteria')}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 6. REAL-TIME PORTFOLIO LEDGER (10 Metrics) */}
      <section className="bg-[#111827] border border-[#1f293d] rounded-xl p-3.5 shadow-md">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2.5">
          <div className="flex items-center gap-2">
            <span>💼</span>
            <span className="font-bold text-xs text-white uppercase tracking-wider">
              REAL-TIME PORTFOLIO LEDGER
            </span>
          </div>
          <span className="font-mono text-cyan-400 text-xs font-bold">
            Total Capital: {formatINR(portfolio.total_equity)}
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-xs font-mono">
          <div className="bg-[#1f293d]/50 p-2 rounded">
            <div className="text-[9px] text-slate-400">{t.availCash}</div>
            <div className="font-bold text-white mt-0.5 truncate">{formatINR(portfolio.available_cash)}</div>
          </div>
          <div className="bg-[#1f293d]/50 p-2 rounded">
            <div className="text-[9px] text-slate-400">{t.invested}</div>
            <div className="font-bold text-slate-200 mt-0.5 truncate">{formatINR(portfolio.invested_capital)}</div>
          </div>
          <div className="bg-[#1f293d]/50 p-2 rounded">
            <div className="text-[9px] text-slate-400">{t.positions}</div>
            <div className="font-bold text-cyan-300 mt-0.5">{portfolio.open_positions ? `${portfolio.open_positions} (${state.position?.qty || 0}sh)` : '0 open'}</div>
          </div>
          <div className="bg-[#1f293d]/50 p-2 rounded">
            <div className="text-[9px] text-slate-400">{t.avgEntry}</div>
            <div className="font-bold text-slate-300 mt-0.5">{portfolio.average_entry_price > 0 ? `₹${portfolio.average_entry_price.toFixed(2)}` : '—'}</div>
          </div>
          <div className="bg-[#1f293d]/50 p-2 rounded">
            <div className="text-[9px] text-slate-400">{t.marketPrice}</div>
            <div className="font-bold text-cyan-400 mt-0.5">{portfolio.current_market_price > 0 ? `₹${portfolio.current_market_price.toFixed(2)}` : '—'}</div>
          </div>
          <div className="bg-[#1f293d]/50 p-2 rounded">
            <div className="text-[9px] text-slate-400">{t.unrealizedPnl}</div>
            <div className={`font-bold mt-0.5 truncate ${portfolio.unrealized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {portfolio.unrealized_pnl >= 0 ? '+' : ''}{formatINR(portfolio.unrealized_pnl)}
            </div>
          </div>
          <div className="bg-[#1f293d]/50 p-2 rounded">
            <div className="text-[9px] text-slate-400">{t.realizedPnl}</div>
            <div className={`font-bold mt-0.5 truncate ${portfolio.realized_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {portfolio.realized_pnl >= 0 ? '+' : ''}{formatINR(portfolio.realized_pnl)}
            </div>
          </div>
          <div className="bg-[#1f293d]/50 p-2 rounded">
            <div className="text-[9px] text-slate-400">{t.totalFees}</div>
            <div className="font-bold text-amber-300 mt-0.5 truncate">{formatINR(portfolio.total_fees)}</div>
          </div>
          <div className="bg-[#1f293d]/50 p-2 rounded">
            <div className="text-[9px] text-slate-400">{t.totalEquity}</div>
            <div className="font-bold text-white mt-0.5 truncate">{formatINR(portfolio.total_equity)}</div>
          </div>
          <div className="bg-[#1f293d]/50 p-2 rounded">
            <div className="text-[9px] text-slate-400">{t.returnPct}</div>
            <div className={`font-bold mt-0.5 ${portfolio.daily_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {portfolio.daily_return_pct >= 0 ? '+' : ''}{portfolio.daily_return_pct.toFixed(2)}%
            </div>
          </div>
        </div>

        {/* Position Summary Banner */}
        {state.position ? (
          <div className="mt-2 text-[11px] font-mono bg-cyan-950/40 border border-cyan-800/60 rounded px-2.5 py-1.5 flex items-center justify-between text-cyan-300">
            <span>Holding {state.position.qty} shares of {state.position.symbol} (Bought at ₹{state.position.buy_price.toFixed(2)})</span>
            <span className="text-rose-400 font-bold">Stop: ₹{state.position.stop_loss.toFixed(2)}</span>
          </div>
        ) : (
          <div className="mt-2 text-[11px] text-center text-slate-500 py-1 font-mono">
            🛡️ Flat Position (100% Cash Preserved in Safe Reserve)
          </div>
        )}
      </section>

      {/* 7. AUDIT DECISION JOURNAL */}
      <section className="bg-[#111827] border border-[#1f293d] rounded-xl p-3.5 shadow-md">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2.5">
          <div className="flex items-center gap-2">
            <span className="text-sm">📜</span>
            <span className="font-bold text-xs text-slate-200 uppercase">
              AUDIT DECISION JOURNAL (Real Strategy Decisions & Rejections)
            </span>
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={hideHolds}
              onChange={(e) => setHideHolds(e.target.checked)}
              className="rounded bg-[#1e293b] border-slate-600 text-cyan-600 focus:ring-0"
            />
            <span>Hide HOLDs</span>
          </label>
        </div>

        <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
          {filteredJournal.length === 0 ? (
            <div className="text-xs text-slate-500 py-3 text-center">
              No journal entries yet. Press START to simulate trading.
            </div>
          ) : (
            filteredJournal.map((entry) => (
              <div
                key={entry.id}
                className="p-2 rounded-lg bg-[#0f172a] border border-[#1e293b] text-xs flex items-start justify-between gap-3"
              >
                <div className="flex items-start gap-2">
                  <span className="font-mono text-[10px] text-cyan-400 mt-0.5 whitespace-nowrap">
                    {entry.time}
                  </span>
                  <span className={`px-1.5 py-0.2 rounded text-[10px] font-bold mt-0.5 ${
                    entry.action === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-700' :
                    entry.action === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-700' :
                    'bg-slate-800 text-slate-400'
                  }`}>
                    {entry.action}
                  </span>
                  <p className="text-slate-200 text-[11px] leading-relaxed">
                    {entry.reason}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </section>

      {/* 8. SUMMARY CARD (WHEN DAY ENDS OR AFTER KILL) */}
      {(isDone || isKilled) && state.summary && (
        <section className="bg-gradient-to-r from-[#111827] via-[#1a2333] to-[#111827] border-2 border-cyan-800/80 rounded-xl p-4 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">{isKilled ? '🛑' : '🏁'}</span>
                <h3 className="font-bold text-sm sm:text-base text-white">
                  {isKilled ? t.summaryTitleKilled : t.summaryTitleDone}
                </h3>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3 text-xs font-mono">
                <div>
                  <span className="text-slate-400 text-[10px] block">{t.totalTrades}</span>
                  <span className="font-bold text-white">{state.summary.total_trades}</span> ({state.summary.wins}W / {state.summary.losses}L)
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] block">{t.netPnl}</span>
                  <span className={`font-bold text-sm ${state.summary.net_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {state.summary.net_pnl >= 0 ? '+' : ''}{formatINR(state.summary.net_pnl)} ({state.summary.return_pct}%)
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] block">{t.benchmark}</span>
                  <span className={`font-bold text-sm ${state.summary.buy_and_hold_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {state.summary.buy_and_hold_return_pct >= 0 ? '+' : ''}{state.summary.buy_and_hold_return_pct}%
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] block">{t.finalCapital}</span>
                  <span className="font-bold text-white text-sm">{formatINR(state.summary.final_equity)}</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => {
                setState((prev) => ({ ...prev, status: 'IDLE', summary: null, closes_so_far: [], buy_markers: [], sell_markers: [], trade_connections: [], journal: [] }));
              }}
              className="px-5 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs shadow-lg shadow-cyan-950 transition"
            >
              {t.runAgain}
            </button>
          </div>
        </section>
      )}

      {/* 9. REQUIREMENT H: DETAIL PANEL MODAL (CLICK-TO-INSPECT) */}
      {selectedTradeMarker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#111827] border border-cyan-700 rounded-2xl p-5 max-w-md w-full shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
              <div className="flex items-center gap-2">
                <span className="text-xl">
                  {selectedTradeMarker.action === 'BUY' ? '🟢' : selectedTradeMarker.action === 'SELL' ? '🔴' : '🟡'}
                </span>
                <h4 className="font-bold text-white text-sm">
                  {selectedTradeMarker.action} Execution Details
                </h4>
              </div>
              <button
                onClick={() => setSelectedTradeMarker(null)}
                className="text-slate-400 hover:text-white text-sm font-bold px-2 py-1"
              >
                ✕
              </button>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div className="flex justify-between bg-[#1f293d]/50 p-2 rounded">
                <span className="text-slate-400">Responsible Agent:</span>
                <span className="text-cyan-300 font-bold">
                  {selectedTradeMarker.agent_name || selectedTradeMarker.agent_tag || 'Agent 1: ORB + VWAP Trend'}
                </span>
              </div>

              <div className="flex justify-between bg-[#1f293d]/50 p-2 rounded">
                <span className="text-slate-400">Execution Time:</span>
                <span className="text-white font-bold">{selectedTradeMarker.time_str || selectedTradeMarker.time} IST</span>
              </div>

              <div className="flex justify-between bg-[#1f293d]/50 p-2 rounded">
                <span className="text-slate-400">{selectedTradeMarker.action === 'BUY' ? 'Entry Price:' : 'Exit Price:'}</span>
                <span className={`font-bold ${selectedTradeMarker.action === 'BUY' ? 'text-emerald-400' : 'text-rose-400'}`}>
                  ₹{Number(selectedTradeMarker.price || 0).toFixed(2)}
                </span>
              </div>

              {selectedTradeMarker.qty && (
                <div className="flex justify-between bg-[#1f293d]/50 p-2 rounded">
                  <span className="text-slate-400">Quantity Filled:</span>
                  <span className="text-white font-bold">{selectedTradeMarker.qty} shares</span>
                </div>
              )}

              {selectedTradeMarker.stop_loss && (
                <div className="flex justify-between bg-[#1f293d]/50 p-2 rounded">
                  <span className="text-slate-400">Approved Stop-Loss:</span>
                  <span className="text-rose-400 font-bold">₹{Number(selectedTradeMarker.stop_loss).toFixed(2)}</span>
                </div>
              )}

              {selectedTradeMarker.fees !== undefined && selectedTradeMarker.fees !== null && (
                <div className="flex justify-between bg-[#1f293d]/50 p-2 rounded">
                  <span className="text-slate-400">Brokerage & STT Fees:</span>
                  <span className="text-amber-300 font-bold">{formatINR(selectedTradeMarker.fees)}</span>
                </div>
              )}

              {selectedTradeMarker.pnl !== null && selectedTradeMarker.pnl !== undefined && (
                <div className="flex justify-between bg-[#1f293d]/50 p-2 rounded">
                  <span className="text-slate-400">Net Realized P&L:</span>
                  <span className={`font-bold text-sm ${selectedTradeMarker.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {selectedTradeMarker.pnl >= 0 ? '+' : ''}{formatINR(selectedTradeMarker.pnl)}
                  </span>
                </div>
              )}

              {selectedTradeMarker.holding_duration && (
                <div className="flex justify-between bg-[#1f293d]/50 p-2 rounded">
                  <span className="text-slate-400">Holding Duration:</span>
                  <span className="text-cyan-300 font-bold">{selectedTradeMarker.holding_duration}</span>
                </div>
              )}

              <div className="bg-[#1f293d]/50 p-2 rounded text-[11px] leading-relaxed">
                <span className="text-slate-400 block mb-1">Decision / Strategy Reason:</span>
                <span className="text-slate-200">{selectedTradeMarker.reason || 'Council Consensus execution'}</span>
              </div>
            </div>

            <div className="mt-4 text-right">
              <button
                onClick={() => setSelectedTradeMarker(null)}
                className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold"
              >
                Close Panel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 10. KILL SWITCH CONFIRMATION MODAL */}
      {showKillModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#180a0a] border border-rose-600 rounded-2xl p-5 max-w-sm w-full shadow-2xl text-center">
            <div className="text-3xl mb-2">🛑</div>
            <h4 className="font-bold text-white text-base mb-1">{t.killModalTitle}</h4>
            <p className="text-xs text-slate-300 mb-5 leading-relaxed">
              {t.killModalMsg}
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => setShowKillModal(false)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                {t.killCancel}
              </button>
              <button
                onClick={handleConfirmKill}
                className="px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold shadow-lg shadow-rose-950"
              >
                {t.killConfirm}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
