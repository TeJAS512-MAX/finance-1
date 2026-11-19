Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "      AetherPravah: AI that handles money better        " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[*] Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "[*] Installing dependencies..." -ForegroundColor Yellow
    .venv\Scripts\pip install -r requirements.txt
}

$env:PYTHONPATH = "."

Write-Host "[*] Launching browser at http://localhost:8000 ..." -ForegroundColor Green
Start-Process "http://localhost:8000"

Write-Host "[*] Starting Uvicorn Server..." -ForegroundColor Cyan
& .venv\Scripts\python.exe -m uvicorn backend.api.server:app --host 0.0.0.0 --port 8000 --reload
