Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      AetherPravah: AI that handles money better        " -ForegroundColor Green
Write-Host "      Full Attractive 3D Web Experience + Causal Engine " -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[*] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "[*] Installing backend dependencies..." -ForegroundColor Yellow
    .venv\Scripts\pip install -r requirements.txt
}

$env:PYTHONPATH = "."

Write-Host "[*] Starting Python Causal Engine (port 8001)..." -ForegroundColor Cyan
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m uvicorn backend.api.server:app --host 127.0.0.1 --port 8001" -WindowStyle Hidden

Write-Host "[*] Starting Next.js 3D Web Experience (port 3001)..." -ForegroundColor Green
$env:NEXT_PUBLIC_AETHER_API_URL = "http://localhost:8001"
$env:NEXT_PUBLIC_MARKET_APP_URL = "http://localhost:3000"
Set-Location "$ScriptDir\frontend"
Start-Process "http://localhost:3001"
npm run dev -- --port 3001
