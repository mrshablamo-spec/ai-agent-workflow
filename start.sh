#!/usr/bin/env bash
set -e

echo "Starting Mini-Palantir Supply Chain Intelligence website..."

if [ ! -f .env ]; then
  echo "No .env file found. Copying from .env.example..."
  cp .env.example .env
  echo "Update SEC_CONTACT_EMAIL in .env before live SEC scraping."
fi

echo "Installing backend dependencies..."
python3 -m pip install -q -r requirements.txt

echo "Installing frontend dependencies..."
(cd frontend && npm install --silent)

echo "Building frontend website..."
(cd frontend && REACT_APP_API_URL=http://localhost:8000 npm run build >/dev/null)

echo "Starting website on http://localhost:8000 ..."
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
