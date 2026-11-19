@echo off
title AetherPravah - Causal Financial Organism
echo ========================================================
echo       AetherPravah: AI that handles money better
echo ========================================================
echo.

cd /d "%~dp0"

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [*] Creating Python virtual environment...
    python -m venv .venv
    echo [*] Installing dependencies...
    .venv\Scripts\pip install -r requirements.txt
)

echo [*] Starting AetherPravah Causal Financial Organism on http://localhost:8000 ...
set PYTHONPATH=.

start "" "http://localhost:8000"

.venv\Scripts\python.exe -m uvicorn backend.api.server:app --host 0.0.0.0 --port 8000 --reload
pause
