#!/bin/bash
# RoadGuard AI - start the backend and the new frontend (frontend-v2) locally.
# Double-click in Finder, or run:  ./run_local.command
# Ctrl+C in this window stops both.

ROOT="$(cd "$(dirname "$0")" && pwd)"
LOGDIR="$ROOT/.run_logs"
mkdir -p "$LOGDIR"
API_PORT=8000
WEB_PORT=5173

say() { printf "\n\033[1;34m==> %s\033[0m\n" "$1"; }
fail() { printf "\n\033[1;31mERROR: %s\033[0m\n" "$1"; read -r -p "Press Return to close."; exit 1; }

# ---------------------------------------------------------------- backend --
cd "$ROOT/backend" || fail "backend/ not found"
[ -f .env ] || fail "backend/.env is missing (copy .env.example or .env.aiven.example)."

if [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
elif python3 -c "import fastapi, uvicorn, ultralytics, sqlalchemy, asyncpg, bcrypt, jwt, reportlab" 2>/dev/null; then
  PY=python3
else
  say "First run: creating backend/.venv and installing requirements (a few minutes, PyTorch is large)"
  python3 -m venv .venv || fail "python3 -m venv failed - is Python 3.11+ installed?"
  .venv/bin/pip install --upgrade pip >/dev/null
  .venv/bin/pip install -r requirements.txt || fail "pip install -r requirements.txt failed"
  PY=.venv/bin/python
fi
say "Backend: using $($PY --version 2>&1) ($PY)"

if lsof -ti tcp:$API_PORT >/dev/null 2>&1; then
  say "Port $API_PORT already in use - assuming the backend is already running"
  API_PID=""
else
  "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port $API_PORT > "$LOGDIR/backend.log" 2>&1 &
  API_PID=$!
fi

say "Waiting for the API (loading the YOLO model)..."
for i in $(seq 1 90); do
  if curl -s "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1; then break; fi
  if [ -n "$API_PID" ] && ! kill -0 $API_PID 2>/dev/null; then
    tail -30 "$LOGDIR/backend.log"; fail "Backend exited - see .run_logs/backend.log"
  fi
  sleep 1
done
curl -s "http://127.0.0.1:$API_PORT/health" | "$PY" -c 'import json,sys; h=json.load(sys.stdin); print("   status:", h["status"], "| model:", h["model"]["version"], "| database:", h["persistence"])' \
  || fail "API did not answer on :$API_PORT - see .run_logs/backend.log"

# --------------------------------------------------------------- frontend --
cd "$ROOT/frontend-v2" || fail "frontend-v2/ not found"
command -v npm >/dev/null || fail "npm not found - install Node.js 18+ from nodejs.org"
if [ ! -d node_modules ]; then
  say "First run: npm install in frontend-v2"
  npm install --no-audit --no-fund || fail "npm install failed"
fi
npx vite --port $WEB_PORT --strictPort > "$LOGDIR/frontend.log" 2>&1 &
WEB_PID=$!

cleanup() {
  say "Stopping..."
  [ -n "$WEB_PID" ] && kill $WEB_PID 2>/dev/null
  [ -n "$API_PID" ] && kill $API_PID 2>/dev/null
  exit 0
}
trap cleanup INT TERM

for i in $(seq 1 30); do
  curl -s "http://localhost:$WEB_PORT" >/dev/null 2>&1 && break
  kill -0 $WEB_PID 2>/dev/null || { tail -20 "$LOGDIR/frontend.log"; fail "Frontend exited - see .run_logs/frontend.log"; }
  sleep 1
done

say "RoadGuard AI is running"
echo "   App:      http://localhost:$WEB_PORT"
echo "   API:      http://localhost:$API_PORT   (docs: http://localhost:$API_PORT/docs)"
echo "   Logs:     .run_logs/backend.log, .run_logs/frontend.log"
echo "   Stop:     Ctrl+C in this window"
open "http://localhost:$WEB_PORT"
wait
