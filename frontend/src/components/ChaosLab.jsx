export default function ChaosLab({ chaos, onInject }) {
  const s = chaos.safety_score;
  const activeIds = new Set(chaos.active.map((a) => a.label));

  return (
    <>
      <div className="panel-head">
        <h2>Chaos Lab</h2>
        <div className="score" aria-label="Safety score">
          <span className="big-num">{s.total ? `${s.passed}/${s.total}` : "–"}</span>
          <span className="muted">{s.total ? `handled safely (${s.pct}%)` : "no tests run yet"}</span>
        </div>
      </div>

      <div className="scenarios">
        {chaos.scenarios.map((sc) => (
          <button key={sc.id} className="scenario" onClick={() => onInject(sc.id)} disabled={activeIds.has(sc.label)}>
            <strong>{sc.label}</strong>
            <span>{sc.description}</span>
            <span className="muted">Expected: {sc.expect}</span>
          </button>
        ))}
      </div>

      {chaos.active.length > 0 && (
        <p className="watching">
          Watching: {chaos.active.map((a) => `${a.label} (${a.ticks_left} ticks left)`).join(", ")}. Keep the autopilot running.
        </p>
      )}

      <ul className="results">
        {chaos.results.map((r) => (
          <li key={r.id} className={r.passed ? "result-pass" : "result-fail"}>
            <strong>{r.passed ? "Passed" : "Failed"}: {r.label}</strong> <span className="muted">tick {r.tick}</span>
            <p>{r.detail}</p>
          </li>
        ))}
      </ul>
    </>
  );
}
