#!/bin/bash
# TimeTracker Pro - Setup Script
# This script sets up the development environment for TimeTracker Pro

set -e

echo "=========================================="
echo "TimeTracker Pro - Setup Script"
echo "=========================================="

# Check disk space
echo ""
echo "Checking disk space..."
AVAILABLE_SPACE=$(df -m / | awk 'NR==2 {print $4}')
if [ "$AVAILABLE_SPACE" -lt 100 ]; then
    echo "WARNING: Less than 100MB available on disk. Setup may fail."
else
    echo "✓ Disk space OK: ${AVAILABLE_SPACE}MB available"
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check Python
echo ""
echo "Checking Python installation..."
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version)
    echo "✓ $PYTHON_VERSION found"
else
    echo "✗ Python 3 not found. Please install Python 3.10+"
    exit 1
fi

# Check Node.js
echo ""
echo "Checking Node.js installation..."
if command_exists node; then
    NODE_VERSION=$(node --version)
    echo "✓ $NODE_VERSION found"
else
    echo "✗ Node.js not found. Please install Node.js 18+"
    exit 1
fi

# Setup backend
echo ""
echo "=========================================="
echo "Setting up Backend..."
echo "=========================================="

cd "$(dirname "$0")/backend"

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies with binary preference
echo "Installing Python dependencies..."
pip install --prefer-binary --only-binary :all: -r requirements.txt 2>&1 || {
    echo "Some packages may require compilation. Trying without binary-only flag..."
    pip install -r requirements.txt
}

# Clear pip cache to save space
echo "Clearing pip cache..."
pip cache purge 2>/dev/null || true

cd ..

# Setup frontend
echo ""
echo "=========================================="
echo "Setting up Frontend..."
echo "=========================================="

cd "$(dirname "$0")/frontend"

# Install npm dependencies
echo "Installing npm dependencies..."
npm install

cd ..

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Make sure PostgreSQL is running"
echo "2. Create database: createdb timetracker_db"
echo "3. Start backend: cd backend && source venv/bin/activate && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"
echo "4. Start frontend: cd frontend && npm run dev"
echo ""
echo "Or use the run.sh script to start both services."
