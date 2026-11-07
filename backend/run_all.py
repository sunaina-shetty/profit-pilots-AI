import os
import sys
import time
import subprocess
import signal
import requests

SERVICES = [
    ("data_service", "backend/services/data_service/app.py", 5001),
    ("agents_service", "backend/services/agents_service/app.py", 5002),
    ("decision_service", "backend/services/decision_service/app.py", 5003),
    ("risk_service", "backend/services/risk_service/app.py", 5004),
    ("exchange_service", "backend/services/exchange_service/app.py", 5005),
    ("journal_service", "backend/services/journal_service/app.py", 5006),
    ("backtest_service", "backend/services/backtest_service/app.py", 5007),
    ("chaos_service", "backend/services/chaos_service/app.py", 5008),
    ("gateway", "backend/services/gateway/app.py", 5000),
]

processes = []

def cleanup(*args):
    print("\nStopping all ProfitPilot AI microservices...", flush=True)
    for name, proc, port in processes:
        try:
            proc.terminate()
            print(f"  [STOPPED] {name} (PID {proc.pid})", flush=True)
        except Exception:
            pass
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    print("=" * 65, flush=True)
    print("  ProfitPilot AI - Multi-Service Orchestrator (PS-02)", flush=True)
    print("  'Fly for profit. Land safe.'", flush=True)
    print("=" * 65, flush=True)

    # Initialize databases first
    print("\n[Step 1/2] Initializing database layer...", flush=True)
    init_script = os.path.join(os.path.dirname(__file__), "scripts", "init_db.py")
    subprocess.run([sys.executable, init_script], check=True)

    print("[Step 2/2] Launching 9 Microservices...", flush=True)
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    for name, script_rel, port in SERVICES:
        script_path = os.path.join(root_dir, script_rel)
        proc = subprocess.Popen(
            [sys.executable, script_path],
            cwd=root_dir
        )
        processes.append((name, proc, port))
        print(f"  -> Starting {name:<18} on port {port} (PID {proc.pid})...", flush=True)

    print("\nWaiting for all services to pass /health checks...", flush=True)
    time.sleep(2)

    all_healthy = True
    for name, proc, port in processes:
        url = f"http://localhost:{port}/health"
        healthy = False
        for attempt in range(12):
            try:
                r = requests.get(url, timeout=1.0)
                if r.status_code == 200:
                    healthy = True
                    break
            except Exception:
                time.sleep(0.5)

        if healthy:
            print(f"  [HEALTHY] {name:<18} (port {port})", flush=True)
        else:
            print(f"  [WARNING] {name:<18} did not respond on port {port} yet", flush=True)
            all_healthy = False

    print("\n" + "=" * 65, flush=True)
    if all_healthy:
        print("  ALL 9 PROFITPILOT SERVICES RUNNING SUCCESSFULLY!", flush=True)
        print("  API Gateway: http://localhost:5000", flush=True)
        print("  Real-time SSE: http://localhost:5000/stream", flush=True)
    else:
        print("  Services started. Check logs if any service is slow to warm up.", flush=True)
    print("  Press Ctrl+C to stop all services.", flush=True)
    print("=" * 65 + "\n", flush=True)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()

if __name__ == "__main__":
    main()
