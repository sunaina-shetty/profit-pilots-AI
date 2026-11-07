import axios from 'axios';

const BASE_URL = 'http://localhost:5000';

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 8000
});

export const api = {
  // SSE real-time stream
  subscribeSSE: (onEvent, onError) => {
    const sse = new EventSource(`${BASE_URL}/stream`);
    
    const events = [
      'connected',
      'price_tick',
      'agent_votes',
      'decision',
      'risk_verdict',
      'order_filled',
      'portfolio',
      'system_state',
      'journal_entry'
    ];

    events.forEach(eventName => {
      sse.addEventListener(eventName, (e) => {
        try {
          const data = JSON.parse(e.data);
          onEvent(eventName, data);
        } catch (err) {
          console.error(`Error parsing SSE event ${eventName}:`, err);
        }
      });
    });

    sse.onerror = (err) => {
      if (onError) onError(err);
    };

    return () => sse.close();
  },

  // Gateway Controls
  getLoopStatus: () => client.get('/loop/status'),
  startLoop: (symbol, intervalSec = 4.0) => client.post('/loop/start', { symbol, interval_sec: intervalSec }),
  stopLoop: () => client.post('/loop/stop'),
  stepTrade: (symbol) => client.post('/trade/step', { symbol }),
  triggerKillSwitch: (action = 'ENGAGE') => client.post('/kill_switch', { action }),
  resetAll: () => client.post('/reset_all'),

  // Direct Service Queries
  getLimits: () => axios.get('http://localhost:5004/limits'),
  getJournalEntries: (limit = 40, symbol = '') => 
    axios.get(`http://localhost:5006/journal/entries?limit=${limit}${symbol ? `&symbol=${symbol}` : ''}`),
  getBacktest: (symbol = 'RELIANCE.NS', days = 120) => 
    axios.post('http://localhost:5007/backtest/run', { symbol, days }),
  getChaosScenarios: () => axios.get('http://localhost:5008/chaos/scenarios'),
  runChaosTests: (scenarioId = null) => 
    axios.post('http://localhost:5008/chaos/run', { scenario_id: scenarioId }),
  
  // Demo Shock Injectors
  injectShock: (symbol, type, extra = {}) => 
    axios.post('http://localhost:5001/inject_shock', { symbol, type, ...extra }),
  setDataMode: (mode) => 
    axios.post('http://localhost:5001/mode', { mode })
};

