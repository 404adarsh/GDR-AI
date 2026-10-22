#!/usr/bin/env bash
# ==============================================================================
# GDR-AI One-Click Auto-Repair Script (Linux & macOS)
# ==============================================================================
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"

if [ -f ".venv/bin/python" ]; then
    exec .venv/bin/python -m gdr.repair "$@"
else
    exec python3 -m gdr.repair "$@"
fi

