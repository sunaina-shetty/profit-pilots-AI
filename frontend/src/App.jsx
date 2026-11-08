import React, { useState, useEffect, useMemo } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine
} from 'recharts';

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

// Generate full-day minute timeline from 09:15 to 15:30 (375 minutes)
function generateDayTimeline() {
  const times = [];
  let h = 9;
  let m = 15;
  for (let i = 0; i < 375; i++) {
    const hh = String(h).padStart(2, '0');
    const mm = String(m).padStart(2, '0');
    times.push(`${hh}:${mm}`);
    m++;
    if (m === 60) {
      m = 0;
      h++;
    }
  }
  return times;
}

const FULL_DAY_TIMES = generateDayTimeline();

export default function App() {
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
    latest_agents: {},
    latest_decision: {},
    journal: [],
    summary: null
  });

  // UI state
  const [hideHolds, setHideHolds] = useState(false);
  const [showKillModal, setShowKillModal] = useState(false);
  const [apiError, setApiError] = useState(null);

  // Load stocks dropdown once
  useEffect(() => {
    fetch('/api/stocks')
      .then((r) => r.json())
      .then((data) => {
        if (data.stocks) setStocksList(data.stocks);
      })
      .catch((err) => console.log('Could not load stocks list:', err));
  }, []);

  // Poll state every 1 second
  useEffect(() => {
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
        .catch((err) => {
          // Keep polling silently
        });
    };

    poll();
    const interval = setInterval(poll, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleStart = async () => {
    setApiError(null);
    const activeSym = (symbol === 'CUSTOM' ? customSymbol : symbol) || 'TCS';
    try {
      const resp = await fetch('/api/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: activeSym,
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

  // Merge full day timeline with closes so far, so X-axis is fixed 09:15 - 15:30
  const chartData = useMemo(() => {
    const closesMap = new Map();
    (state.closes_so_far || []).forEach((item) => {
      closesMap.set(item.time, item.price);
    });

    const buyMap = new Map();
    (state.buy_markers || []).forEach((b) => buyMap.set(b.time, b));

    const sellMap = new Map();
    (state.sell_markers || []).forEach((s) => sellMap.set(s.time, s));

    return FULL_DAY_TIMES.map((time) => ({
      time,
      price: closesMap.has(time) ? closesMap.get(time) : null,
      buyMarker: buyMap.get(time) || null,
      sellMarker: sellMap.get(time) || null
    }));
  }, [state.closes_so_far, state.buy_markers, state.sell_markers]);

  // Compute auto-scaled Y range
  const { minY, maxY } = useMemo(() => {
    const validPrices = (state.closes_so_far || []).map((c) => c.price);
    if (!validPrices.length) return { minY: 'auto', maxY: 'auto' };
    let minP = Math.min(...validPrices);
    let maxP = Math.max(...validPrices);
    if (state.active_stop_loss) {
      minP = Math.min(minP, state.active_stop_loss);
    }
    const pad = Math.max(1.0, (maxP - minP) * 0.08);
    return {
      minY: Math.floor(minP - pad),
      maxY: Math.ceil(maxP + pad)
    };
  }, [state.closes_so_far, state.active_stop_loss]);

  // Custom Dot renderer for Buy (green ▲) and Sell (red ▼)
  const renderCustomDot = (props) => {
    const { cx, cy, payload } = props;
    if (!payload || payload.price === null) return null;

    if (payload.buyMarker) {
      return (
        <svg key={`buy-${payload.time}`} x={cx - 7} y={cy - 14} width="14" height="14" viewBox="0 0 14 14">
          <polygon points="7,0 14,14 0,14" fill="#10b981" stroke="#064e3b" strokeWidth="1" />
        </svg>
      );
    }

    if (payload.sellMarker) {
      return (
        <svg key={`sell-${payload.time}`} x={cx - 7} y={cy} width="14" height="14" viewBox="0 0 14 14">
          <polygon points="0,0 14,0 7,14" fill="#ef4444" stroke="#7f1d1d" strokeWidth="1" />
        </svg>
      );
    }

    return null;
  };

  const isRunning = state.status === 'RUNNING';
  const isKilled = state.status === 'KILLED';
  const isDone = state.status === 'DONE';

  const trend = state.latest_agents?.trend || { signal: 'HOLD', confidence: 0.5, reason: 'Awaiting indicators' };
  const news = state.latest_agents?.news || { signal: 'HOLD', confidence: 0.5, reason: 'Scanning news feed' };
  const contrarian = state.latest_agents?.contrarian || { signal: 'HOLD', confidence: 0.5, reason: 'Checking crowd extremes' };

  const filteredJournal = (state.journal || []).filter((j) => {
    if (hideHolds && j.is_hold) return false;
    return true;
  });

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 p-3 sm:p-5 flex flex-col gap-4 max-w-[1440px] mx-auto">
      {/* 1. TOP HEADER ROW */}
      <header className="bg-[#111827] border border-[#1f293d] rounded-xl px-4 py-3 flex flex-wrap items-center justify-between gap-3 shadow-md">
        <div className="flex items-center gap-3">
          <span className="text-2xl">✈️</span>
          <div>
            <div className="font-extrabold tracking-wider text-cyan-400 text-base leading-tight">
              PROFITPILOT <span className="text-xs px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">AI</span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono tracking-tight">
              FLY FOR PROFIT. LAND SAFE.
            </div>
          </div>

          <div className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-950/70 border border-amber-600/40 text-amber-300 text-xs font-semibold">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
            PAPER TRADING — VIRTUAL MONEY ONLY
          </div>
        </div>

        {/* Live Metrics */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-xs font-mono">
          {/* Status Badge */}
          <div className="flex items-center gap-1.5 bg-[#1f293d]/80 px-2.5 py-1 rounded-lg border border-slate-700">
            <span className="text-slate-400">STATUS:</span>
            {isRunning ? (
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span> RUNNING
              </span>
            ) : isKilled ? (
              <span className="text-rose-400 font-bold">🛑 KILLED</span>
            ) : isDone ? (
              <span className="text-cyan-400 font-bold">🏁 DONE</span>
            ) : (
              <span className="text-slate-400 font-bold">IDLE</span>
            )}
          </div>

          {/* Clock */}
          <div className="bg-[#1f293d]/80 px-2.5 py-1 rounded-lg border border-slate-700 text-slate-300">
            <span className="text-slate-400">IST: </span>
            <span className="text-cyan-300 font-bold">{state.simulated_time || '09:15'}</span>
          </div>

          {/* Equity */}
          <div className="bg-[#1f293d]/80 px-2.5 py-1 rounded-lg border border-slate-700">
            <span className="text-slate-400">EQUITY: </span>
            <span className="text-white font-bold">{formatINR(state.equity)}</span>
          </div>

          {/* Day P&L */}
          <div className="bg-[#1f293d]/80 px-2.5 py-1 rounded-lg border border-slate-700">
            <span className="text-slate-400">P&L: </span>
            <span className={`font-bold ${state.day_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
              {state.day_pnl >= 0 ? '+' : ''}{formatINR(state.day_pnl)}
            </span>
          </div>
        </div>
      </header>

      {/* 2. CONTROLS ROW */}
      <section className="bg-[#111827] border border-[#1f293d] rounded-xl p-3 sm:p-4 shadow-md">
        <div className="flex flex-wrap items-end gap-3 sm:gap-4">
          {/* Stock Symbol Dropdown */}
          <div className="flex-1 min-w-[180px]">
            <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
              Symbol (NSE)
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
                Enter Symbol
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
              Amount (₹)
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
          <div className="w-28">
            <label className="block text-[11px] font-semibold text-slate-400 uppercase mb-1">
              Stop-Loss %
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
              Session Date
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
              onClick={handleStart}
              disabled={isRunning}
              className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white font-bold text-xs shadow-md shadow-emerald-950 transition flex items-center gap-1.5"
            >
              <span>▶️</span> START
            </button>

            <button
              onClick={() => setShowKillModal(true)}
              disabled={!isRunning}
              className="px-5 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 disabled:opacity-40 text-white font-bold text-xs shadow-md shadow-rose-950 transition flex items-center gap-1.5"
            >
              <span>🛑</span> KILL
            </button>
          </div>
        </div>

        {/* API Error Notification */}
        {apiError && (
          <div className="mt-2.5 text-xs text-rose-300 bg-rose-950/60 border border-rose-800 rounded-lg p-2 font-mono">
            ⚠️ {apiError}
          </div>
        )}

        {/* Data Source Label */}
        {state.data_source && state.data_source !== 'IDLE' && (
          <div className="mt-2 text-[11px] font-mono text-cyan-400">
            📊 Feed Source: <span className="font-semibold text-slate-300">{state.data_source}</span>
          </div>
        )}
      </section>

      {/* 3. MAIN GRID: CHART (LEFT) + 3 AGENTS & POSITION (RIGHT) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Intraday Price Line Chart (09:15 to 15:30) */}
        <section className="lg:col-span-7 bg-[#111827] border border-[#1f293d] rounded-xl p-4 shadow-md flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <div className="font-bold text-xs sm:text-sm text-slate-200">
                INTRADAY PRICE ACTION (09:15 – 15:30 IST)
              </div>
              <div className="text-[11px] font-mono text-cyan-300">
                Current: {state.current_price ? `₹${state.current_price.toFixed(2)}` : '₹0.00'}
              </div>
            </div>

            {/* Chart Legend */}
            <div className="flex items-center gap-4 text-[10px] text-slate-400 mb-2">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 bg-emerald-500 rounded-sm"></span> ▲ BUY Fill
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 bg-rose-500 rounded-sm"></span> ▼ SELL / Exit
              </span>
              {state.active_stop_loss && (
                <span className="flex items-center gap-1 text-rose-400 font-mono">
                  <span className="w-3 border-b-2 border-dashed border-rose-500"></span> Active Stop: ₹{state.active_stop_loss.toFixed(2)}
                </span>
              )}
            </div>
          </div>

          <div className="w-full h-[340px] relative">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 15, left: 5, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis
                  dataKey="time"
                  stroke="#64748b"
                  ticks={['09:15', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '15:30']}
                  tick={{ fontSize: 10 }}
                />
                <YAxis
                  domain={[minY, maxY]}
                  stroke="#64748b"
                  orientation="right"
                  tick={{ fontSize: 10 }}
                  tickFormatter={(val) => `₹${val}`}
                />
                <Tooltip
                  formatter={(val) => (val ? `₹${Number(val).toFixed(2)}` : '')}
                  labelFormatter={(lbl) => `Time: ${lbl} IST`}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                />
                {state.active_stop_loss && (
                  <ReferenceLine
                    y={state.active_stop_loss}
                    stroke="#ef4444"
                    strokeDasharray="4 4"
                    label={{
                      value: `Stop: ₹${state.active_stop_loss.toFixed(2)}`,
                      fill: '#f87171',
                      fontSize: 10,
                      position: 'insideBottomRight'
                    }}
                  />
                )}
                <Line
                  type="monotone"
                  dataKey="price"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  connectNulls={false}
                  isAnimationActive={false}
                  dot={renderCustomDot}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>

        {/* Right Column: 3 Agents Cards, Decision, and Position */}
        <section className="lg:col-span-5 flex flex-col gap-3">
          {/* 3 Agent Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            {/* 1. Trend Agent */}
            <div className="bg-[#111827] border border-[#1f293d] rounded-xl p-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-300">📈 Trend</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    trend.signal === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-600' :
                    trend.signal === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-600' :
                    'bg-slate-800 text-slate-300'
                  }`}>
                    {trend.signal}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 mb-1">
                  Confidence: <span className="font-mono text-cyan-400 font-bold">{Math.round((trend.confidence || 0) * 100)}%</span>
                </div>
              </div>
              <p className="text-[11px] text-slate-300 leading-tight mt-1 line-clamp-3">
                {trend.reason}
              </p>
            </div>

            {/* 2. News Agent */}
            <div className="bg-[#111827] border border-[#1f293d] rounded-xl p-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-300">📰 News</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    news.signal === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-600' :
                    news.signal === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-600' :
                    'bg-slate-800 text-slate-300'
                  }`}>
                    {news.signal}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 mb-1">
                  Confidence: <span className="font-mono text-cyan-400 font-bold">{Math.round((news.confidence || 0) * 100)}%</span>
                </div>
              </div>
              <p className="text-[11px] text-slate-300 leading-tight mt-1 line-clamp-3">
                {news.reason}
              </p>
            </div>

            {/* 3. Contrarian Agent */}
            <div className="bg-[#111827] border border-[#1f293d] rounded-xl p-3 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-300">🛡️ Contrarian</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    contrarian.signal === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-600' :
                    contrarian.signal === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-600' :
                    'bg-slate-800 text-slate-300'
                  }`}>
                    {contrarian.signal}
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 mb-1">
                  Confidence: <span className="font-mono text-cyan-400 font-bold">{Math.round((contrarian.confidence || 0) * 100)}%</span>
                </div>
              </div>
              <p className="text-[11px] text-slate-300 leading-tight mt-1 line-clamp-3">
                {contrarian.reason}
              </p>
            </div>
          </div>

          {/* Final Decision & Rule Used */}
          <div className="bg-[#111827] border border-[#1f293d] rounded-xl p-3 shadow-md flex items-center justify-between gap-3">
            <div>
              <div className="text-[10px] text-slate-400 uppercase font-semibold">Council Decision</div>
              <div className="text-xs font-bold text-slate-200 mt-0.5">
                {state.latest_decision?.rule || 'Waiting for closed 5m bar'}
              </div>
            </div>
            <div className="text-right">
              <span className={`px-3 py-1 rounded text-xs font-extrabold ${
                state.latest_decision?.action === 'BUY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-600' :
                state.latest_decision?.action === 'SELL' ? 'bg-rose-950 text-rose-400 border border-rose-600' :
                'bg-slate-800 text-slate-300'
              }`}>
                {state.latest_decision?.action || 'HOLD'}
                {state.latest_decision?.size && state.latest_decision.size !== 'none' && ` (${state.latest_decision.size})`}
              </span>
            </div>
          </div>

          {/* Open Position Desk */}
          <div className="bg-[#111827] border border-[#1f293d] rounded-xl p-3.5 shadow-md flex-1 flex flex-col justify-center">
            <div className="text-xs font-bold text-slate-300 mb-2 border-b border-slate-800 pb-1 flex justify-between">
              <span>💼 PORTFOLIO POSITION</span>
              <span className="font-mono text-slate-400">Cash: {formatINR(state.cash)}</span>
            </div>

            {state.position ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                <div className="bg-[#1f293d]/50 p-2 rounded">
                  <div className="text-[10px] text-slate-400">QUANTITY</div>
                  <div className="font-bold text-white mt-0.5">{state.position.qty} shares</div>
                </div>
                <div className="bg-[#1f293d]/50 p-2 rounded">
                  <div className="text-[10px] text-slate-400">BUY PRICE</div>
                  <div className="font-bold text-slate-200 mt-0.5">₹{state.position.buy_price.toFixed(2)}</div>
                </div>
                <div className="bg-[#1f293d]/50 p-2 rounded">
                  <div className="text-[10px] text-slate-400">STOP-LOSS</div>
                  <div className="font-bold text-rose-400 mt-0.5">₹{state.position.stop_loss.toFixed(2)}</div>
                </div>
                <div className="bg-[#1f293d]/50 p-2 rounded">
                  <div className="text-[10px] text-slate-400">UNREALIZED P&L</div>
                  <div className={`font-bold mt-0.5 ${state.position.profit_loss >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {state.position.profit_loss >= 0 ? '+' : ''}{formatINR(state.position.profit_loss)}
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-4 text-xs text-slate-500">
                🛡️ No open position (100% Capital Safe in Cash)
              </div>
            )}
          </div>
        </section>
      </div>

      {/* 4. SUMMARY CARD (WHEN DAY ENDS OR AFTER KILL) */}
      {(isDone || isKilled) && state.summary && (
        <section className="bg-gradient-to-r from-[#111827] via-[#1a2333] to-[#111827] border-2 border-cyan-800/80 rounded-xl p-4 shadow-xl">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">{isKilled ? '🛑' : '🏁'}</span>
                <h3 className="font-bold text-sm sm:text-base text-white">
                  {isKilled ? 'SIMULATION ABORTED (EMERGENCY KILL SWITCH)' : 'SESSION COMPLETED — PERFORMANCE SUMMARY'}
                </h3>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-3 text-xs font-mono">
                <div>
                  <span className="text-slate-400 text-[10px] block">TOTAL TRADES</span>
                  <span className="font-bold text-white">{state.summary.total_trades}</span> ({state.summary.wins}W / {state.summary.losses}L)
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] block">BOT NET P&L (AFTER FEES)</span>
                  <span className={`font-bold text-sm ${state.summary.net_pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {state.summary.net_pnl >= 0 ? '+' : ''}{formatINR(state.summary.net_pnl)} ({state.summary.return_pct}%)
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] block">BUY & HOLD BENCHMARK</span>
                  <span className={`font-bold text-sm ${state.summary.buy_and_hold_return_pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {state.summary.buy_and_hold_return_pct >= 0 ? '+' : ''}{state.summary.buy_and_hold_return_pct}%
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 text-[10px] block">FINAL EQUITY</span>
                  <span className="font-bold text-white text-sm">{formatINR(state.summary.final_equity)}</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => {
                setState((prev) => ({ ...prev, status: 'IDLE', summary: null, closes_so_far: [], buy_markers: [], sell_markers: [], journal: [] }));
              }}
              className="px-5 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs shadow-lg shadow-cyan-950 transition"
            >
              🔄 Run Again
            </button>
          </div>
        </section>
      )}

      {/* 5. BOTTOM SECTION: AUDIT JOURNAL */}
      <section className="bg-[#111827] border border-[#1f293d] rounded-xl p-4 shadow-md">
        <div className="flex items-center justify-between border-b border-slate-800 pb-2.5 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-sm">📜</span>
            <span className="font-bold text-xs sm:text-sm text-slate-200">
              AUDIT DECISION JOURNAL
            </span>
            <span className="text-[10px] text-slate-500 hidden sm:inline">
              (Plain-English explanation for every BUY, SELL, and HOLD)
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

        {/* Entries list */}
        <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
          {filteredJournal.length === 0 ? (
            <div className="text-xs text-slate-500 py-4 text-center">
              No journal entries yet. Press START to simulate trading.
            </div>
          ) : (
            filteredJournal.map((entry) => (
              <div
                key={entry.id}
                className="p-2.5 rounded-lg bg-[#0f172a] border border-[#1e293b] text-xs flex items-start justify-between gap-3"
              >
                <div className="flex items-start gap-2.5">
                  <span className="font-mono text-[10px] text-cyan-400 mt-0.5 whitespace-nowrap">
                    {entry.time}
                  </span>
                  <span className={`px-2 py-0.2 rounded text-[10px] font-bold mt-0.5 ${
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

                {entry.source === 'AI' && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 shrink-0">
                    AI
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      </section>

      {/* KILL SWITCH CONFIRMATION MODAL */}
      {showKillModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-[#180a0a] border border-rose-600 rounded-2xl p-5 max-w-sm w-full shadow-2xl text-center">
            <div className="text-3xl mb-2">🛑</div>
            <h4 className="font-bold text-white text-base mb-1">Emergency Kill Switch</h4>
            <p className="text-xs text-slate-300 mb-5 leading-relaxed">
              Are you sure? This will sell all open positions immediately at the current market price and terminate trading for the day.
            </p>
            <div className="flex items-center justify-center gap-3">
              <button
                onClick={() => setShowKillModal(false)}
                className="px-4 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmKill}
                className="px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold shadow-lg shadow-rose-950"
              >
                Yes, Kill Trading
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
