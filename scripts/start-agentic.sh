#!/usr/bin/env bash
# Start the agentic LangGraph backend (port 5003) and frontend (port 5000).
# Requires .env in the project root with Azure OpenAI credentials.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
    echo "[WARN] No .env found. Copy .env.example to .env and fill in your keys."
fi

( cd backend  && python agentic_api.py ) &
BACKEND_PID=$!
( cd frontend && python app.py ) &
FRONTEND_PID=$!

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT INT TERM

echo
echo "Backend (agentic):   http://localhost:5003/api/health"
echo "Frontend (review):   http://localhost:5000/"
wait
