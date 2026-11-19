#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "========================================================"
echo "      AetherPravah: AI that handles money better        "
echo "========================================================"

if [ ! -f ".venv/bin/python" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv .venv
    echo "[*] Installing dependencies..."
    .venv/bin/pip install -r requirements.txt
fi

export PYTHONPATH="."

echo "[*] Opening http://localhost:8000 ..."
if which xdg-open > /dev/null; then
    xdg-open "http://localhost:8000" &
elif which open > /dev/null; then
    open "http://localhost:8000" &
fi

echo "[*] Starting Uvicorn Server..."
.venv/bin/python -m uvicorn backend.api.server:app --host 0.0.0.0 --port 8000 --reload
