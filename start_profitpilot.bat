@echo off
title ProfitPilot AI - Launching System
echo ============================================================
echo   ProfitPilot AI - Hackathon PS-02 Launcher
echo   "Fly for profit. Land safe."
echo ============================================================
echo.

echo [1/2] Starting Backend Microservices (Ports 5000-5008)...
start "ProfitPilot Backend" cmd /k "python backend\run_all.py"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Frontend Vite Cockpit (Port 5173)...
start "ProfitPilot Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ============================================================
echo   All services launched in separate windows!
echo   Open your browser at: http://localhost:5173
echo ============================================================
pause

