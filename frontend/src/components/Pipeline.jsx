const VoteChip = ({ v }) => <span className={`chip chip-${(v || "none").toLowerCase()}`}>{v || "–"}</span>;

export default function Pipeline({ state }) {
  const last = state.last;
  if (!last) {
    return (
      <>
        <div className="panel-head"><h2>Decision pipeline</h2></div>
        <p className="empty">Start the autopilot or step one tick to see the agents vote.</p>
      </>
    );
  }
  const { validation: val, votes, decision, verdict } = last;
  const stepState = (ok) => (ok ? "ok" : "bad");

  return (
    <>
      <div className="panel-head">
        <h2>Decision pipeline</h2>
        <span className="muted">Tick {last.tick}</span>
      </div>

      <ol className="pipeline">
        <li className={`stage stage-${stepState(val.fresh && !val.quarantined.length)}`}>
          <h3><span className="step-no">1–2</span> Data check</h3>
          <p>{val.fresh ? `Price is fresh (${val.age_seconds}s old).` : `Price is ${val.age_seconds}s old. No trading.`}</p>
          <p className="muted">{val.headlines.length} trusted headline{val.headlines.length === 1 ? "" : "s"} in view.</p>
          {val.quarantined.map((q, i) => (
            <p key={i} className="quarantine">Quarantined: “{q.headline}” from {q.source}</p>
          ))}
        </li>

        <li className="stage stage-agents">
          <h3><span className="step-no">3</span> Agents vote</h3>
          {votes.length === 0 && <p className="muted">Agents paused: {decision.reason}</p>}
          <div className="agents">
            {votes.map((v) => (
              <article key={v.agent} className={`agent ${v.offline ? "agent-offline" : ""}`}>
                <header>
                  <strong>{v.agent}</strong>
                  <VoteChip v={v.vote} />
                </header>
                <p>{v.reason}</p>
                <div className="confidence" aria-label={`Confidence ${Math.round(v.confidence * 100)}%`}>
                  <div style={{ width: `${v.confidence * 100}%` }} />
                </div>
              </article>
            ))}
          </div>
        </li>

        <li className="stage">
          <h3><span className="step-no">4</span> Decision</h3>
          <p className="decision"><VoteChip v={decision.action} />
            {decision.size ? <span className="muted">{decision.size === 1 ? "Full size" : "Half size"}</span> : null}
          </p>
          <p>{decision.reason}</p>
        </li>

        <li className={`stage ${verdict ? `stage-${stepState(verdict.approved)}` : ""}`}>
          <h3><span className="step-no">5–6</span> Risk manager</h3>
          {!verdict && <p className="muted">No order requested this tick.</p>}
          {verdict && (
            <>
              <p className={verdict.approved ? "up" : "down"}>
                {verdict.approved ? `Approved: ${verdict.qty} shares` : "Rejected"}
              </p>
              <ul className="checks">
                {verdict.checks.map((c) => (
                  <li key={c.name} className={c.ok ? "check-ok" : "check-bad"}>
                    <span aria-hidden="true">{c.ok ? "✓" : "✕"}</span> <strong>{c.name}:</strong> {c.detail}
                  </li>
                ))}
              </ul>
            </>
          )}
        </li>
      </ol>
    </>
  );
}
