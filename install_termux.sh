#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# GDR-AI — Automated Android Termux Installer
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================================="
echo "📱 GDR-AI — Android Termux Native Installer"
echo "=================================================================="
echo "This script configures GDR-AI on your Android phone via Termux:"
echo "  • Updates packages and installs Python, Git, and FFmpeg"
echo "  • Configures Termux:API for hardware control (Flashlight, Camera, SMS)"
echo "  • Provisions isolated virtual environment and dependencies"
echo "  • Launches interactive setup wizard with pre-filled defaults"
echo "=================================================================="
echo ""

# 1. Update Termux repositories & install core dependencies
echo "📦 Updating Termux packages..."
pkg update -y || true

echo "📦 Installing Python, Git, FFmpeg, Clang & Termux API..."
pkg install -y python git ffmpeg clang libffi openssl libjpeg-turbo termux-api cloudflared || true

# 2. Check for Termux:API App
if ! command -v termux-battery-status &> /dev/null; then
    echo "⚠️  Note: Termux:API package was installed, but please ensure you also have the"
    echo "    'Termux:API' companion app installed from F-Droid to enable hardware tools"
    echo "    (Flashlight, Camera, Battery, SMS, GPS):"
    echo "    👉 https://f-droid.org/packages/com.termux.api/"
fi

# 3. Create Virtual Environment
echo "📦 Setting up Python virtual environment..."
if [ ! -d ".venv" ]; then
    python -m venv --system-site-packages .venv
fi

VENV_PY="$SCRIPT_DIR/.venv/bin/python"
VENV_PIP="$SCRIPT_DIR/.venv/bin/pip"

# 4. Install Dependencies
echo "📦 Installing GDR-AI dependencies..."
"$VENV_PIP" install --upgrade pip setuptools wheel
"$VENV_PIP" install -e .

# 5. Provision .env if missing
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp ".env.example" ".env"
    echo "📄 Created .env from .env.example"
fi

# 6. Make scripts executable
chmod +x "$SCRIPT_DIR/run_termux.sh" "$SCRIPT_DIR/run.sh" 2>/dev/null || true

# 7. Create global 'gdr' command in Termux
if [ -n "$PREFIX" ] && [ -d "$PREFIX/bin" ]; then
    cat << EOF > "$PREFIX/bin/gdr"
#!/data/data/com.termux/files/usr/bin/bash
exec "$SCRIPT_DIR/run_termux.sh" "\$@"
EOF
    chmod +x "$PREFIX/bin/gdr"
fi

# Also add alias into ~/.bashrc
mkdir -p "$HOME"
if [ -f "$HOME/.bashrc" ]; then
    if ! grep -q 'alias gdr=' "$HOME/.bashrc" 2>/dev/null; then
        echo "alias gdr=\"$SCRIPT_DIR/run_termux.sh\"" >> "$HOME/.bashrc"
    fi
else
    echo "alias gdr=\"$SCRIPT_DIR/run_termux.sh\"" > "$HOME/.bashrc"
fi

# 8. Launch Interactive Setup Wizard
echo ""
echo "🚀 Launching Interactive Configuration Wizard..."
"$VENV_PY" -m gdr.setup_interactive || true

echo ""
echo "=================================================================="
echo "🎉 Android Termux installation complete!"
echo "=================================================================="
echo "🚀 To launch GDR-AI anytime on your Android phone, simply type:"
echo "   gdr"
echo ""
echo "The Web Dashboard will open automatically in your Android browser at:"
echo "   http://127.0.0.1:8844"
echo "=================================================================="

