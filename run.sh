#!/usr/bin/env bash
# ==============================================================================
# Aarushi AI / GDR Agent - Quick Launcher (Linux & macOS)
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"
export GDR_CONFIG_DIR="${GDR_CONFIG_DIR:-$HOME/.config/gdr}"

if [ ! -d ".venv" ] || [ ! -f ".venv/bin/python" ]; then
    echo "⚠️ Virtual environment not detected. Running installer first..."
    bash "$SCRIPT_DIR/install.sh"
fi

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp ".env.example" ".env"
    echo "📄 Generated default .env file."
fi

VENV_PY="$SCRIPT_DIR/.venv/bin/python"

AI_NAME="$(grep -E "^ASSISTANT_NAME=" .env 2>/dev/null | cut -d'=' -f2 | tr -d '\"'"'" || echo "GDR-AI")"
AI_NAME="${AI_NAME:-GDR-AI}"

if [ $# -eq 0 ]; then
    echo "🌸 Starting Aarushi Desktop Companion at http://127.0.0.1:8844/call ..."
    exec "$VENV_PY" -m gdr.cli --call
else
    exec "$VENV_PY" -m gdr.cli "$@"
fi

