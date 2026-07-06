#!/usr/bin/env bash
# Launch the DocLens backend from its virtualenv (creating it on first run).
set -euo pipefail

cd "$(dirname "$0")/../backend"

if [ ! -d venv ]; then
  echo "Creating backend virtualenv..."
  python3 -m venv venv
  ./venv/bin/pip install --upgrade pip
  ./venv/bin/pip install -r requirements.txt
fi

exec ./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
