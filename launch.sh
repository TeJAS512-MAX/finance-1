#!/bin/bash
echo "========================================================"
echo "      AetherPravah: AI that handles money better        "
echo "      Full Attractive 3D Web Experience + Causal Engine "
echo "========================================================"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ ! -d ".venv" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv .venv
    echo "[*] Installing backend dependencies..."
    .venv/bin/pip install -r requirements.txt
fi

export PYTHONPATH=.

echo "[*] Starting Python Causal Engine (port 8001)..."
.venv/bin/python3 -m uvicorn backend.api.server:app --host 127.0.0.1 --port 8001 &

echo "[*] Starting Next.js 3D Web Experience (port 3001)..."
export NEXT_PUBLIC_AETHER_API_URL=http://localhost:8001
export NEXT_PUBLIC_MARKET_APP_URL=http://localhost:3000
cd frontend
npm run dev -- --port 3001
