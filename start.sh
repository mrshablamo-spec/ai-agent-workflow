#!/usr/bin/env bash
set -e

echo "🚀 Starting NEXUS Intelligence Platform..."

# Check .env
if [ ! -f .env ]; then
  echo "⚠️  No .env file found. Copying from .env.example..."
  cp .env.example .env
  echo "   → Please edit .env with your API keys before continuing."
  exit 1
fi

# Start backend
echo "📡 Starting FastAPI backend on port 8000..."
cd backend
pip install -q -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Start frontend
echo "🖥️  Starting React frontend on port 3000..."
cd frontend
npm install --silent
REACT_APP_API_URL=http://localhost:8000 npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ NEXUS is running!"
echo "   Frontend: http://localhost:3000"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services."

# Wait for Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '🛑 Stopped.'" EXIT INT TERM
wait
