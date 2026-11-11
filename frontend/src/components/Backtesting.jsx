import React, { useState } from 'react';
import { Play, TrendingUp, TrendingDown, DollarSign, Activity, Percent, ShieldCheck, AlertCircle, ArrowUpRight, ArrowDownRight, Layers } from 'lucide-react';
import { getApiUrl } from '../utils/api';

export default function Backtesting({ stocksList = [], onSelectSymbol, onOpenTerminalWithSymbol }) {
  const [symbol, setSymbol] = useState('TCS');
  const [strategyId, setStrategyId] = useState('strat_orb');
  const [days, setDays] = useState(5);
  const [initialCapital, setInitialCapital] = useState(100000);
  const [riskPerTradePct, setRiskPerTradePct] = useState(0.5);
  const [stopLossPct, setStopLossPct] = useState(1.0);
  const [targetRr, setTargetRr] = useState(1.5);
  const [isLoading, setIsLoading] = useState(false);
  const [backtestResult, setBacktestResult] = useState(null);
  const [error, setError] = useState(null);

  const STRATEGIES = [
    { id: 'strat_orb', name: 'Opening Range Breakout (ORB)', category: 'Breakout' },
    { id: 'strat_ema_rsi_vol', name: 'EMA 9/21 + RSI 14 + Volume', category: 'Trend Following' },
    { id: 'strat_supertrend_ema200', name: 'Supertrend (10,3) + EMA 200', category: 'Trend Following' },
    { id: 'strat_vwap_pullback', name: 'VWAP + EMA 9/21 Pullback', category: 'Trend/Pullback' },
    { id: 'strat_macd_rsi_ema200', name: 'MACD (12,26,9) + RSI + EMA 200', category: 'Momentum' },
    { id: 'strat_bb_rsi_reversal', name: 'Bollinger Bands (20,2) + RSI Reversal', category: 'Mean Reversion' },
    { id: 'strat_adx_di_regime', name: 'ADX (14) + DI + EMA 200', category: 'Trend Strength' },
    { id: 'strat_rsi_divergence', name: 'RSI Divergence + EMA Crossover', category: 'Reversal' },
    { id: 'strat_donchian_breakout', name: 'Donchian Channel (20) + EMA 200', category: 'Breakout' },
    { id: 'strat_stochastic_ema', name: 'Stochastic (14,3,3) + EMA 50/200', category: 'Momentum' },
  ];

  const handleRunBacktest = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await fetch(getApiUrl('/api/backtest'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol,
          strategy_id: strategyId,
          days: Number(days),
          initial_capital: Number(initialCapital),
          risk_per_trade_pct: Number(riskPerTradePct),
          stop_loss_pct: Number(stopLossPct),
          target_rr: Number(targetRr)
        })
      });
      const data = await resp.json();
      if (!resp.ok) {
        throw new Error(data.error || 'Backtest failed to execute');
      }
      setBacktestResult(data);
    } catch (err) {
      setError(err.message || 'Error executing backtest');
    } finally {
      setIsLoading(false);
    }
  };

  const metrics = backtestResult?.metrics;

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-[#0f141f] border border-[#1f293d] p-5 rounded-2xl shadow-lg">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white tracking-wide">Quantitative Backtesting Lab</h1>
            <span className="text-[10px] font-extrabold uppercase px-2 py-0.5 rounded bg-emerald-500/20 text-[#00c896] border border-emerald-500/30">
              Institutional Engine
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Chronological multi-day out-of-sample simulation across all 10 trading strategies with exact regulatory fee modeling and zero look-ahead bias.
          </p>
        </div>
      </div>

      {/* Configuration Form */}
      <div className="bg-[#0f141f] border border-[#1f293d] rounded-2xl p-5 shadow-lg">
        <h2 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Layers className="w-4 h-4 text-emerald-400" />
          Backtest Configuration Parameters
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-xs">
          {/* Stock Selection */}
          <div>
            <label className="block text-slate-400 font-semibold mb-1">Target Stock (NSE)</label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-2 text-white font-bold focus:outline-none focus:border-[#00c896]"
            >
              {stocksList.map((s) => (
                <option key={s.symbol} value={s.symbol.replace('.NS', '')}>
                  {s.display || s.symbol}
                </option>
              ))}
            </select>
          </div>

          {/* Strategy Selection */}
          <div>
            <label className="block text-slate-400 font-semibold mb-1">Trading Strategy</label>
            <select
              value={strategyId}
              onChange={(e) => setStrategyId(e.target.value)}
              className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-2 text-white font-bold focus:outline-none focus:border-[#00c896]"
            >
              {STRATEGIES.map((st) => (
                <option key={st.id} value={st.id}>
                  {st.name} ({st.category})
                </option>
              ))}
            </select>
          </div>

          {/* Date Range / Days */}
          <div>
            <label className="block text-slate-400 font-semibold mb-1">Historical Period (Days)</label>
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-2 text-white font-bold focus:outline-none focus:border-[#00c896]"
            >
              <option value={2}>2 Trading Days (Quick Scan)</option>
              <option value={5}>5 Trading Days (1 Full Week)</option>
              <option value={10}>10 Trading Days (2 Weeks)</option>
              <option value={20}>20 Trading Days (1 Month)</option>
            </select>
          </div>

          {/* Starting Capital */}
          <div>
            <label className="block text-slate-400 font-semibold mb-1">Starting Capital (₹)</label>
            <input
              type="number"
              step="10000"
              value={initialCapital}
              onChange={(e) => setInitialCapital(Number(e.target.value))}
              className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-2 text-white font-mono font-bold focus:outline-none focus:border-[#00c896]"
            />
          </div>

          {/* Risk Per Trade % */}
          <div>
            <label className="block text-slate-400 font-semibold mb-1">Risk Per Trade (%)</label>
            <input
              type="number"
              step="0.1"
              min="0.1"
              max="2.0"
              value={riskPerTradePct}
              onChange={(e) => setRiskPerTradePct(Number(e.target.value))}
              className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-2 text-white font-mono font-bold focus:outline-none focus:border-[#00c896]"
            />
          </div>

          {/* Stop-Loss % */}
          <div>
            <label className="block text-slate-400 font-semibold mb-1">Stop-Loss Distance (%)</label>
            <input
              type="number"
              step="0.1"
              min="0.3"
              max="5.0"
              value={stopLossPct}
              onChange={(e) => setStopLossPct(Number(e.target.value))}
              className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-2 text-white font-mono font-bold focus:outline-none focus:border-[#00c896]"
            />
          </div>

          {/* Target Risk/Reward */}
          <div>
            <label className="block text-slate-400 font-semibold mb-1">Target Reward (R Multiple)</label>
            <input
              type="number"
              step="0.1"
              min="1.0"
              max="4.0"
              value={targetRr}
              onChange={(e) => setTargetRr(Number(e.target.value))}
              className="w-full bg-[#161f30] border border-[#1f293d] rounded-lg px-3 py-2 text-white font-mono font-bold focus:outline-none focus:border-[#00c896]"
            />
          </div>

          {/* Run Button */}
          <div className="flex items-end">
            <button
              onClick={handleRunBacktest}
              disabled={isLoading}
              className="w-full py-2 px-4 rounded-lg bg-[#00c896] hover:bg-emerald-400 disabled:opacity-50 text-black font-extrabold flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/40 transition-all active:scale-95"
            >
              {isLoading ? (
                <>
                  <Activity className="w-4 h-4 animate-spin" />
                  <span>Computing Multi-Day Bars...</span>
                </>
              ) : (
                <>
                  <Play className="w-4 h-4 fill-current" />
                  <span>Run Quantitative Backtest</span>
                </>
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-rose-950/80 border border-rose-500/50 text-rose-300 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Backtest Results Display */}
      {backtestResult && metrics && (
        <div className="space-y-6">
          {/* Key Metrics Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="bg-[#0f141f] border border-[#1f293d] p-4 rounded-xl">
              <span className="text-[11px] text-slate-400 uppercase font-semibold">Net Realized P&L</span>
              <div className={`text-lg font-mono font-black mt-1 ${metrics.net_profit >= 0 ? 'text-[#00c896]' : 'text-rose-400'}`}>
                {metrics.net_profit >= 0 ? '+₹' : '-₹'}{Math.abs(metrics.net_profit).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <span className="text-[10px] text-slate-400 font-mono">ROI: {metrics.net_roi_pct}%</span>
            </div>

            <div className="bg-[#0f141f] border border-[#1f293d] p-4 rounded-xl">
              <span className="text-[11px] text-slate-400 uppercase font-semibold">Win Rate</span>
              <div className="text-lg font-mono font-black text-white mt-1">
                {metrics.win_rate}%
              </div>
              <span className="text-[10px] text-slate-400 font-mono">{metrics.winning_trades}W / {metrics.losing_trades}L</span>
            </div>

            <div className="bg-[#0f141f] border border-[#1f293d] p-4 rounded-xl">
              <span className="text-[11px] text-slate-400 uppercase font-semibold">Profit Factor</span>
              <div className="text-lg font-mono font-black text-sky-400 mt-1">
                {metrics.profit_factor}
              </div>
              <span className="text-[10px] text-slate-400 font-mono">Gross Gain / Loss</span>
            </div>

            <div className="bg-[#0f141f] border border-[#1f293d] p-4 rounded-xl">
              <span className="text-[11px] text-slate-400 uppercase font-semibold">Max Drawdown</span>
              <div className="text-lg font-mono font-black text-amber-400 mt-1">
                {metrics.max_drawdown}%
              </div>
              <span className="text-[10px] text-slate-400 font-mono">Peak to Trough</span>
            </div>

            <div className="bg-[#0f141f] border border-[#1f293d] p-4 rounded-xl">
              <span className="text-[11px] text-slate-400 uppercase font-semibold">Sharpe Ratio</span>
              <div className="text-lg font-mono font-black text-purple-400 mt-1">
                {metrics.sharpe_ratio}
              </div>
              <span className="text-[10px] text-slate-400 font-mono">Risk-Adjusted</span>
            </div>

            <div className="bg-[#0f141f] border border-[#1f293d] p-4 rounded-xl">
              <span className="text-[11px] text-slate-400 uppercase font-semibold">Regulatory Fees</span>
              <div className="text-lg font-mono font-black text-slate-300 mt-1">
                ₹{metrics.total_fees.toFixed(2)}
              </div>
              <span className="text-[10px] text-slate-400 font-mono">STT, GST, Brokerage</span>
            </div>
          </div>

          {/* Equity Progression Summary */}
          <div className="bg-[#0f141f] border border-[#1f293d] p-5 rounded-2xl">
            <div className="flex justify-between items-center mb-4">
              <div>
                <h3 className="text-sm font-bold text-white">Equity Curve Progression</h3>
                <span className="text-xs text-slate-400 font-mono">
                  Starting: ₹{backtestResult.initial_capital.toLocaleString('en-IN')} → Ending: ₹{backtestResult.final_capital.toLocaleString('en-IN')}
                </span>
              </div>
              <span className={`px-2.5 py-1 rounded text-xs font-bold ${
                backtestResult.is_real_data ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/40' : 'bg-amber-950 text-amber-300 border border-amber-500/40'
              }`}>
                {backtestResult.is_real_data ? 'Real 5m NSE Candles' : 'Calibrated Synthetic Baseline'}
              </span>
            </div>

            {/* Visual equity sparkline bars */}
            <div className="h-32 flex items-end gap-1 overflow-x-auto py-2 border-b border-[#1f293d]">
              {backtestResult.equity_curve.map((pt, idx) => {
                const minEq = Math.min(...backtestResult.equity_curve.map((p) => p.equity)) * 0.99;
                const maxEq = Math.max(...backtestResult.equity_curve.map((p) => p.equity)) * 1.01;
                const heightPct = Math.max(10, Math.min(100, ((pt.equity - minEq) / Math.max(1, maxEq - minEq)) * 100));
                const isProfitable = pt.equity >= backtestResult.initial_capital;

                return (
                  <div
                    key={idx}
                    className="flex-1 min-w-[6px] group relative flex flex-col justify-end items-center"
                    style={{ height: '100%' }}
                  >
                    <div
                      className={`w-full rounded-t-sm transition-all ${isProfitable ? 'bg-[#00c896]' : 'bg-rose-500'}`}
                      style={{ height: `${heightPct}%` }}
                    />
                    {/* Tooltip */}
                    <div className="hidden group-hover:block absolute bottom-full mb-2 bg-[#121926] border border-[#1f293d] p-2 rounded shadow-2xl z-30 text-[10px] whitespace-nowrap font-mono text-white">
                      <div>Time: {pt.time}</div>
                      <div>Equity: ₹{pt.equity.toLocaleString('en-IN')}</div>
                      <div>Drawdown: {pt.drawdown}%</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Trade Execution Ledger Table */}
          <div className="bg-[#0f141f] border border-[#1f293d] rounded-2xl p-5 overflow-hidden">
            <h3 className="text-sm font-bold text-white mb-3">Completed Backtest Trades ({backtestResult.trades.length})</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono">
                <thead className="bg-[#161f30] text-slate-400 uppercase text-[10px]">
                  <tr>
                    <th className="p-2.5">ID</th>
                    <th className="p-2.5">Side</th>
                    <th className="p-2.5">Qty</th>
                    <th className="p-2.5">Entry (₹)</th>
                    <th className="p-2.5">Exit (₹)</th>
                    <th className="p-2.5">Fees (₹)</th>
                    <th className="p-2.5">Net P&L (₹)</th>
                    <th className="p-2.5">Exit Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1f293d]">
                  {backtestResult.trades.length > 0 ? (
                    backtestResult.trades.map((tr) => (
                      <tr key={tr.id} className="hover:bg-[#121926]/50">
                        <td className="p-2.5 font-bold text-slate-300">{tr.id}</td>
                        <td className="p-2.5">
                          <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            tr.side === 'BUY' ? 'bg-emerald-950 text-emerald-400' : 'bg-rose-950 text-rose-400'
                          }`}>
                            {tr.side}
                          </span>
                        </td>
                        <td className="p-2.5 text-white">{tr.qty}</td>
                        <td className="p-2.5 text-slate-200">₹{tr.entry_price.toFixed(2)}</td>
                        <td className="p-2.5 text-slate-200">₹{tr.exit_price.toFixed(2)}</td>
                        <td className="p-2.5 text-slate-400">₹{tr.fees.toFixed(2)}</td>
                        <td className={`p-2.5 font-bold ${tr.net_pnl >= 0 ? 'text-[#00c896]' : 'text-rose-400'}`}>
                          {tr.net_pnl >= 0 ? '+₹' : '-₹'}{Math.abs(tr.net_pnl).toFixed(2)}
                        </td>
                        <td className="p-2.5 text-slate-400 text-[11px]">{tr.exit_reason}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={8} className="p-4 text-center text-slate-500 font-sans">
                        No trades triggered for this strategy across the selected historical period.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

