#!/usr/bin/env bash
set -e

echo "Starting Mini-Palantir Supply Chain Intelligence Engine..."

if [ ! -f .env ]; then
  echo "No .env file found. Copying from .env.example..."
  cp .env.example .env
  echo "Update SEC_CONTACT_EMAIL in .env before live SEC scraping."
fi

echo "Installing backend dependencies..."
python3 -m pip install -q -r requirements.txt

echo "Starting backend on http://localhost:8000 ..."
(cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload) &
BACKEND_PID=$!

echo "Installing frontend dependencies..."
(cd frontend && npm install --silent)

echo "Starting frontend on http://localhost:3000 ..."
(cd frontend && REACT_APP_API_URL=http://localhost:8000 npm start) &
FRONTEND_PID=$!

echo "Press Ctrl+C to stop all services."
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true" EXIT INT TERM
wait
