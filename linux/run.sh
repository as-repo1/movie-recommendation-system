#!/usr/bin/env bash
# linux/run.sh — Launch RecLens Native Linux Application

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

if [ -f ".venv/bin/python" ]; then
    PYTHON_EXEC=".venv/bin/python"
else
    PYTHON_EXEC="python3"
fi

export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

echo "🚀 Launching RecLens Native GTK4/Libadwaita Linux App..."
exec "$PYTHON_EXEC" "$SCRIPT_DIR/app/main.py" "$@"
