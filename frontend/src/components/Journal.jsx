const KIND_LABEL = {
  TRADE: "Trade", HOLD: "Wait", BLOCKED: "Blocked", RISK: "Risk", ALERT: "Alert", CHAOS: "Chaos", SYSTEM: "System",
};

export default function Journal({ entries }) {
  return (
    <>
      <div className="panel-head">
        <h2>Flight journal</h2>
        <span className="muted">Every decision in plain language</span>
      </div>
      <ol className="journal">
        {entries.map((e) => (
          <li key={e.id} className={`entry entry-${e.kind.toLowerCase()}`}>
            <span className="entry-kind">{KIND_LABEL[e.kind] || e.kind}</span>
            <span className="entry-tick">t{e.tick}</span>
            <p>{e.text}</p>
          </li>
        ))}
      </ol>
    </>
  );
}
