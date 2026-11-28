@echo off
cd /d "%~dp0"
echo ==================================================
echo   Starting Market Intelligence AI + SME Finance
echo ==================================================
echo.

echo [1/2] Starting Unified API (FastAPI on Port 8000)...
start "Backend (Python)" cmd /k "cd /d backend && set DEBUG=false && .venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000"

echo [2/2] Starting Unified Dashboard (Next.js on Port 3000)...
start "Frontend (Next.js)" cmd /k "cd /d frontend && npm run dev -- --port 3000"

echo.
echo Both unified services are booting up in separate windows!
echo - Dashboard + SME Finance Hub: http://localhost:3000
echo - Unified API Docs:            http://localhost:8000/docs
echo.
echo Select SME Finance Hub in the sidebar to open the finance phase inside AI Analysis.
echo Close the two service windows to stop the system.
