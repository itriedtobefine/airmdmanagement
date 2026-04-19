#!/bin/bash

# TODO App Setup Script
# This script sets up the PostgreSQL database and starts the backend server

set -e

echo "========================================="
echo "TODO App Setup Script"
echo "========================================="

# Configuration
DB_NAME="${POSTGRES_DB:-todo_db}"
DB_USER="${POSTGRES_USER:-postgres}"
DB_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Configuration:${NC}"
echo "  Database: $DB_NAME"
echo "  User: $DB_USER"
echo "  Host: $DB_HOST:$DB_PORT"
echo ""

# Check if PostgreSQL client is available
if command -v psql &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL client found${NC}"
else
    echo -e "${YELLOW}⚠ PostgreSQL client not found. Please ensure PostgreSQL is installed.${NC}"
fi

# Set environment variable for the application
export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo ""
echo -e "${YELLOW}Database URL configured${NC}"

# Try to create database if it doesn't exist (requires psql)
if command -v psql &> /dev/null; then
    echo -e "${YELLOW}Attempting to create database...${NC}"
    
    # Create database if it doesn't exist
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d postgres -tc \
        "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d postgres -c \
        "CREATE DATABASE $DB_NAME"
    
    echo -e "${GREEN}✓ Database ready${NC}"
else
    echo -e "${YELLOW}Skipping database creation (psql not available). Please create database manually:${NC}"
    echo "  CREATE DATABASE $DB_NAME;"
fi

echo ""
echo "========================================="
echo "Starting FastAPI Backend..."
echo "========================================="
echo ""
echo "API will be available at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the FastAPI server
cd "$(dirname "$0")"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
