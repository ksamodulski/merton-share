#!/bin/bash

# Merton Share - start backend + frontend (detached).
# Use ./stop.sh to stop, ./restart.sh to restart.

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"
RUN_DIR="$PROJECT_ROOT/.run"
BACKEND_PORT=8000
FRONTEND_PORT=5173

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "$RUN_DIR"

# Prerequisites
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}Error: python3 not found${NC}"; exit 1; }
command -v node >/dev/null 2>&1   || { echo -e "${RED}Error: node not found${NC}"; exit 1; }

# Don't double-start
port_in_use() {
    if command -v fuser >/dev/null 2>&1; then
        fuser "${1}/tcp" >/dev/null 2>&1
    else
        lsof -ti "tcp:${1}" >/dev/null 2>&1
    fi
}
if port_in_use "$BACKEND_PORT" || port_in_use "$FRONTEND_PORT"; then
    echo -e "${YELLOW}A server is already running on :$BACKEND_PORT or :$FRONTEND_PORT.${NC}"
    echo -e "${YELLOW}Use ./restart.sh to restart, or ./stop.sh first.${NC}"
    exit 1
fi

# .env
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo -e "${YELLOW}No .env found — copying from .env.example...${NC}"
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo -e "${YELLOW}Edit $BACKEND_DIR/.env and add your Anthropic API key.${NC}"
fi

# Backend
echo -e "${GREEN}Starting backend...${NC}"
cd "$BACKEND_DIR"
[ -d venv ] || { echo -e "${YELLOW}Creating venv...${NC}"; python3 -m venv venv; }
# shellcheck disable=SC1091
source venv/bin/activate
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}Installing backend dependencies...${NC}"
    pip install -r requirements.txt
fi
setsid uvicorn app.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" \
    > "$RUN_DIR/backend.log" 2>&1 < /dev/null &
echo $! > "$RUN_DIR/backend.pid"
echo -e "${GREEN}Backend started (PID $(cat "$RUN_DIR/backend.pid"), log: .run/backend.log)${NC}"

# Frontend
echo -e "${GREEN}Starting frontend...${NC}"
cd "$FRONTEND_DIR"
[ -d node_modules ] || { echo -e "${YELLOW}Installing frontend dependencies...${NC}"; npm install; }
setsid npm run dev > "$RUN_DIR/frontend.log" 2>&1 < /dev/null &
echo $! > "$RUN_DIR/frontend.pid"
echo -e "${GREEN}Frontend started (PID $(cat "$RUN_DIR/frontend.pid"), log: .run/frontend.log)${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Merton Share is running!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Frontend: ${YELLOW}http://localhost:${FRONTEND_PORT}${NC}"
echo -e "Backend:  ${YELLOW}http://localhost:${BACKEND_PORT}${NC}"
echo -e "API Docs: ${YELLOW}http://localhost:${BACKEND_PORT}/docs${NC}"
echo ""
echo -e "Logs:  ${YELLOW}tail -f .run/backend.log .run/frontend.log${NC}"
echo -e "Stop:  ${YELLOW}./stop.sh${NC}"
