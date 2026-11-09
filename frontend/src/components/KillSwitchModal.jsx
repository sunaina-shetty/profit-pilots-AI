import React, { useState } from 'react';
import { ShieldAlert, PauseCircle, ZapOff, X } from 'lucide-react';

export default function KillSwitchModal({ isOpen, onClose, onConfirmKill }) {
  const [selectedMode, setSelectedMode] = useState('flatten'); // 'flatten' | 'stop_new'

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 select-none">
      <div className="bg-[#121926] border border-rose-500/40 rounded-2xl w-full max-w-md shadow-2xl shadow-rose-950/60 p-6 space-y-5 animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#1f293d] pb-3">
          <div className="flex items-center gap-2 text-rose-400 font-extrabold text-base">
            <ShieldAlert className="w-5 h-5 text-rose-500 animate-pulse" />
            <span>EMERGENCY KILL SWITCH</span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed">
          Select an emergency intervention mode. This command will be dispatched immediately to the broker and trading engine.
        </p>

        {/* Mode Selector */}
        <div className="space-y-3">
          {/* Mode 1: Emergency Flatten */}
          <button
            onClick={() => setSelectedMode('flatten')}
            className={`w-full text-left p-3.5 rounded-xl border transition-all flex items-start gap-3 ${
              selectedMode === 'flatten'
                ? 'bg-rose-950/40 border-rose-500 text-white shadow-md shadow-rose-950/50'
                : 'bg-[#0f1420] border-[#1a2333] hover:bg-[#161f30] text-slate-300'
            }`}
          >
            <ZapOff className={`w-5 h-5 mt-0.5 shrink-0 ${selectedMode === 'flatten' ? 'text-rose-400' : 'text-slate-500'}`} />
            <div>
              <div className="font-bold text-xs flex items-center gap-2">
                <span>Emergency Flatten (Market Close All)</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30">
                  Instant Liquidate
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1 leading-normal">
                Immediately market liquidates any active open positions, cancels all pending orders, and completely stops simulation.
              </p>
            </div>
          </button>

          {/* Mode 2: Stop New Trades */}
          <button
            onClick={() => setSelectedMode('stop_new')}
            className={`w-full text-left p-3.5 rounded-xl border transition-all flex items-start gap-3 ${
              selectedMode === 'stop_new'
                ? 'bg-amber-950/40 border-amber-500 text-white shadow-md shadow-amber-950/50'
                : 'bg-[#0f1420] border-[#1a2333] hover:bg-[#161f30] text-slate-300'
            }`}
          >
            <PauseCircle className={`w-5 h-5 mt-0.5 shrink-0 ${selectedMode === 'stop_new' ? 'text-amber-400' : 'text-slate-500'}`} />
            <div>
              <div className="font-bold text-xs flex items-center gap-2">
                <span>Stop New Trades (Manage Active Position)</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  Soft Halt
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-1 leading-normal">
                Blocks agents from initiating any new trades. Any open position is left intact to hit its designated Stop-Loss, Take-Profit (1.5R), or 15:15 square-off.
              </p>
            </div>
          </button>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#1f293d]">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-[#1a2333] text-slate-300 text-xs font-semibold hover:bg-slate-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onConfirmKill(selectedMode)}
            className={`px-5 py-2 rounded-lg text-white text-xs font-bold transition-all shadow-lg active:scale-95 ${
              selectedMode === 'flatten'
                ? 'bg-rose-600 hover:bg-rose-500 shadow-rose-950/60'
                : 'bg-amber-600 hover:bg-amber-500 shadow-amber-950/60'
            }`}
          >
            {selectedMode === 'flatten' ? 'CONFIRM EMERGENCY FLATTEN' : 'CONFIRM STOP NEW TRADES'}
          </button>
        </div>
      </div>
    </div>
  );
}

