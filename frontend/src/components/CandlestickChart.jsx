import React, { useEffect, useRef, useState, useCallback } from 'react';
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  createSeriesMarkers,
  LineStyle,
  ColorType,
  CrosshairMode
} from 'lightweight-charts';

/**
 * Continuous Candlestick Chart:
 * - Slim, perfectly proportioned Candlesticks (green bullish, red bearish) with thin upper/lower wicks
 * - Visible right price axis (auto-scaling) and visible bottom time axis
 * - Prominent BUY Markers: ▲ BUY – AGENT 1 / AGENT 3 @ ₹Price (green upward triangle below bar)
 * - Prominent SELL Markers: ▼ SELL – AGENT 1 / AGENT 3 / STOP-LOSS @ ₹Price (red downward triangle above bar)
 * - Subtle HOLD Markers: Small discrete orange dot (shape: circle, size: 1, no repeated giant text)
 * - Indicator Toggles: Average Price (VWAP), Today's High (ORB H), Today's Low (ORB L), Safety Limit, HOLD Markers
 * - SVG Trade Connection Lines connecting BUY entry to SELL exit (green for profit, red for loss)
 * - Interactive click-to-inspect trade detail panel
 */
export default function CandlestickChart({
  candles = [],
  buyMarkers = [],
  sellMarkers = [],
  holdMarkers = [],
  tradeConnections = [],
  activeStopLoss = null,
  currentSimulatedTime = null,
  currentTimestamp = null,
  isReplaying = false,
  onSelectMarker,
  t = {},
  showVwap = true,
  setShowVwap,
  showOrbHigh = true,
  setShowOrbHigh,
  showOrbLow = true,
  setShowOrbLow,
  showStopLoss = true,
  setShowStopLoss,
  showHoldSignals = false,
  setShowHoldSignals
}) {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const vwapSeriesRef = useRef(null);
  const orbHighScoreRef = useRef(null);
  const orbLowScoreRef = useRef(null);
  const stopLossLineRef = useRef(null);
  const markersPrimitiveRef = useRef(null);

  // SVG Trade Connection Lines state & cursor X coordinate
  const [svgLines, setSvgLines] = useState([]);
  const [cursorX, setCursorX] = useState(null);

  // STEP 1 & STEP 5: Initialize Lightweight Charts instance
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const container = chartContainerRef.current;
    const initialWidth = container.clientWidth > 0 ? container.clientWidth : 800;

    const chart = createChart(container, {
      width: initialWidth,
      height: 380,
      layout: {
        background: { type: ColorType.Solid, color: '#111827' },
        textColor: '#94a3b8',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        visible: true,
        borderColor: '#334155',
        autoScale: true,
        scaleMargins: { top: 0.12, bottom: 0.12 },
      },
      timeScale: {
        visible: true,
        borderColor: '#334155',
        timeVisible: true,
        secondsVisible: false,
        barSpacing: 9, // Slimmer, thinner candle spacing
        minBarSpacing: 3,
        rightOffset: 12,
      },
    });

    console.log('[CandlestickChart] Chart initialized with dimensions:', initialWidth, 'x', 380);

    // 1. Candlestick Series (Lightweight Charts v5 API) with thin, clean wicks
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    // 2. Average Price Indicator (VWAP) (Purple dashed)
    const vwapSeries = chart.addSeries(LineSeries, {
      color: '#c084fc',
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      title: t?.toggleAveragePrice || 'Avg Price',
      priceLineVisible: false,
      lastValueVisible: false,
    });

    // 3. Today's High Indicator Line (Amber dashed)
    const orbHighScore = chart.addSeries(LineSeries, {
      color: '#fbbf24',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      title: t?.toggleTodaysHigh || "Today's High",
      priceLineVisible: false,
      lastValueVisible: false,
    });

    // 4. Today's Low Indicator Line (Amber dashed)
    const orbLowScore = chart.addSeries(LineSeries, {
      color: '#f59e0b',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      title: t?.toggleTodaysLow || "Today's Low",
      priceLineVisible: false,
      lastValueVisible: false,
    });

    // 5. Execution Markers Primitive
    const markersPrimitive = createSeriesMarkers(candleSeries, []);

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    vwapSeriesRef.current = vwapSeries;
    orbHighScoreRef.current = orbHighScore;
    orbLowScoreRef.current = orbLowScore;
    markersPrimitiveRef.current = markersPrimitive;

    // Responsive sizing via ResizeObserver
    const resizeObserver = new ResizeObserver((entries) => {
      if (!entries || !entries.length || !chartRef.current) return;
      const { width } = entries[0].contentRect;
      if (width > 0) {
        chartRef.current.applyOptions({ width });
      }
    });
    resizeObserver.observe(container);

    const handleWindowResize = () => {
      if (container && chartRef.current && container.clientWidth > 0) {
        chartRef.current.applyOptions({ width: container.clientWidth });
      }
    };
    window.addEventListener('resize', handleWindowResize);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', handleWindowResize);
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      vwapSeriesRef.current = null;
      orbHighScoreRef.current = null;
      orbLowScoreRef.current = null;
      markersPrimitiveRef.current = null;
    };
  }, []);

  // Sync indicator visibility with toggle props
  useEffect(() => {
    if (vwapSeriesRef.current) {
      vwapSeriesRef.current.applyOptions({ visible: !!showVwap });
    }
  }, [showVwap]);

  useEffect(() => {
    if (orbHighScoreRef.current) {
      orbHighScoreRef.current.applyOptions({ visible: !!showOrbHigh });
    }
  }, [showOrbHigh]);

  useEffect(() => {
    if (orbLowScoreRef.current) {
      orbLowScoreRef.current.applyOptions({ visible: !!showOrbLow });
    }
  }, [showOrbLow]);

  // STEP 3 & STEP 4: Update Data, Indicators, Stop-Loss and Prominent Markers
  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current) return;

    const container = chartContainerRef.current;
    const candleSeries = candleSeriesRef.current;
    const vwapSeries = vwapSeriesRef.current;
    const orbHighScore = orbHighScoreRef.current;
    const orbLowScore = orbLowScoreRef.current;
    const markersPrimitive = markersPrimitiveRef.current;

    const formattedCandles = [];
    const vwapPoints = [];
    const orbHighPoints = [];
    const orbLowPoints = [];
    const seenTimes = new Set();

    candles.forEach((c) => {
      if (!c) return;
      let tVal = typeof c.time === 'number' ? c.time : (typeof c.timestamp === 'number' ? c.timestamp : null);
      if (!tVal && typeof c.time === 'string' && c.time.includes(':')) {
        try {
          const today = c.date || new Date().toISOString().split('T')[0];
          tVal = Math.floor(new Date(`${today}T${c.time}:00+05:30`).getTime() / 1000);
        } catch (e) {
          tVal = null;
        }
      }
      if (!tVal || isNaN(tVal) || seenTimes.has(tVal)) return;

      const open = Number(c.open);
      const close = Number(c.close);
      let high = Number(c.high);
      let low = Number(c.low);

      if (!isFinite(open) || !isFinite(close) || !isFinite(high) || !isFinite(low) || open <= 0 || close <= 0) return;
      high = Math.max(high, open, close);
      low = Math.min(low, open, close);

      seenTimes.add(tVal);
      formattedCandles.push({ time: tVal, open, high, low, close });

      if (c.vwap !== undefined && c.vwap !== null && isFinite(Number(c.vwap))) {
        vwapPoints.push({ time: tVal, value: Number(c.vwap) });
      }
      if (c.orb_high !== undefined && c.orb_high !== null && isFinite(Number(c.orb_high))) {
        orbHighPoints.push({ time: tVal, value: Number(c.orb_high) });
      }
      if (c.orb_low !== undefined && c.orb_low !== null && isFinite(Number(c.orb_low))) {
        orbLowPoints.push({ time: tVal, value: Number(c.orb_low) });
      }
    });

    formattedCandles.sort((a, b) => a.time - b.time);
    vwapPoints.sort((a, b) => a.time - b.time);
    orbHighPoints.sort((a, b) => a.time - b.time);
    orbLowPoints.sort((a, b) => a.time - b.time);

    console.log({
      seriesExists: !!candleSeries,
      candleCount: formattedCandles.length,
      firstCandle: formattedCandles[0],
      lastCandle: formattedCandles[formattedCandles.length - 1],
      containerWidth: container?.clientWidth,
      containerHeight: container?.clientHeight
    });

    candleSeries.setData(formattedCandles);
    if (vwapSeries) vwapSeries.setData(vwapPoints);
    if (orbHighScore) orbHighScore.setData(orbHighPoints);
    if (orbLowScore) orbLowScore.setData(orbLowPoints);

    // Requirement B: Smart zoom & horizontal spacing so candles are thin, slim, and not stretched wide
    if (formattedCandles.length >= 30) {
      chartRef.current.timeScale().fitContent();
    } else if (formattedCandles.length > 0) {
      chartRef.current.timeScale().applyOptions({
        barSpacing: 10,
        rightOffset: 12,
      });
      chartRef.current.timeScale().scrollToRealTime();
    }

    // Active Safety Limit / Stop-Loss Line
    if (stopLossLineRef.current) {
      candleSeries.removePriceLine(stopLossLineRef.current);
      stopLossLineRef.current = null;
    }
    if (showStopLoss && activeStopLoss && activeStopLoss > 0) {
      stopLossLineRef.current = candleSeries.createPriceLine({
        price: activeStopLoss,
        color: '#f43f5e',
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: `${t?.stopLossTag || 'SAFETY LIMIT'}: ₹${activeStopLoss.toFixed(2)}`
      });
    }

    // -------------------------------------------------------------
    // Requirement A & F: Prominent Visual Signals on Chart
    // - BUY: Green upward triangle (arrowUp) with label ▲ BUY – AGENT 1 / AGENT 3 @ ₹Price
    // - SELL: Red downward triangle (arrowDown) with label ▼ SELL – AGENT 1 / AGENT 3 / STOP-LOSS @ ₹Price
    // - HOLD: Small discrete orange dot (shape: circle, size: 1, text: '') — NO GIANT REPEATED TEXT
    // -------------------------------------------------------------
    const formattedMarkers = [];

    // Buy Markers (belowBar, green arrowUp, prominent label with responsible agent)
    buyMarkers.forEach((m) => {
      const tVal = typeof m.time === 'number' ? m.time : (typeof m.timestamp === 'number' ? m.timestamp : null);
      if (tVal && seenTimes.has(tVal)) {
        const isAgent3 = (m.agent_name || m.agent_tag || '').includes('Agent 3') || (m.agent_tag || '').includes('Reversion');
        const agentName = isAgent3 ? 'AGENT 3' : 'AGENT 1';
        const priceStr = m.price ? ` @ ₹${Number(m.price).toFixed(2)}` : '';
        formattedMarkers.push({
          time: tVal,
          position: 'belowBar',
          color: '#10b981',
          shape: 'arrowUp',
          text: `▲ BUY – ${agentName}${priceStr}`,
          size: 2,
          id: m.id || `buy-${tVal}`
        });
      }
    });

    // Sell Markers (aboveBar, red arrowDown, prominent label with responsible agent)
    sellMarkers.forEach((m) => {
      const tVal = typeof m.time === 'number' ? m.time : (typeof m.timestamp === 'number' ? m.timestamp : null);
      if (tVal && seenTimes.has(tVal)) {
        let exitAgent = 'AGENT 1';
        if ((m.reason || m.agent_name || '').toLowerCase().includes('stop loss') || (m.reason || '').toLowerCase().includes('stop-loss')) {
          exitAgent = 'STOP-LOSS';
        } else if ((m.agent_name || m.agent_tag || '').includes('Agent 3') || (m.reason || '').includes('Agent 3') || (m.reason || '').includes('reversion')) {
          exitAgent = 'AGENT 3';
        } else if ((m.agent_name || m.agent_tag || '').includes('Agent 1') || (m.reason || '').includes('Agent 1') || (m.reason || '').includes('ORB') || (m.reason || '').includes('trailing')) {
          exitAgent = 'AGENT 1';
        } else {
          exitAgent = 'RISK';
        }

        const pnlStr = (m.pnl !== null && m.pnl !== undefined)
          ? ` (${m.pnl >= 0 ? '+' : ''}₹${Number(m.pnl).toFixed(0)})`
          : (m.price ? ` @ ₹${Number(m.price).toFixed(2)}` : '');

        formattedMarkers.push({
          time: tVal,
          position: 'aboveBar',
          color: '#ef4444',
          shape: 'arrowDown',
          text: `▼ SELL – ${exitAgent}${pnlStr}`,
          size: 2,
          id: m.id || `sell-${tVal}`
        });
      }
    });

    // Requirement C: Subtle HOLD Markers — Small discrete orange circle, NO GIANT TEXT
    if (showHoldSignals && holdMarkers && holdMarkers.length > 0) {
      holdMarkers.forEach((m) => {
        const tVal = typeof m.time === 'number' ? m.time : (typeof m.timestamp === 'number' ? m.timestamp : null);
        if (tVal && seenTimes.has(tVal)) {
          formattedMarkers.push({
            time: tVal,
            position: 'belowBar',
            color: '#f59e0b',
            shape: 'circle',
            text: '', // Empty text: small discrete dot to eliminate visual clutter!
            size: 1,
            id: m.id || `hold-${tVal}`
          });
        }
      });
    }

    formattedMarkers.sort((a, b) => a.time - b.time);
    if (markersPrimitiveRef.current) {
      markersPrimitiveRef.current.setMarkers(formattedMarkers);
    }
  }, [candles, buyMarkers, sellMarkers, holdMarkers, activeStopLoss, showVwap, showOrbHigh, showOrbLow, showStopLoss, showHoldSignals, t]);

  // Update Trade Connection Lines & Cursor coordinate
  const updateOverlays = useCallback(() => {
    if (!chartRef.current || !candleSeriesRef.current) return;

    const chart = chartRef.current;
    const series = candleSeriesRef.current;
    const timeScale = chart.timeScale();

    // 1. Requirement G: Trade Connection Lines
    if (tradeConnections.length) {
      const lines = [];
      tradeConnections.forEach((conn) => {
        const tBuy = typeof conn.entry_timestamp === 'number' ? conn.entry_timestamp : null;
        const tSell = typeof conn.exit_timestamp === 'number' ? conn.exit_timestamp : null;
        if (!tBuy || !tSell) return;

        const x1 = timeScale.timeToCoordinate(tBuy);
        const y1 = series.priceToCoordinate(conn.entry_price);
        const x2 = timeScale.timeToCoordinate(tSell);
        const y2 = series.priceToCoordinate(conn.exit_price);

        if (x1 !== null && y1 !== null && x2 !== null && y2 !== null) {
          lines.push({
            id: conn.trade_id || `${tBuy}-${tSell}`,
            x1,
            y1,
            x2,
            y2,
            pnl: conn.pnl,
            isProfit: (conn.pnl || 0) >= 0,
            agent: conn.agent_name || conn.agent_tag || 'Agent 1'
          });
        }
      });
      setSvgLines(lines);
    } else {
      setSvgLines([]);
    }

    // 2. Replay cursor coordinate
    if (currentTimestamp && typeof currentTimestamp === 'number') {
      const cx = timeScale.timeToCoordinate(currentTimestamp);
      setCursorX(cx);
    } else {
      setCursorX(null);
    }
  }, [tradeConnections, currentTimestamp]);

  useEffect(() => {
    if (!chartRef.current) return;
    const timeScale = chartRef.current.timeScale();
    timeScale.subscribeVisibleTimeRangeChange(updateOverlays);
    updateOverlays();

    return () => {
      if (chartRef.current) {
        timeScale.unsubscribeVisibleTimeRangeChange(updateOverlays);
      }
    };
  }, [updateOverlays]);

  // Click on chart to inspect nearest trade marker
  useEffect(() => {
    if (!chartRef.current) return;
    const chart = chartRef.current;

    const handleClick = (param) => {
      if (!param || !param.time || !onSelectMarker) return;
      const clickedTime = param.time;

      const matchBuy = buyMarkers.find((m) => {
        const tVal = typeof m.time === 'number' ? m.time : (typeof m.timestamp === 'number' ? m.timestamp : null);
        return tVal === clickedTime;
      });
      if (matchBuy) {
        onSelectMarker({ ...matchBuy, action: 'BUY' });
        return;
      }

      const matchSell = sellMarkers.find((m) => {
        const tVal = typeof m.time === 'number' ? m.time : (typeof m.timestamp === 'number' ? m.timestamp : null);
        return tVal === clickedTime;
      });
      if (matchSell) {
        onSelectMarker({ ...matchSell, action: 'SELL' });
        return;
      }

      if (holdMarkers && holdMarkers.length > 0) {
        const matchHold = holdMarkers.find((m) => {
          const tVal = typeof m.time === 'number' ? m.time : (typeof m.timestamp === 'number' ? m.timestamp : null);
          return tVal === clickedTime;
        });
        if (matchHold) {
          onSelectMarker({ ...matchHold, action: 'HOLD' });
        }
      }
    };

    chart.subscribeClick(handleClick);
    return () => chart.unsubscribeClick(handleClick);
  }, [buyMarkers, sellMarkers, holdMarkers, onSelectMarker]);

  const allExecutedMarkers = [...buyMarkers, ...sellMarkers].sort((a, b) => {
    const tA = typeof a.time === 'number' ? a.time : (typeof a.timestamp === 'number' ? a.timestamp : 0);
    const tB = typeof b.time === 'number' ? b.time : (typeof b.timestamp === 'number' ? b.timestamp : 0);
    return tA - tB;
  });

  return (
    <div className="flex flex-col gap-2">
      {/* Optional Indicators & Toggles Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 bg-[#0d1424] px-3 py-2 rounded-lg border border-[#1e293b] text-xs">
        {/* Candle Colors Legend */}
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
            <span className="w-2.5 h-3 bg-emerald-500 rounded-[1px] inline-block shadow-sm shadow-emerald-500/50"></span>
            {t?.bullishLabel || 'Price Going Up'}
          </span>
          <span className="flex items-center gap-1.5 text-rose-400 font-medium">
            <span className="w-2.5 h-3 bg-rose-500 rounded-[1px] inline-block shadow-sm shadow-rose-500/50"></span>
            {t?.bearishLabel || 'Price Going Down'}
          </span>
        </div>

        {/* Indicator Toggles */}
        <div className="flex flex-wrap items-center gap-2">
          {setShowVwap && (
            <button
              type="button"
              onClick={() => setShowVwap(!showVwap)}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold border transition flex items-center gap-1 ${
                showVwap
                  ? 'bg-purple-950/80 text-purple-300 border-purple-500 shadow-sm shadow-purple-900/50'
                  : 'bg-[#1e293b]/60 text-slate-500 border-slate-700 hover:text-slate-300'
              }`}
              title="Toggle Average Price Line (VWAP)"
            >
              <span className={`w-2 h-2 rounded-full ${showVwap ? 'bg-purple-400' : 'bg-slate-600'}`}></span>
              {t?.toggleAveragePrice || 'Average Price'}
            </button>
          )}

          {setShowOrbHigh && (
            <button
              type="button"
              onClick={() => setShowOrbHigh(!showOrbHigh)}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold border transition flex items-center gap-1 ${
                showOrbHigh
                  ? 'bg-amber-950/80 text-amber-300 border-amber-500 shadow-sm shadow-amber-900/50'
                  : 'bg-[#1e293b]/60 text-slate-500 border-slate-700 hover:text-slate-300'
              }`}
              title="Toggle Today's High Line"
            >
              <span className={`w-2 h-2 rounded-full ${showOrbHigh ? 'bg-amber-400' : 'bg-slate-600'}`}></span>
              {t?.toggleTodaysHigh || "Today's High"}
            </button>
          )}

          {setShowOrbLow && (
            <button
              type="button"
              onClick={() => setShowOrbLow(!showOrbLow)}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold border transition flex items-center gap-1 ${
                showOrbLow
                  ? 'bg-amber-950/80 text-amber-300 border-amber-600 shadow-sm shadow-amber-900/50'
                  : 'bg-[#1e293b]/60 text-slate-500 border-slate-700 hover:text-slate-300'
              }`}
              title="Toggle Today's Low Line"
            >
              <span className={`w-2 h-2 rounded-full ${showOrbLow ? 'bg-amber-500' : 'bg-slate-600'}`}></span>
              {t?.toggleTodaysLow || "Today's Low"}
            </button>
          )}

          {setShowStopLoss && activeStopLoss && activeStopLoss > 0 && (
            <button
              type="button"
              onClick={() => setShowStopLoss(!showStopLoss)}
              className={`px-2 py-0.5 rounded text-[11px] font-semibold border transition flex items-center gap-1 ${
                showStopLoss
                  ? 'bg-rose-950/80 text-rose-300 border-rose-500 shadow-sm shadow-rose-900/50'
                  : 'bg-[#1e293b]/60 text-slate-500 border-slate-700 hover:text-slate-300'
              }`}
              title="Toggle Safety Limit (Stop-Loss Line)"
            >
              <span className={`w-2 h-2 rounded-full ${showStopLoss ? 'bg-rose-400' : 'bg-slate-600'}`}></span>
              {t?.stopLossTag || 'Safety Limit'}: ₹{activeStopLoss.toFixed(2)}
            </button>
          )}

          {/* Requirement C: Toggle HOLD Markers */}
          {setShowHoldSignals && (
            <button
              type="button"
              onClick={() => setShowHoldSignals(!showHoldSignals)}
              className={`px-2.5 py-0.5 rounded text-[11px] font-semibold border transition flex items-center gap-1.5 ${
                showHoldSignals
                  ? 'bg-amber-950 text-amber-300 border-amber-500 shadow-sm shadow-amber-950'
                  : 'bg-[#1e293b]/60 text-slate-400 border-slate-700 hover:text-slate-200'
              }`}
              title="Toggle discrete HOLD dots on evaluated bars"
            >
              <span className={`w-2 h-2 rounded-full ${showHoldSignals ? 'bg-amber-400 shadow-sm shadow-amber-400' : 'bg-slate-600'}`}></span>
              <span>{showHoldSignals ? 'Hide HOLD Dots' : 'Show HOLD Dots'}</span>
            </button>
          )}
        </div>
      </div>

      {/* Chart Canvas & SVG Connection Lines Layer */}
      <div className="relative w-full h-[380px] rounded-lg overflow-hidden border border-[#1e293b] bg-[#111827]">
        {/* Lightweight Charts Canvas Container */}
        <div ref={chartContainerRef} className="w-full h-[380px]" style={{ minHeight: '380px' }} />

        {/* SVG Trade Connection Lines & Vertical Replay Cursor Overlay */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
          {/* Vertical Replay Cursor */}
          {cursorX !== null && cursorX >= 0 && (
            <g>
              <line
                x1={cursorX}
                y1={0}
                x2={cursorX}
                y2={380}
                stroke="#06b6d4"
                strokeWidth={1.5}
                strokeDasharray="3 3"
                opacity={0.85}
              />
              <g transform={`translate(${Math.max(10, Math.min(cursorX - 25, (chartContainerRef.current?.clientWidth || 600) - 60))}, 6)`}>
                <rect width={52} height={18} rx={3} fill="#0891b2" opacity={0.9} />
                <text x={26} y={13} textAnchor="middle" fill="#ffffff" fontSize={10} fontFamily="monospace" fontWeight="bold">
                  {currentSimulatedTime || 'LIVE'}
                </text>
              </g>
            </g>
          )}

          {/* Connected Trade Lines */}
          {svgLines.map((line) => (
            <g key={line.id}>
              <line
                x1={line.x1}
                y1={line.y1}
                x2={line.x2}
                y2={line.y2}
                stroke={line.isProfit ? '#10b981' : '#ef4444'}
                strokeWidth={1.5}
                strokeDasharray="4 3"
                opacity={0.8}
              />
              <circle cx={line.x1} cy={line.y1} r={3} fill="#10b981" />
              <circle cx={line.x2} cy={line.y2} r={3} fill="#ef4444" />
            </g>
          ))}
        </svg>
      </div>

      {/* Interactive Trade Marker Inspector Bar */}
      <div className="bg-[#0f172a] border border-[#1e293b] rounded-lg p-2.5 flex flex-wrap items-center justify-between gap-2 text-xs font-mono">
        <div className="flex items-center gap-2">
          <span className="text-cyan-400 text-[11px] font-bold">
            🔍 {t?.tradeInspectorTitle || 'TRADE SIGNAL INSPECTOR'}:
          </span>
          {allExecutedMarkers.length === 0 ? (
            <span className="text-slate-500 text-[11px]">
              {t?.noTradesYet || 'No executed trades yet. The system is scanning market conditions.'}
            </span>
          ) : (
            <div className="flex flex-wrap items-center gap-1.5 max-h-16 overflow-y-auto">
              {allExecutedMarkers.map((m) => {
                const isBuy = m.action === 'BUY';
                const timeLabel = m.time_str || m.time;
                const isAgent3 = (m.agent_name || m.agent_tag || '').includes('Agent 3') || (m.agent_tag || '').includes('Reversion');
                const badge = isBuy ? (isAgent3 ? 'A3' : 'A1') : '';
                return (
                  <button
                    key={m.id || `${m.time}-${m.action}`}
                    onClick={() => onSelectMarker && onSelectMarker(m)}
                    className={`px-2.5 py-1 rounded text-[11px] font-bold border transition flex items-center gap-1 shadow-sm ${
                      isBuy
                        ? 'bg-emerald-950 text-emerald-300 border-emerald-600 hover:bg-emerald-900 shadow-emerald-950/50'
                        : 'bg-rose-950 text-rose-300 border-rose-600 hover:bg-rose-900 shadow-rose-950/50'
                    }`}
                    title="Click to view full execution details"
                  >
                    <span>{isBuy ? `▲ BUY [${badge}]` : '▼ SELL'}</span>
                    <span className="text-slate-300">{timeLabel}</span>
                    <span className="text-white">₹{Number(m.price).toFixed(2)}</span>
                    {m.pnl !== null && m.pnl !== undefined && (
                      <span className={m.pnl >= 0 ? 'text-emerald-400 font-extrabold' : 'text-rose-400 font-extrabold'}>
                        ({m.pnl >= 0 ? '+' : ''}₹{Number(m.pnl).toFixed(2)})
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        <div className="text-[10px] text-slate-400 hidden sm:inline">
          {t?.inspectorTip || '💡 Click any BUY or SELL arrow on the chart to inspect execution details.'}
        </div>
      </div>
    </div>
  );
}
