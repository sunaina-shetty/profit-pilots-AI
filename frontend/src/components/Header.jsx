export default function Header({ state, running, speed, onToggleRun, onStep, onReset, onSpeed, onKill }) {
  const progress = Math.round((state.tick / state.total_ticks) * 100);
  const killed = state.risk.kill_switch;

  return (
    <header className="header">
      <div className="brand">
        <h1>ProfitPilot AI</h1>
        <p>Fly for profit. Land safe.</p>
      </div>

      <div className="flight">
        <span className="paper-badge">Paper trading · virtual money</span>
        <div className="progress" aria-label={`Session ${progress}% complete`}>
          <div className="progress-fill" style={{ width: `${progress}%` }} />
        </div>
        <span className="muted">Tick {state.tick} of {state.total_ticks}</span>
      </div>

      <div className="controls">
        <button className="btn btn-primary" onClick={onToggleRun} disabled={state.done}>
          {state.done ? "Session ended" : running ? "Pause" : "Start autopilot"}
        </button>
        <button className="btn" onClick={onStep} disabled={running || state.done}>Step one tick</button>
        <label className="speed">
          Speed
          <select value={speed} onChange={(e) => onSpeed(Number(e.target.value))}>
            <option value={1}>1×</option>
            <option value={3}>3×</option>
            <option value={10}>10×</option>
          </select>
        </label>
        <button className="btn btn-ghost" onClick={onReset}>Reset session</button>
      </div>

      <button
        className={`kill ${killed ? "kill-on" : ""}`}
        onClick={onKill}
        aria-pressed={killed}
      >
        <span className="kill-guard" aria-hidden="true" />
        <span className="kill-label">{killed ? "Release kill switch" : "Kill switch"}</span>
      </button>
    </header>
  );
}
