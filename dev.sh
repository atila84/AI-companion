#!/usr/bin/env bash
# Starts the backend and frontend dev servers together, in one terminal.
# Ctrl+C stops both. See USAGE.md for manual (two-terminal) instructions
# and troubleshooting.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

check_port() {
  if port_in_use "$1"; then
    echo "ERROR: port $1 is already in use (needed for $2)." >&2
    echo "  See what's using it: lsof -nP -iTCP:$1 -sTCP:LISTEN" >&2
    echo "  Stop it with: kill <PID>" >&2
    exit 1
  fi
}

check_port 8000 backend
check_port 5173 frontend

[ -d "$BACKEND_DIR/.venv" ] || {
  echo "ERROR: backend/.venv not found. One-time setup:" >&2
  echo "  cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt" >&2
  exit 1
}

[ -f "$BACKEND_DIR/.env" ] || {
  echo "ERROR: backend/.env not found. Run:" >&2
  echo "  cp backend/.env.example backend/.env" >&2
  echo "  then edit it and set your real ANTHROPIC_API_KEY." >&2
  exit 1
}

[ -d "$FRONTEND_DIR/node_modules" ] || {
  echo "ERROR: frontend/node_modules not found. Run:" >&2
  echo "  cd frontend && npm install" >&2
  exit 1
}

if grep -q "sk-ant-your-key-here" "$BACKEND_DIR/.env"; then
  echo "WARNING: backend/.env still has the placeholder ANTHROPIC_API_KEY." >&2
  echo "  Chat requests will fail with 401 until you set a real key and restart." >&2
fi

cleanup() {
  echo ""
  echo "Stopping backend and frontend..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

(cd "$BACKEND_DIR" && source .venv/bin/activate && exec python -m uvicorn src.main:app --reload --port 8000) &
BACKEND_PID=$!

(cd "$FRONTEND_DIR" && exec npm run dev) &
FRONTEND_PID=$!

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop both."
echo ""

wait
