#!/bin/bash

# Merton Share - stop backend + frontend.
# Kills by listening port so uvicorn's reloader parent AND its worker child
# (and the vite process tree) are all caught — more reliable than pkill -f.

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
RUN_DIR="$PROJECT_ROOT/.run"
BACKEND_PORT=8000
FRONTEND_PORT=5173

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

kill_port() {
    local port=$1 name=$2
    if command -v fuser >/dev/null 2>&1; then
        if fuser -k "${port}/tcp" >/dev/null 2>&1; then
            echo -e "${GREEN}Stopped ${name} (:${port})${NC}"
        else
            echo -e "${YELLOW}${name} (:${port}) not running${NC}"
        fi
    elif command -v lsof >/dev/null 2>&1; then
        local pids
        pids=$(lsof -ti "tcp:${port}" 2>/dev/null)
        if [ -n "$pids" ]; then
            kill -9 $pids 2>/dev/null
            echo -e "${GREEN}Stopped ${name} (:${port})${NC}"
        else
            echo -e "${YELLOW}${name} (:${port}) not running${NC}"
        fi
    else
        echo "Neither fuser nor lsof available; cannot kill by port." >&2
        return 1
    fi
}

kill_port "$BACKEND_PORT" backend
kill_port "$FRONTEND_PORT" frontend

rm -f "$RUN_DIR"/*.pid 2>/dev/null || true
