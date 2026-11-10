import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  createSeriesMarkers,
  LineStyle,
  ColorType,
  CrosshairMode
} from 'lightweight-charts';

/**
 * Enhanced Continuous Candlestick Chart:
 * - Slim, crisp candlesticks with thin wicks
 * - Live Indicators Dropdown (fx Indicators) supporting all 10 technical strategies:
 *    1. EMA 9 (Momentum) - Blue
 *    2. EMA 21 (Pullback / Cross) - Pink
 *    3. EMA 50 (Intermediate Trend) - Amber
 *    4. EMA 200 (Macro Trend) - Purple
 *    5. VWAP (Volume Weighted Avg Price) - Dashed Violet
 *    6. Bollinger Bands (Upper, Mid, Lower) - Cyan / Teal
 *    7. Donchian Channels (20-bar High & Low) - Emerald
 *    8. Supertrend (ATR Dynamic Trend) - Lime
 *    9. Volume Bars (Color-coded histogram at base of main chart)
 *    10. RSI 14 Sub-Chart (Synchronized sub-pane with 70/50/30 levels)
 *    11. MACD Line & Signal
 *    12. Stochastic %K & %D
 *    13. Today's High & Low (ORB High/Low)
 *    14. Active Stop-Loss Line
 * - Groww / TradingView Legend (MA 9 close, MA 21 close, Volume, RSI 14)
 * - Floating BUY / SELL Execution Badges
 * - SVG Trade Connection Lines connecting BUY entry to SELL exit
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
  showVwap = false,
  setShowVwap,
  showOrbHigh = false,
  setShowOrbHigh,
  showOrbLow = false,
  setShowOrbLow,
  showStopLoss = true,
  setShowStopLoss,
  showHoldSignals = false,
  setShowHoldSignals,
  selectedTimeframe = '5m',
  onSelectTimeframe,
  simulationSpeed = '20x',
  onSelectSpeed,
  isLiveMode = false,
  onExecuteOrder = null
}) {
  const chartContainerRef = useRef(null);
  const rsiContainerRef = useRef(null);
  const chartRef = useRef(null);
  const rsiChartRef = useRef(null);

  // Series refs
  const candleSeriesRef = useRef(null);
  const volumeSeriesRef = useRef(null);
  const ema9SeriesRef = useRef(null);
  const ema21SeriesRef = useRef(null);
  const ema50SeriesRef = useRef(null);
  const ema200SeriesRef = useRef(null);
  const vwapSeriesRef = useRef(null);
  const bbUpperSeriesRef = useRef(null);
  const bbLowerSeriesRef = useRef(null);
  const bbMidSeriesRef = useRef(null);
  const donchianHighSeriesRef = useRef(null);
  const donchianLowSeriesRef = useRef(null);
  const supertrendSeriesRef = useRef(null);
  const orbHighScoreRef = useRef(null);
  const orbLowScoreRef = useRef(null);
  const macdLineSeriesRef = useRef(null);
  const macdSignalSeriesRef = useRef(null);
  const stochKSeriesRef = useRef(null);
  const stochDSeriesRef = useRef(null);
  const stopLossLineRef = useRef(null);
  const markersPrimitiveRef = useRef(null);
  const rsiSeriesRef = useRef(null);

  // Indicators State - Default matches screenshot (EMA 9, EMA 21, Volume, RSI 14)
  const [indicators, setIndicators] = useState({
    ema9: true,
    ema21: true,
    ema50: false,
    ema200: false,
    vwap: false,
    bb: false,
    donchian: false,
    supertrend: false,
    volume: true,
    rsi: true,
    macd: false,
    stoch: false,
    orb: false,
    stopLoss: true,
    holdSignals: false
  });

  const [showIndicatorsMenu, setShowIndicatorsMenu] = useState(false);
  const [svgLines, setSvgLines] = useState([]);
  const [cursorX, setCursorX] = useState(null);

  const toggleIndicator = (key) => {
    setIndicators((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      if (key === 'vwap' && setShowVwap) setShowVwap(next[key]);
      if (key === 'orb' && setShowOrbHigh && setShowOrbLow) {
        setShowOrbHigh(next[key]);
        setShowOrbLow(next[key]);
      }
      if (key === 'stopLoss' && setShowStopLoss) setShowStopLoss(next[key]);
      if (key === 'holdSignals' && setShowHoldSignals) setShowHoldSignals(next[key]);
      return next;
    });
  };

  const applyPreset = (preset) => {
    if (preset === 'default') {
      setIndicators({
        ema9: true,
        ema21: true,
        ema50: false,
        ema200: false,
        vwap: false,
        bb: false,
        donchian: false,
        supertrend: false,
        volume: true,
        rsi: true,
        macd: false,
        stoch: false,
        orb: false,
        stopLoss: true,
        holdSignals: false
      });
    } else if (preset === 'all') {
      setIndicators({
        ema9: true,
        ema21: true,
        ema50: true,
        ema200: true,
        vwap: true,
        bb: true,
        donchian: true,
        supertrend: true,
        volume: true,
        rsi: true,
        macd: true,
        stoch: true,
        orb: true,
        stopLoss: true,
        holdSignals: true
      });
    } else if (preset === 'minimal') {
      setIndicators({
        ema9: false,
        ema21: false,
        ema50: false,
        ema200: false,
        vwap: false,
        bb: false,
        donchian: false,
        supertrend: false,
        volume: true,
        rsi: false,
        macd: false,
        stoch: false,
        orb: false,
        stopLoss: true,
        holdSignals: false
      });
    }
  };

  // Latest candle values for top-left legend
  const latestCandle = candles && candles.length > 0 ? candles[candles.length - 1] : null;
  const latestPrice = latestCandle?.close || 0;
  const latestEma9 = latestCandle?.ema9;
  const latestEma21 = latestCandle?.ema21;
  const latestVolume = latestCandle?.volume;
  const latestRsi = latestCandle?.rsi14;

  const activeIndicatorsCount = useMemo(() => {
    return Object.values(indicators).filter(Boolean).length;
  }, [indicators]);

  // -------------------------------------------------------------
  // INITIALIZE MAIN CHART
  // -------------------------------------------------------------
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
        scaleMargins: { top: 0.12, bottom: 0.22 },
      },
      timeScale: {
        visible: !indicators.rsi, // Hide main time scale when RSI sub-pane is active
        borderColor: '#334155',
        timeVisible: true,
        secondsVisible: false,
        barSpacing: 9,
        minBarSpacing: 3,
        rightOffset: 12,
      },
    });

    // 1. Candlestick Series
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#10b981',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#10b981',
      wickDownColor: '#ef4444',
    });

    // 2. Volume Histogram Series (scaled at bottom 20%)
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
      visible: false,
    });

    // 3. Moving Averages Series (EMA 9, EMA 21, EMA 50, EMA 200)
    const ema9Series = chart.addSeries(LineSeries, {
      color: '#38bdf8', // Light blue (matching screenshot)
      lineWidth: 1.5,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const ema21Series = chart.addSeries(LineSeries, {
      color: '#f43f5e', // Rose/Magenta (matching screenshot)
      lineWidth: 1.5,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const ema50Series = chart.addSeries(LineSeries, {
      color: '#f59e0b', // Amber/Orange
      lineWidth: 1.5,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const ema200Series = chart.addSeries(LineSeries, {
      color: '#a855f7', // Purple
      lineWidth: 1.5,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    // 4. VWAP Series
    const vwapSeries = chart.addSeries(LineSeries, {
      color: '#c084fc',
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    // 5. Bollinger Bands (Upper, Lower, Mid)
    const bbUpperSeries = chart.addSeries(LineSeries, {
      color: '#06b6d4',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const bbLowerSeries = chart.addSeries(LineSeries, {
      color: '#06b6d4',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const bbMidSeries = chart.addSeries(LineSeries, {
      color: '#14b8a6',
      lineWidth: 1,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    // 6. Donchian Channels (High, Low)
    const donchianHighSeries = chart.addSeries(LineSeries, {
      color: '#10b981',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const donchianLowSeries = chart.addSeries(LineSeries, {
      color: '#10b981',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    // 7. Supertrend Series
    const supertrendSeries = chart.addSeries(LineSeries, {
      color: '#84cc16',
      lineWidth: 1.5,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    // 8. ORB High / Low
    const orbHighScore = chart.addSeries(LineSeries, {
      color: '#fbbf24',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const orbLowScore = chart.addSeries(LineSeries, {
      color: '#f59e0b',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
    });

    // 9. MACD Line & Signal
    const macdLineSeries = chart.addSeries(LineSeries, {
      color: '#38bdf8',
      lineWidth: 1,
      priceScaleId: 'macd',
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const macdSignalSeries = chart.addSeries(LineSeries, {
      color: '#f59e0b',
      lineWidth: 1,
      priceScaleId: 'macd',
      priceLineVisible: false,
      lastValueVisible: false,
    });
    chart.priceScale('macd').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
      visible: false,
    });

    // 10. Stochastic %K & %D
    const stochKSeries = chart.addSeries(LineSeries, {
      color: '#06b6d4',
      lineWidth: 1,
      priceScaleId: 'stoch',
      priceLineVisible: false,
      lastValueVisible: false,
    });
    const stochDSeries = chart.addSeries(LineSeries, {
      color: '#f43f5e',
      lineWidth: 1,
      priceScaleId: 'stoch',
      priceLineVisible: false,
      lastValueVisible: false,
    });
    chart.priceScale('stoch').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
      visible: false,
    });

    // Markers Primitive
    const markersPrimitive = createSeriesMarkers(candleSeries, []);

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;
    ema9SeriesRef.current = ema9Series;
    ema21SeriesRef.current = ema21Series;
    ema50SeriesRef.current = ema50Series;
    ema200SeriesRef.current = ema200Series;
    vwapSeriesRef.current = vwapSeries;
    bbUpperSeriesRef.current = bbUpperSeries;
    bbLowerSeriesRef.current = bbLowerSeries;
    bbMidSeriesRef.current = bbMidSeries;
    donchianHighSeriesRef.current = donchianHighSeries;
    donchianLowSeriesRef.current = donchianLowSeries;
    supertrendSeriesRef.current = supertrendSeries;
    orbHighScoreRef.current = orbHighScore;
    orbLowScoreRef.current = orbLowScore;
    macdLineSeriesRef.current = macdLineSeries;
    macdSignalSeriesRef.current = macdSignalSeries;
    stochKSeriesRef.current = stochKSeries;
    stochDSeriesRef.current = stochDSeries;
    markersPrimitiveRef.current = markersPrimitive;

    // Resize Observer
    const resizeObserver = new ResizeObserver((entries) => {
      if (!entries || !entries.length || !chartRef.current) return;
      const { width } = entries[0].contentRect;
      if (width > 0) {
        chartRef.current.applyOptions({ width });
        if (rsiChartRef.current) {
          rsiChartRef.current.applyOptions({ width });
        }
      }
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      volumeSeriesRef.current = null;
    };
  }, []);

  // -------------------------------------------------------------
  // INITIALIZE / TEARDOWN RSI 14 SUB-PANE
  // -------------------------------------------------------------
  useEffect(() => {
    if (!indicators.rsi || !rsiContainerRef.current) {
      if (rsiChartRef.current) {
        rsiChartRef.current.remove();
        rsiChartRef.current = null;
        rsiSeriesRef.current = null;
      }
      if (chartRef.current) {
        chartRef.current.timeScale().applyOptions({ visible: true });
      }
      return;
    }

    // Hide main chart time scale when RSI sub-pane is active
    if (chartRef.current) {
      chartRef.current.timeScale().applyOptions({ visible: false });
    }

    const container = rsiContainerRef.current;
    const initialWidth = container.clientWidth > 0 ? container.clientWidth : 800;

    const rsiChart = createChart(container, {
      width: initialWidth,
      height: 110,
      layout: {
        background: { type: ColorType.Solid, color: '#0d121c' },
        textColor: '#94a3b8',
        fontSize: 10,
      },
      grid: {
        vertLines: { color: '#161f30' },
        horzLines: { color: '#161f30' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        visible: true,
        borderColor: '#334155',
        autoScale: false,
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        visible: true,
        borderColor: '#334155',
        timeVisible: true,
        secondsVisible: false,
        barSpacing: 9,
        minBarSpacing: 3,
        rightOffset: 12,
      },
    });

    const rsiSeries = rsiChart.addSeries(LineSeries, {
      color: '#a855f7', // Purple line matching screenshot
      lineWidth: 1.5,
      priceLineVisible: false,
      lastValueVisible: true,
      autoscaleInfoProvider: () => ({
        priceRange: {
          minValue: 20,
          maxValue: 80,
        },
      }),
    });

    // Reference levels: 70 (Overbought), 50 (Mid), 30 (Oversold)
    rsiSeries.createPriceLine({
      price: 70,
      color: '#ef444488',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: '70',
    });
    rsiSeries.createPriceLine({
      price: 50,
      color: '#64748b66',
      lineWidth: 1,
      lineStyle: LineStyle.Dotted,
      axisLabelVisible: true,
      title: '50',
    });
    rsiSeries.createPriceLine({
      price: 30,
      color: '#10b98188',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: '30',
    });

    rsiChartRef.current = rsiChart;
    rsiSeriesRef.current = rsiSeries;

    // Synchronize time scales
    if (chartRef.current) {
      const mainTimeScale = chartRef.current.timeScale();
      const rsiTimeScale = rsiChart.timeScale();

      mainTimeScale.subscribeVisibleLogicalRangeChange((range) => {
        if (range && rsiChartRef.current) {
          rsiTimeScale.setVisibleLogicalRange(range);
        }
      });
      rsiTimeScale.subscribeVisibleLogicalRangeChange((range) => {
        if (range && chartRef.current) {
          mainTimeScale.setVisibleLogicalRange(range);
        }
      });
    }

    return () => {
      rsiChart.remove();
      rsiChartRef.current = null;
      rsiSeriesRef.current = null;
    };
  }, [indicators.rsi]);

  // -------------------------------------------------------------
  // UPDATE VISIBILITY OF SERIES BASED ON INDICATOR TOGGLES
  // -------------------------------------------------------------
  useEffect(() => {
    if (ema9SeriesRef.current) ema9SeriesRef.current.applyOptions({ visible: !!indicators.ema9 });
    if (ema21SeriesRef.current) ema21SeriesRef.current.applyOptions({ visible: !!indicators.ema21 });
    if (ema50SeriesRef.current) ema50SeriesRef.current.applyOptions({ visible: !!indicators.ema50 });
    if (ema200SeriesRef.current) ema200SeriesRef.current.applyOptions({ visible: !!indicators.ema200 });
    if (vwapSeriesRef.current) vwapSeriesRef.current.applyOptions({ visible: !!indicators.vwap });
    if (bbUpperSeriesRef.current) bbUpperSeriesRef.current.applyOptions({ visible: !!indicators.bb });
    if (bbLowerSeriesRef.current) bbLowerSeriesRef.current.applyOptions({ visible: !!indicators.bb });
    if (bbMidSeriesRef.current) bbMidSeriesRef.current.applyOptions({ visible: !!indicators.bb });
    if (donchianHighSeriesRef.current) donchianHighSeriesRef.current.applyOptions({ visible: !!indicators.donchian });
    if (donchianLowSeriesRef.current) donchianLowSeriesRef.current.applyOptions({ visible: !!indicators.donchian });
    if (supertrendSeriesRef.current) supertrendSeriesRef.current.applyOptions({ visible: !!indicators.supertrend });
    if (orbHighScoreRef.current) orbHighScoreRef.current.applyOptions({ visible: !!indicators.orb });
    if (orbLowScoreRef.current) orbLowScoreRef.current.applyOptions({ visible: !!indicators.orb });
    if (volumeSeriesRef.current) volumeSeriesRef.current.applyOptions({ visible: !!indicators.volume });
    if (macdLineSeriesRef.current) macdLineSeriesRef.current.applyOptions({ visible: !!indicators.macd });
    if (macdSignalSeriesRef.current) macdSignalSeriesRef.current.applyOptions({ visible: !!indicators.macd });
    if (stochKSeriesRef.current) stochKSeriesRef.current.applyOptions({ visible: !!indicators.stoch });
    if (stochDSeriesRef.current) stochDSeriesRef.current.applyOptions({ visible: !!indicators.stoch });
  }, [indicators]);

  // -------------------------------------------------------------
  // UPDATE CANDLESTICK & INDICATOR DATA
  // -------------------------------------------------------------
  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current) return;

    const formattedCandles = [];
    const volumePoints = [];
    const ema9Points = [];
    const ema21Points = [];
    const ema50Points = [];
    const ema200Points = [];
    const vwapPoints = [];
    const bbUpperPoints = [];
    const bbLowerPoints = [];
    const bbMidPoints = [];
    const donchianHighPoints = [];
    const donchianLowPoints = [];
    const supertrendPoints = [];
    const orbHighPoints = [];
    const orbLowPoints = [];
    const rsiPoints = [];
    const macdLinePoints = [];
    const macdSignalPoints = [];
    const stochKPoints = [];
    const stochDPoints = [];
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

      // Volume bar color-coded
      const vol = Number(c.volume || 0);
      volumePoints.push({
        time: tVal,
        value: vol,
        color: close >= open ? '#10b98166' : '#ef444466',
      });

      if (c.ema9 !== undefined && isFinite(Number(c.ema9))) ema9Points.push({ time: tVal, value: Number(c.ema9) });
      if (c.ema21 !== undefined && isFinite(Number(c.ema21))) ema21Points.push({ time: tVal, value: Number(c.ema21) });
      if (c.ema50 !== undefined && isFinite(Number(c.ema50))) ema50Points.push({ time: tVal, value: Number(c.ema50) });
      if (c.ema200 !== undefined && isFinite(Number(c.ema200))) ema200Points.push({ time: tVal, value: Number(c.ema200) });
      if (c.vwap !== undefined && isFinite(Number(c.vwap))) vwapPoints.push({ time: tVal, value: Number(c.vwap) });
      if (c.bb_upper !== undefined && isFinite(Number(c.bb_upper))) bbUpperPoints.push({ time: tVal, value: Number(c.bb_upper) });
      if (c.bb_lower !== undefined && isFinite(Number(c.bb_lower))) bbLowerPoints.push({ time: tVal, value: Number(c.bb_lower) });
      if (c.bb_mid !== undefined && isFinite(Number(c.bb_mid))) bbMidPoints.push({ time: tVal, value: Number(c.bb_mid) });
      if (c.donchian_high !== undefined && isFinite(Number(c.donchian_high))) donchianHighPoints.push({ time: tVal, value: Number(c.donchian_high) });
      if (c.donchian_low !== undefined && isFinite(Number(c.donchian_low))) donchianLowPoints.push({ time: tVal, value: Number(c.donchian_low) });
      if (c.supertrend !== undefined && isFinite(Number(c.supertrend))) supertrendPoints.push({ time: tVal, value: Number(c.supertrend) });
      if (c.orb_high !== undefined && isFinite(Number(c.orb_high))) orbHighPoints.push({ time: tVal, value: Number(c.orb_high) });
      if (c.orb_low !== undefined && isFinite(Number(c.orb_low))) orbLowPoints.push({ time: tVal, value: Number(c.orb_low) });
      if (c.rsi14 !== undefined && isFinite(Number(c.rsi14))) rsiPoints.push({ time: tVal, value: Number(c.rsi14) });
      if (c.macd_line !== undefined && isFinite(Number(c.macd_line))) macdLinePoints.push({ time: tVal, value: Number(c.macd_line) });
      if (c.macd_signal !== undefined && isFinite(Number(c.macd_signal))) macdSignalPoints.push({ time: tVal, value: Number(c.macd_signal) });
      if (c.stoch_k !== undefined && isFinite(Number(c.stoch_k))) stochKPoints.push({ time: tVal, value: Number(c.stoch_k) });
      if (c.stoch_d !== undefined && isFinite(Number(c.stoch_d))) stochDPoints.push({ time: tVal, value: Number(c.stoch_d) });
    });

    const sortFn = (a, b) => a.time - b.time;
    formattedCandles.sort(sortFn);
    volumePoints.sort(sortFn);
    ema9Points.sort(sortFn);
    ema21Points.sort(sortFn);
    ema50Points.sort(sortFn);
    ema200Points.sort(sortFn);
    vwapPoints.sort(sortFn);
    bbUpperPoints.sort(sortFn);
    bbLowerPoints.sort(sortFn);
    bbMidPoints.sort(sortFn);
    donchianHighPoints.sort(sortFn);
    donchianLowPoints.sort(sortFn);
    supertrendPoints.sort(sortFn);
    orbHighPoints.sort(sortFn);
    orbLowPoints.sort(sortFn);
    rsiPoints.sort(sortFn);
    macdLinePoints.sort(sortFn);
    macdSignalPoints.sort(sortFn);
    stochKPoints.sort(sortFn);
    stochDPoints.sort(sortFn);

    candleSeriesRef.current.setData(formattedCandles);
    if (volumeSeriesRef.current) volumeSeriesRef.current.setData(volumePoints);
    if (ema9SeriesRef.current) ema9SeriesRef.current.setData(ema9Points);
    if (ema21SeriesRef.current) ema21SeriesRef.current.setData(ema21Points);
    if (ema50SeriesRef.current) ema50SeriesRef.current.setData(ema50Points);
    if (ema200SeriesRef.current) ema200SeriesRef.current.setData(ema200Points);
    if (vwapSeriesRef.current) vwapSeriesRef.current.setData(vwapPoints);
    if (bbUpperSeriesRef.current) bbUpperSeriesRef.current.setData(bbUpperPoints);
    if (bbLowerSeriesRef.current) bbLowerSeriesRef.current.setData(bbLowerPoints);
    if (bbMidSeriesRef.current) bbMidSeriesRef.current.setData(bbMidPoints);
    if (donchianHighSeriesRef.current) donchianHighSeriesRef.current.setData(donchianHighPoints);
    if (donchianLowSeriesRef.current) donchianLowSeriesRef.current.setData(donchianLowPoints);
    if (supertrendSeriesRef.current) supertrendSeriesRef.current.setData(supertrendPoints);
    if (orbHighScoreRef.current) orbHighScoreRef.current.setData(orbHighPoints);
    if (orbLowScoreRef.current) orbLowScoreRef.current.setData(orbLowPoints);
    if (macdLineSeriesRef.current) macdLineSeriesRef.current.setData(macdLinePoints);
    if (macdSignalSeriesRef.current) macdSignalSeriesRef.current.setData(macdSignalPoints);
    if (stochKSeriesRef.current) stochKSeriesRef.current.setData(stochKPoints);
    if (stochDSeriesRef.current) stochDSeriesRef.current.setData(stochDPoints);

    if (rsiSeriesRef.current) {
      rsiSeriesRef.current.setData(rsiPoints);
    }

    if (formattedCandles.length >= 30) {
      chartRef.current.timeScale().fitContent();
      if (rsiChartRef.current) rsiChartRef.current.timeScale().fitContent();
    } else if (formattedCandles.length > 0) {
      chartRef.current.timeScale().applyOptions({ barSpacing: 10, rightOffset: 12 });
      chartRef.current.timeScale().scrollToRealTime();
    }

    // Active Safety Limit / Stop-Loss Line
    if (stopLossLineRef.current) {
      candleSeriesRef.current.removePriceLine(stopLossLineRef.current);
      stopLossLineRef.current = null;
    }
    if (indicators.stopLoss && activeStopLoss && activeStopLoss > 0) {
      stopLossLineRef.current = candleSeriesRef.current.createPriceLine({
        price: activeStopLoss,
        color: '#f43f5e',
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: `${t?.stopLossTag || 'SAFETY LIMIT'}: ₹${activeStopLoss.toFixed(2)}`,
      });
    }

    // -------------------------------------------------------------
    // TRADE MARKERS (BUY, SELL, subtle HOLD)
    // -------------------------------------------------------------
    const formattedMarkers = [];

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
          id: m.id || `buy-${tVal}`,
        });
      }
    });

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

        const pnlStr = m.pnl !== null && m.pnl !== undefined
          ? ` (${m.pnl >= 0 ? '+' : ''}₹${Number(m.pnl).toFixed(0)})`
          : (m.price ? ` @ ₹${Number(m.price).toFixed(2)}` : '');

        formattedMarkers.push({
          time: tVal,
          position: 'aboveBar',
          color: '#ef4444',
          shape: 'arrowDown',
          text: `▼ SELL – ${exitAgent}${pnlStr}`,
          size: 2,
          id: m.id || `sell-${tVal}`,
        });
      }
    });

    if (indicators.holdSignals && holdMarkers && holdMarkers.length > 0) {
      holdMarkers.forEach((m) => {
        const tVal = typeof m.time === 'number' ? m.time : (typeof m.timestamp === 'number' ? m.timestamp : null);
        if (tVal && seenTimes.has(tVal)) {
          formattedMarkers.push({
            time: tVal,
            position: 'belowBar',
            color: '#f59e0b',
            shape: 'circle',
            text: '',
            size: 1,
            id: m.id || `hold-${tVal}`,
          });
        }
      });
    }

    formattedMarkers.sort(sortFn);
    if (markersPrimitiveRef.current) {
      markersPrimitiveRef.current.setMarkers(formattedMarkers);
    }
  }, [candles, buyMarkers, sellMarkers, holdMarkers, activeStopLoss, indicators, t]);

  // Update Trade Connection Lines & Cursor coordinate
  const updateOverlays = useCallback(() => {
    if (!chartRef.current || !candleSeriesRef.current) return;
    const chart = chartRef.current;
    const series = candleSeriesRef.current;
    const timeScale = chart.timeScale();

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
            isProfit: (conn.pnl || 0) >= 0,
          });
        }
      });
      setSvgLines(lines);
    } else {
      setSvgLines([]);
    }

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

  // Marker click inspector
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
    };

    chart.subscribeClick(handleClick);
    return () => chart.unsubscribeClick(handleClick);
  }, [buyMarkers, sellMarkers, onSelectMarker]);

  const allExecutedMarkers = [...buyMarkers, ...sellMarkers].sort((a, b) => {
    const tA = typeof a.time === 'number' ? a.time : (typeof a.timestamp === 'number' ? a.timestamp : 0);
    const tB = typeof b.time === 'number' ? b.time : (typeof b.timestamp === 'number' ? b.timestamp : 0);
    return tA - tB;
  });

  return (
    <div className="flex flex-col gap-2 relative">
      {/* Top TradingView-Style Bar: Timeframes, fx Indicators Dropdown, Simulation Speed */}
      <div className="flex flex-wrap items-center justify-between gap-2 bg-[#0b0e14] px-3 py-2 rounded-lg border border-[#1f293d] text-xs">
        {/* Timeframe & Indicators */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Timeframe Selector */}
          <div className="flex items-center gap-1 bg-[#141b29] p-0.5 rounded border border-[#1f293d]">
            {[
              { id: '5m', label: '5m' },
              { id: '15m', label: '15m' },
              { id: '1h', label: '1h' },
              { id: '1d', label: '1D' },
              { id: '1w', label: '1W' },
              { id: '1mo', label: '1M' },
            ].map((tf) => {
              const isActive = selectedTimeframe === tf.id;
              return (
                <button
                  key={tf.id}
                  type="button"
                  onClick={() => onSelectTimeframe && onSelectTimeframe(tf.id)}
                  className={`px-2 py-0.5 rounded text-[11px] font-bold transition-all ${
                    isActive
                      ? 'bg-[#00c896] text-black font-black shadow-sm'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                  title={`Switch timeframe to ${tf.label}`}
                >
                  {tf.label}
                </button>
              );
            })}
          </div>

          <div className="h-4 w-px bg-slate-700 mx-1 hidden sm:block" />

          {/* fx Indicators Dropdown Button (matching screenshot) */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowIndicatorsMenu(!showIndicatorsMenu)}
              className={`px-3 py-1 rounded text-xs font-bold transition-all flex items-center gap-1.5 border shadow-sm ${
                showIndicatorsMenu
                  ? 'bg-emerald-950 text-emerald-300 border-emerald-500 shadow-emerald-950'
                  : 'bg-[#141b29] text-slate-200 border-[#2a374f] hover:border-emerald-500/60 hover:text-white'
              }`}
            >
              <span className="font-serif italic font-extrabold text-[#00c896] text-sm">fx</span>
              <span className="font-bold">Indicators</span>
              <span className="ml-1 text-[10px] px-1.5 py-0.2 rounded-full bg-[#1e293b] text-emerald-400 font-mono font-bold">
                {activeIndicatorsCount}
              </span>
              <span className="text-[10px] text-slate-400">▾</span>
            </button>

            {/* Dropdown Menu Modal */}
            {showIndicatorsMenu && (
              <div className="absolute left-0 top-9 w-80 bg-[#0f172a] border border-[#2a374f] rounded-xl shadow-2xl p-3 z-50 text-xs space-y-3">
                {/* Header & Presets */}
                <div className="flex items-center justify-between border-b border-slate-700/60 pb-2">
                  <span className="font-extrabold text-white text-xs flex items-center gap-1.5">
                    <span className="font-serif italic text-emerald-400">fx</span> Technical Indicators
                  </span>
                  <button
                    type="button"
                    onClick={() => setShowIndicatorsMenu(false)}
                    className="text-slate-400 hover:text-white text-xs px-1"
                  >
                    ✕
                  </button>
                </div>

                {/* Quick Presets */}
                <div className="flex items-center gap-1.5 bg-[#141b29] p-1 rounded-lg border border-[#1f293d]">
                  <button
                    type="button"
                    onClick={() => applyPreset('default')}
                    className="flex-1 py-1 rounded text-[10px] font-bold bg-[#1e293b] text-emerald-400 hover:bg-slate-700 text-center"
                    title="Groww/TradingView Default: EMA9 + EMA21 + Volume + RSI 14"
                  >
                    Terminal Default
                  </button>
                  <button
                    type="button"
                    onClick={() => applyPreset('all')}
                    className="flex-1 py-1 rounded text-[10px] font-bold bg-[#1e293b] text-sky-400 hover:bg-slate-700 text-center"
                  >
                    All 10 Strategies
                  </button>
                  <button
                    type="button"
                    onClick={() => applyPreset('minimal')}
                    className="flex-1 py-1 rounded text-[10px] font-bold bg-[#1e293b] text-slate-400 hover:bg-slate-700 text-center"
                  >
                    Clean
                  </button>
                </div>

                {/* Indicator Groups */}
                <div className="max-h-72 overflow-y-auto space-y-2 pr-1 no-scrollbar">
                  {/* Category: Moving Averages */}
                  <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider pt-1">
                    Moving Averages & Trend
                  </div>
                  <div className="space-y-1">
                    {[
                      { key: 'ema9', label: 'EMA 9 (Momentum Trend)', color: '#38bdf8' },
                      { key: 'ema21', label: 'EMA 21 (Pullback / Baseline)', color: '#f43f5e' },
                      { key: 'ema50', label: 'EMA 50 (Intermediate Trend)', color: '#f59e0b' },
                      { key: 'ema200', label: 'EMA 200 (Macro Long-Term Trend)', color: '#a855f7' },
                      { key: 'vwap', label: 'VWAP (Volume-Weighted Avg Price)', color: '#c084fc', dashed: true },
                    ].map((item) => (
                      <label
                        key={item.key}
                        className="flex items-center justify-between p-1.5 rounded hover:bg-slate-800/60 cursor-pointer select-none"
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className="w-3 h-1 rounded-sm inline-block"
                            style={{ backgroundColor: item.color }}
                          />
                          <span className="text-slate-200 text-[11px] font-medium">{item.label}</span>
                        </div>
                        <input
                          type="checkbox"
                          checked={indicators[item.key]}
                          onChange={() => toggleIndicator(item.key)}
                          className="w-3.5 h-3.5 accent-[#00c896] rounded cursor-pointer"
                        />
                      </label>
                    ))}
                  </div>

                  {/* Category: Volatility & Breakout */}
                  <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider pt-2 border-t border-slate-800">
                    Volatility & Breakouts
                  </div>
                  <div className="space-y-1">
                    {[
                      { key: 'bb', label: 'Bollinger Bands (20, 2)', color: '#06b6d4' },
                      { key: 'donchian', label: 'Donchian Channels (20-bar Breakout)', color: '#10b981' },
                      { key: 'supertrend', label: 'Supertrend (ATR 10, 3.0)', color: '#84cc16' },
                      { key: 'orb', label: "Today's High / Low (ORB Bands)", color: '#fbbf24' },
                    ].map((item) => (
                      <label
                        key={item.key}
                        className="flex items-center justify-between p-1.5 rounded hover:bg-slate-800/60 cursor-pointer select-none"
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className="w-3 h-1 rounded-sm inline-block"
                            style={{ backgroundColor: item.color }}
                          />
                          <span className="text-slate-200 text-[11px] font-medium">{item.label}</span>
                        </div>
                        <input
                          type="checkbox"
                          checked={indicators[item.key]}
                          onChange={() => toggleIndicator(item.key)}
                          className="w-3.5 h-3.5 accent-[#00c896] rounded cursor-pointer"
                        />
                      </label>
                    ))}
                  </div>

                  {/* Category: Oscillators & Volume */}
                  <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider pt-2 border-t border-slate-800">
                    Oscillators & Volume
                  </div>
                  <div className="space-y-1">
                    {[
                      { key: 'volume', label: 'Volume Histogram Bars', color: '#10b981' },
                      { key: 'rsi', label: 'RSI 14 Sub-Chart (70 / 50 / 30)', color: '#a855f7' },
                      { key: 'macd', label: 'MACD (12, 26, 9 Momentum)', color: '#38bdf8' },
                      { key: 'stoch', label: 'Stochastic Oscillator (%K, %D)', color: '#06b6d4' },
                    ].map((item) => (
                      <label
                        key={item.key}
                        className="flex items-center justify-between p-1.5 rounded hover:bg-slate-800/60 cursor-pointer select-none"
                      >
                        <div className="flex items-center gap-2">
                          <span
                            className="w-3 h-1 rounded-sm inline-block"
                            style={{ backgroundColor: item.color }}
                          />
                          <span className="text-slate-200 text-[11px] font-medium">{item.label}</span>
                        </div>
                        <input
                          type="checkbox"
                          checked={indicators[item.key]}
                          onChange={() => toggleIndicator(item.key)}
                          className="w-3.5 h-3.5 accent-[#00c896] rounded cursor-pointer"
                        />
                      </label>
                    ))}
                  </div>

                  {/* Category: Risk & Signals */}
                  <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider pt-2 border-t border-slate-800">
                    Risk & Signals
                  </div>
                  <div className="space-y-1">
                    <label className="flex items-center justify-between p-1.5 rounded hover:bg-slate-800/60 cursor-pointer select-none">
                      <div className="flex items-center gap-2">
                        <span className="w-3 h-1 rounded-sm inline-block bg-[#f43f5e]" />
                        <span className="text-slate-200 text-[11px] font-medium">Safety Limit (Active Stop-Loss)</span>
                      </div>
                      <input
                        type="checkbox"
                        checked={indicators.stopLoss}
                        onChange={() => toggleIndicator('stopLoss')}
                        className="w-3.5 h-3.5 accent-[#00c896] rounded cursor-pointer"
                      />
                    </label>

                    <label className="flex items-center justify-between p-1.5 rounded hover:bg-slate-800/60 cursor-pointer select-none">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full inline-block bg-[#f59e0b]" />
                        <span className="text-slate-200 text-[11px] font-medium">Discrete HOLD Dots</span>
                      </div>
                      <input
                        type="checkbox"
                        checked={indicators.holdSignals}
                        onChange={() => toggleIndicator('holdSignals')}
                        className="w-3.5 h-3.5 accent-[#00c896] rounded cursor-pointer"
                      />
                    </label>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Simulation Speed Buttons */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mr-1 hidden sm:inline">
            Speed:
          </span>
          {[
            { id: '1x', label: '1x' },
            { id: '5x', label: '5x' },
            { id: '10x', label: '10x' },
            { id: '20x', label: '20x' },
            { id: '50x', label: '50x' },
          ].map((sp) => {
            const isActive = (simulationSpeed || '').toLowerCase() === sp.id.toLowerCase();
            const is20x = sp.id === '20x';
            return (
              <button
                key={sp.id}
                type="button"
                onClick={() => onSelectSpeed && onSelectSpeed(sp.id)}
                className={`px-2 py-0.5 rounded text-[11px] font-extrabold transition-all flex items-center gap-1 ${
                  isActive
                    ? 'bg-amber-400 text-black shadow-md shadow-amber-950/50 ring-1 ring-amber-300'
                    : is20x
                    ? 'bg-amber-950/60 text-amber-300 border border-amber-500/50 hover:bg-amber-900/50'
                    : 'bg-[#141b29] text-slate-400 hover:text-white hover:bg-slate-800 border border-[#1f293d]'
                }`}
                title={`Set replay speed to ${sp.label}`}
              >
                {is20x && <span>⚡</span>}
                <span>{sp.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Candlestick Chart Canvas Container */}
      <div className="relative w-full h-[380px] rounded-lg overflow-hidden border border-[#1e293b] bg-[#111827]">
        {/* Floating Buy/Sell Badges (Matching Screenshot) */}
        {latestPrice > 0 && (
          <div className="absolute top-2.5 left-3 z-20 flex items-center gap-1.5 font-mono text-xs select-none bg-[#0b0e14]/85 backdrop-blur-sm p-1 rounded-lg border border-[#1f293d] shadow-lg pointer-events-auto">
            <button
              type="button"
              onClick={() => onExecuteOrder && onExecuteOrder('SELL')}
              className="flex items-center gap-1 px-2 py-0.5 rounded bg-[#eb5757] hover:bg-rose-500 text-white font-bold text-[11px] shadow-sm shadow-rose-950 transition-all active:scale-95"
              title="Click to execute SELL order"
            >
              <span>₹{(latestPrice - 0.50).toFixed(2)}</span>
              <span className="text-[9px] font-sans font-extrabold uppercase ml-1 opacity-90">SELL</span>
            </button>
            <div className="px-1.5 py-0.5 rounded bg-[#161f30] text-slate-400 text-[10px] font-bold">
              0.00
            </div>
            <button
              type="button"
              onClick={() => onExecuteOrder && onExecuteOrder('BUY')}
              className="flex items-center gap-1 px-2 py-0.5 rounded bg-[#00c896] hover:bg-emerald-400 text-black font-extrabold text-[11px] shadow-sm shadow-emerald-950 transition-all active:scale-95"
              title="Click to execute BUY order"
            >
              <span>₹{(latestPrice + 0.50).toFixed(2)}</span>
              <span className="text-[9px] font-sans font-extrabold uppercase ml-1 opacity-90">BUY</span>
            </button>
          </div>
        )}

        {/* Legend Overlay: MA 9, MA 21, Volume (Matching Screenshot) */}
        {latestPrice > 0 && (
          <div className="absolute top-10 left-3 z-20 flex flex-col gap-0.5 font-mono text-[11px] select-none pointer-events-none">
            {indicators.ema9 && latestEma9 && (
              <div className="flex items-center gap-2">
                <span className="text-[#38bdf8] font-bold">
                  MA 9 close <span className="text-white">₹{Number(latestEma9).toFixed(2)}</span>
                </span>
              </div>
            )}
            {indicators.ema21 && latestEma21 && (
              <div className="flex items-center gap-2">
                <span className="text-[#f43f5e] font-bold">
                  MA 21 close <span className="text-white">₹{Number(latestEma21).toFixed(2)}</span>
                </span>
              </div>
            )}
            {indicators.volume && latestVolume !== undefined && (
              <div className="flex items-center gap-2">
                <span className="text-[#10b981] font-bold">
                  Volume <span className="text-slate-300">{(latestVolume / 1000).toFixed(2)} K</span>
                </span>
              </div>
            )}
            {indicators.vwap && latestCandle?.vwap && (
              <div className="flex items-center gap-2">
                <span className="text-[#c084fc] font-bold">
                  VWAP <span className="text-white">₹{Number(latestCandle.vwap).toFixed(2)}</span>
                </span>
              </div>
            )}
          </div>
        )}

        {/* Lightweight Charts Canvas */}
        <div ref={chartContainerRef} className="w-full h-[380px]" style={{ minHeight: '380px' }} />

        {/* SVG Trade Connection Lines & Vertical Replay Cursor Overlay */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-10">
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
              <g
                transform={`translate(${Math.max(
                  10,
                  Math.min(cursorX - 25, (chartContainerRef.current?.clientWidth || 600) - 60)
                )}, 6)`}
              >
                <rect width={52} height={18} rx={3} fill="#0891b2" opacity={0.9} />
                <text x={26} y={13} textAnchor="middle" fill="#ffffff" fontSize={10} fontFamily="monospace" fontWeight="bold">
                  {currentSimulatedTime || (isLiveMode ? 'LIVE' : '09:15')}
                </text>
              </g>
            </g>
          )}

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

      {/* RSI 14 Synchronized Sub-Pane (Matching Screenshot) */}
      {indicators.rsi && (
        <div className="relative w-full h-[110px] rounded-lg overflow-hidden border border-[#1e293b] bg-[#0d121c]">
          {/* RSI Legend Label */}
          <div className="absolute top-2 left-3 z-20 flex items-center gap-2 font-mono text-[11px] select-none pointer-events-none">
            <span className="text-[#a855f7] font-bold">
              RSI 14{' '}
              <span className="text-white font-extrabold">
                {latestRsi ? Number(latestRsi).toFixed(2) : '50.00'}
              </span>
            </span>
            <span className="text-[10px] text-slate-500 font-sans">
              (70 Overbought • 30 Oversold)
            </span>
          </div>

          <div ref={rsiContainerRef} className="w-full h-[110px]" style={{ minHeight: '110px' }} />
        </div>
      )}

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
                    title="Click to view execution details"
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
