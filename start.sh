#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=================================================="
echo " Starting VideoManager (Backend & Frontend)"
echo "=================================================="

# Check Python virtualenv
if [ ! -d "backend/venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv backend/venv
fi

# Activate venv
source backend/venv/bin/activate

# Install backend dependencies if not installed
echo "Checking backend dependencies..."
pip install -r backend/requirements.txt -q

# Install frontend dependencies if needed
if [ ! -d "frontend/node_modules" ]; then
    echo "Installing frontend dependencies..."
    (cd "$DIR/frontend" && npm install --cache /tmp/.npm-cache)
fi

# Build frontend production bundle for FastAPI static serving
echo "Building frontend..."
(cd "$DIR/frontend" && npm run build)

echo ""
echo "🚀 Starting VideoManager Server on http://localhost:8000..."
echo "Press Ctrl+C to stop."
echo ""

# Run uvicorn inside backend
cd "$DIR/backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
