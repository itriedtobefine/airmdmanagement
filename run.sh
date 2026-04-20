#!/bin/bash
# TimeTracker Pro - Run Script
# Starts both backend and frontend services

set -e

echo "=========================================="
echo "TimeTracker Pro - Starting Services"
echo "=========================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Kill any existing processes on our ports
echo "Cleaning up existing processes..."
pkill -f "uvicorn.*8000" 2>/dev/null || true
pkill -f "vite.*3000" 2>/dev/null || true
sleep 1

# Start backend
echo ""
echo "Starting Backend on port 8000..."
cd backend
source venv/bin/activate
nohup uvicorn backend.main:app --host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"
cd ..

# Wait for backend to start
echo "Waiting for backend to initialize..."
sleep 3

# Check if backend is running
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Backend is running"
else
    echo "⚠ Backend may still be starting. Check /tmp/backend.log for details."
fi

# Start frontend
echo ""
echo "Starting Frontend on port 3000..."
cd frontend
nohup npm run dev > /tmp/frontend.log 2>&1 &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"
cd ..

echo ""
echo "=========================================="
echo "Services Started!"
echo "=========================================="
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "To stop services: pkill -f 'uvicorn|vite'"
echo "Logs:"
echo "  Backend:  /tmp/backend.log"
echo "  Frontend: /tmp/frontend.log"
