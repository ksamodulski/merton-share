#!/bin/bash

# Merton Share - restart backend + frontend (stop, then start).

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

"$PROJECT_ROOT/stop.sh"
sleep 1
exec "$PROJECT_ROOT/start.sh"
