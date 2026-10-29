async function call(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Request to ${path} failed with ${res.status}`);
  }
  return res.json();
}

const post = (path, body = {}) => call(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  state: () => call("/state"),
  tick: (steps = 1) => post("/tick", { steps }),
  reset: () => post("/reset"),
  killSwitch: (engaged) => post("/kill-switch", { engaged }),
  chaos: (scenario) => post("/chaos", { scenario }),
  backtest: () => call("/backtest"),
};

export const fmt = (n, digits = 2) =>
  n === null || n === undefined
    ? "–"
    : Number(n).toLocaleString("en-IN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
