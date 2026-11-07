import React from 'react';

export default function KillSwitchModal({ isOpen, onClose, onConfirm, action = 'ENGAGE' }) {
  if (!isOpen) return null;

  const isEngage = action === 'ENGAGE';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className={`w-full max-w-md p-6 rounded-2xl border shadow-2xl ${
        isEngage ? 'bg-[#180a0a] border-red-600/80' : 'bg-[#0a1811] border-emerald-600/80'
      }`}>
        <div className="flex items-center gap-3 mb-4">
          <div className={`w-12 h-12 rounded-full flex items-center justify-center text-2xl ${
            isEngage ? 'bg-red-950 text-red-400 border border-red-700' : 'bg-emerald-950 text-emerald-400 border border-emerald-700'
          }`}>
            {isEngage ? '⚠️' : '✅'}
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">
              {isEngage ? 'ENGAGE EMERGENCY KILL SWITCH' : 'RESUME TRADING PROTOCOL'}
            </h3>
            <p className="text-xs text-slate-400">
              {isEngage ? 'Direct Risk Manager Hardware Circuit' : 'Unlock Autonomous Execution'}
            </p>
          </div>
        </div>

        <p className="text-sm text-slate-300 mb-6 leading-relaxed">
          {isEngage ? (
            <>
              Activating the <span className="font-bold text-red-400">EMERGENCY KILL SWITCH</span> instantly overrides all AI agents and algorithms:
              <ul className="list-disc list-inside mt-2 space-y-1 text-slate-400 text-xs">
                <li>Immediately halts all incoming orders</li>
                <li>Flattens and market-sells all active open positions</li>
                <li>Operates independently of agents or external LLM uptime</li>
              </ul>
            </>
          ) : (
            <>
              Confirming <span className="font-bold text-emerald-400">RESUME TRADING</span> will clear the hardware lock and restore autonomous signal evaluation and order execution under full 16-rule risk validation.
            </>
          )}
        </p>

        <div className="flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-semibold"
          >
            Cancel
          </button>
          <button
            onClick={() => {
              onConfirm();
              onClose();
            }}
            className={`px-4 py-2 rounded-lg text-white text-sm font-bold shadow-lg transition-all ${
              isEngage ? 'bg-red-600 hover:bg-red-500 shadow-red-950' : 'bg-emerald-600 hover:bg-emerald-500 shadow-emerald-950'
            }`}
          >
            {isEngage ? 'CONFIRM KILL ALL' : 'CONFIRM RESUME'}
          </button>
        </div>
      </div>
    </div>
  );
}

