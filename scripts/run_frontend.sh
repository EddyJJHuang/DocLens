#!/usr/bin/env bash
# Launch the DocLens frontend dev server (installing deps on first run).
set -euo pipefail

cd "$(dirname "$0")/../frontend"

[ -d node_modules ] || npm install

exec npm run dev
