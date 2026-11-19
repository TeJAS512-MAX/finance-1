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

Write-Host "[*] Starting Python Causal Engine (port 8000)..." -ForegroundColor Cyan
Start-Process -FilePath ".venv\Scripts\python.exe" -ArgumentList "-m uvicorn backend.api.server:app --host 0.0.0.0 --port 8000" -WindowStyle Hidden

Write-Host "[*] Starting Next.js 3D Web Experience (port 3000)..." -ForegroundColor Green
Set-Location "$ScriptDir\frontend"
Start-Process "http://localhost:3000"
npm run dev
