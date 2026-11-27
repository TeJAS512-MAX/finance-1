@echo off
title AetherPravah - 3D Causal Financial Organism
echo ========================================================
echo       AetherPravah: AI that handles money better
echo       Full Attractive 3D Web Experience + Causal Engine
echo ========================================================
echo.

cd /d "%~dp0"

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [*] Creating Python virtual environment...
    python -m venv .venv
    echo [*] Installing backend dependencies...
    .venv\Scripts\pip install -r requirements.txt
)

echo [*] Starting Python Causal Engine on port 8001...
set PYTHONPATH=.
start "AetherPravah Backend" /B .venv\Scripts\python.exe -m uvicorn backend.api.server:app --host 127.0.0.1 --port 8001

echo [*] Starting Next.js 3D Web Experience on port 3001...
set NEXT_PUBLIC_AETHER_API_URL=http://localhost:8001
set NEXT_PUBLIC_MARKET_APP_URL=http://localhost:3000
cd frontend
start "" "http://localhost:3001"
npm run dev -- --port 3001
pause
