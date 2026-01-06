#!/bin/bash

# Merton Share - Development Server Startup Script

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Merton Share...${NC}"
echo ""

# Check prerequisites
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 not found${NC}"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: node not found${NC}"
    exit 1
fi

# Check for .env file
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo -e "${YELLOW}Warning: No .env file found. Copying from .env.example...${NC}"
    if [ -f "$BACKEND_DIR/.env.example" ]; then
        cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
        echo -e "${YELLOW}Please edit $BACKEND_DIR/.env and add your Anthropic API key${NC}"
    else
        echo -e "${RED}Error: No .env.example found${NC}"
        exit 1
    fi
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo -e "${GREEN}Servers stopped.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${GREEN}Starting backend server...${NC}"
cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

source venv/bin/activate

# Check if dependencies are installed
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing backend dependencies...${NC}"
    pip install -r requirements.txt
fi

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo -e "${GREEN}Backend started (PID: $BACKEND_PID)${NC}"

# Start frontend
echo -e "${GREEN}Starting frontend server...${NC}"
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    npm install
fi

npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend started (PID: $FRONTEND_PID)${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Merton Share is running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Frontend: ${YELLOW}http://localhost:5173${NC}"
echo -e "Backend:  ${YELLOW}http://localhost:8000${NC}"
echo -e "API Docs: ${YELLOW}http://localhost:8000/docs${NC}"
echo ""
echo -e "Press ${RED}Ctrl+C${NC} to stop both servers"
echo ""

# Wait for both processes
wait
