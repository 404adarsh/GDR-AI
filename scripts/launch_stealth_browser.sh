#!/usr/bin/env bash
# ==============================================================================
# Stealth Browser Launcher with X11 Anti-Capture Hook
# Ensures that Google Meet, Zoom, or Discord running in Chrome CANNOT see
# the BlockBrain HUD during screen sharing!
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOK_LIB="$REPO_ROOT/native_hooks/linux_x11_cloak/libstealthcloak.so"

if [ ! -f "$HOOK_LIB" ]; then
    echo "🔨 Compiling libstealthcloak.so ..."
    make -C "$REPO_ROOT/native_hooks/linux_x11_cloak"
fi

BROWSER=""
for b in google-chrome-stable google-chrome chromium chromium-browser firefox; do
    if command -v "$b" >/dev/null 2>&1; then
        BROWSER="$b"
        break
    fi
done

if [ -z "$BROWSER" ]; then
    echo "❌ No supported browser found."
    exit 1
fi

echo "🛡️ Launching $BROWSER with Screen-Share Invisibility Hook active..."
echo "👁️ Any screen share (Google Meet / Zoom / Discord) in this browser will NOT see BlockBrain HUD!"

LD_PRELOAD="$HOOK_LIB" "$BROWSER" "$@" &
