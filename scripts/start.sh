#!/usr/bin/env bash
# ==============================================================================
# BlockBrain AI // All-in-One Launcher (Python Backend + Flutter Desktop HUD)
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "⚡ Initializing BlockBrain AI (Jarvis Engine + Flutter HUD)..."

# 1. Start Python Backend in background
echo "🧠 Starting Python Brain on http://127.0.0.1:8844 ..."
PY_BIN="python3"
if [ -f "$REPO_ROOT/.venv/bin/python" ]; then
    PY_BIN="$REPO_ROOT/.venv/bin/python"
fi
PYTHONPATH="$REPO_ROOT" "$PY_BIN" "$REPO_ROOT/backend/run_backend.py" &
BACKEND_PID=$!

# Ensure backend terminates when script exits
trap "echo '🛑 Stopping BlockBrain Python Brain...'; kill $BACKEND_PID 2>/dev/null || true" EXIT

# 2. Wait for backend to be healthy
echo "⏳ Waiting for backend health check..."
for i in {1..30}; do
    if curl -s http://127.0.0.1:8844/api/status >/dev/null 2>&1; then
        echo "✅ BlockBrain Brain is ONLINE and ready!"
        break
    fi
    sleep 0.5
done

# 3. Compile native stealth hook if not compiled
if [ ! -f "$REPO_ROOT/native_hooks/linux_x11_cloak/libstealthcloak.so" ]; then
    echo "🔨 Compiling libstealthcloak.so ..."
    make -C "$REPO_ROOT/native_hooks/linux_x11_cloak"
fi

# 4. Launch Flutter Desktop HUD
echo "🚀 Launching BlockBrain Flutter Desktop HUD..."
# Kill any lingering previous instance to ensure fresh UI
pkill -9 -f "bundle/blockbrain_hud" 2>/dev/null || true
sleep 0.5

export GDK_BACKEND=x11
if [ -f "$REPO_ROOT/frontend/build/linux/x64/debug/bundle/blockbrain_hud" ]; then
    "$REPO_ROOT/frontend/build/linux/x64/debug/bundle/blockbrain_hud"
else
    cd "$REPO_ROOT/frontend"
    flutter run -d linux
fi
