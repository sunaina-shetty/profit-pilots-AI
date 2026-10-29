import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import Header from "./components/Header.jsx";
import PriceChart from "./components/PriceChart.jsx";
import Portfolio from "./components/Portfolio.jsx";
import Pipeline from "./components/Pipeline.jsx";
import ChaosLab from "./components/ChaosLab.jsx";
import Journal from "./components/Journal.jsx";
import Backtest from "./components/Backtest.jsx";

const BEAT_MS = 700;

export default function App() {
  const [state, setState] = useState(null);
  const [running, setRunning] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [error, setError] = useState(null);
  const inFlight = useRef(false);

  const run = useCallback(async (request) => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const next = await request();
      setState(next);
      setError(null);
      if (next.done) setRunning(false);
    } catch (e) {
      setError(e.message.includes("fetch") || e.message.includes("502") || e.message.includes("500")
        ? "Can't reach the trading engine. Start the backend with: python app.py"
        : e.message);
      setRunning(false);
    } finally {
      inFlight.current = false;
    }
  }, []);

  useEffect(() => { run(api.state); }, [run]);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => run(() => api.tick(speed)), BEAT_MS);
    return () => clearInterval(id);
  }, [running, speed, run]);

  if (!state) {
    return (
      <div className="boot">
        <h1>ProfitPilot AI</h1>
        <p>{error || "Connecting to the trading engine…"}</p>
      </div>
    );
  }

  const killEngaged = state.risk.kill_switch;

  return (
    <div className={`app ${killEngaged ? "is-killed" : ""}`}>
      <div className="topbar">
      <Header
        state={state}
        running={running}
        speed={speed}
        onToggleRun={() => setRunning((r) => !r)}
        onStep={() => run(() => api.tick(1))}
        onReset={() => { setRunning(false); run(api.reset); }}
        onSpeed={setSpeed}
        onKill={() => run(() => api.killSwitch(!killEngaged))}
      />

      {error && <div className="banner banner-error" role="alert">{error}</div>}
      {killEngaged && (
        <div className="banner banner-kill" role="status">
          Kill switch engaged. The AI cannot place orders. Stop-losses remain active.
        </div>
      )}
      </div>

      <main className="grid">
        <section className="panel area-chart">
          <PriceChart state={state} />
        </section>
        <section className="panel area-portfolio">
          <Portfolio state={state} />
        </section>
        <section className="panel area-pipeline">
          <Pipeline state={state} />
        </section>
        <section className="panel area-chaos">
          <ChaosLab chaos={state.chaos} onInject={(s) => run(() => api.chaos(s))} />
        </section>
        <section className="panel area-journal">
          <Journal entries={state.journal} />
        </section>
        <section className="panel area-backtest">
          <Backtest />
        </section>
      </main>

      <footer className="footer">
        Paper trading only. Virtual money; no real orders are ever sent. Data: {state.data_source}.
      </footer>
    </div>
  );
}
