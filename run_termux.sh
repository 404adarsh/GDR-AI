#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# GDR-AI — Android Termux Launcher
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONPATH="$SCRIPT_DIR:${PYTHONPATH:-}"

if [ ! -d ".venv" ] || [ ! -f ".venv/bin/python" ]; then
    echo "⚠️ Virtual environment not detected. Running Termux installer first..."
    bash "$SCRIPT_DIR/install_termux.sh"
fi

VENV_PY="$SCRIPT_DIR/.venv/bin/python"

AI_NAME="$(grep -E "^ASSISTANT_NAME=" .env 2>/dev/null | cut -d'=' -f2 | tr -d '\"'"'" || echo "GDR-AI")"
AI_NAME="${AI_NAME:-GDR-AI}"

echo "=================================================================="
echo "📱 Starting ${AI_NAME} on Android (Termux)..."
echo "=================================================================="
echo "Dashboard running at:"
echo "   👉 Local: http://127.0.0.1:8844"
echo "=================================================================="

# Open in default Android browser if termux-open-url is available
if [ $# -eq 0 ]; then
    if command -v termux-open-url &> /dev/null; then
        (sleep 2 && termux-open-url "http://127.0.0.1:8844") &
    fi
    exec "$VENV_PY" -m gdr.cli --gui
else
    exec "$VENV_PY" -m gdr.cli "$@"
fi
