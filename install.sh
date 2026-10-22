#!/usr/bin/env bash
# ==============================================================================
# Aarushi AI / GDR Agent - Universal Installer (Linux & macOS)
# Automatically configures Python, virtual environments, audio drivers & dependencies.
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================================="
echo "🌸 Aarushi AI / GDR Agent - Universal Setup & Installer"
echo "=================================================================="

OS="$(uname -s)"
echo "🖥️  Detected Operating System: $OS"

# ------------------------------------------------------------------------------
# 1. Ensure Python 3 (3.11+) is available or install it
# ------------------------------------------------------------------------------
PYTHON_BIN="$(which python3 || which python || true)"

check_python_version() {
    if [ -n "$1" ]; then
        VER="$($1 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")"
        MAJOR="$(echo "$VER" | cut -d. -f1)"
        MINOR="$(echo "$VER" | cut -d. -f2)"
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 11 ]; then
            return 0
        fi
    fi
    return 1
}

if ! check_python_version "$PYTHON_BIN"; then
    echo "⚠️  Python 3.11+ is not found. Attempting automatic installation..."
    if [ "$OS" = "Darwin" ]; then
        if ! command -v brew &>/dev/null; then
            echo "📦 Installing Homebrew package manager for macOS..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi
        echo "📦 Installing Python 3.11 & audio dependencies via Homebrew..."
        brew install python@3.11 portaudio ffmpeg
        PYTHON_BIN="$(brew --prefix)/bin/python3.11"
    elif [ -f /etc/debian_version ] || [ -f /etc/kali_version ]; then
        echo "📦 Installing Python 3.11+, audio libraries & compiler via apt..."
        sudo apt-get update -y
        sudo apt-get install -y python3 python3-pip python3-venv portaudio19-dev libasound2-dev alsa-utils ffmpeg build-essential
        PYTHON_BIN="$(which python3)"
    elif [ -f /etc/fedora-release ] || [ -f /etc/redhat-release ]; then
        echo "📦 Installing Python 3.11 & audio libraries via dnf..."
        sudo dnf install -y python3 python3-pip python3-devel portaudio-devel alsa-lib-devel ffmpeg gcc
        PYTHON_BIN="$(which python3)"
    elif [ -f /etc/arch-release ]; then
        echo "📦 Installing Python & audio libraries via pacman..."
        sudo pacman -Sy --noconfirm python python-pip portaudio alsa-lib ffmpeg base-devel
        PYTHON_BIN="$(which python3)"
    else
        echo "❌ Unsupported Linux distribution for auto-package manager. Please install Python 3.11+ manually."
        exit 1
    fi
fi

echo "✅ Using Python: $("$PYTHON_BIN" --version) at $PYTHON_BIN"

# ------------------------------------------------------------------------------
# 2. Virtual Environment Setup
# ------------------------------------------------------------------------------
if [ ! -d ".venv" ]; then
    echo "📦 Creating isolated virtual environment (.venv)..."
    "$PYTHON_BIN" -m venv .venv
else
    echo "📦 Existing virtual environment (.venv) detected."
fi

VENV_PY="$SCRIPT_DIR/.venv/bin/python"
VENV_PIP="$SCRIPT_DIR/.venv/bin/pip"

# ------------------------------------------------------------------------------
# 3. Install & Upgrade Python Dependencies
# ------------------------------------------------------------------------------
echo "📦 Installing and upgrading core packages..."
"$VENV_PIP" install --upgrade pip setuptools wheel
"$VENV_PIP" install -e .

# ------------------------------------------------------------------------------
# 4. Interactive Configuration Wizard (Pre-fills existing .env values)
# ------------------------------------------------------------------------------
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp ".env.example" ".env"
    echo "📄 Created .env from .env.example"
fi

if [ -t 0 ]; then
    "$VENV_PY" -m gdr.setup_interactive || true
else
    "$VENV_PY" -m gdr.system.compatibility || true
    "$VENV_PY" -m gdr.system.autostart repair || true
fi

# Ensure user directories exist
mkdir -p "$HOME/.config/gdr" "$HOME/.local/bin" "$HOME/.gdr/skills"

# Ensure cloudflared binary is installed for 1-click Cloudflare Tunnel sharing
if ! command -v cloudflared &>/dev/null && [ ! -f "$HOME/.local/bin/cloudflared" ]; then
    echo "☁️ Installing Cloudflare Quick Tunnel binary (cloudflared)..."
    ARCH="$(uname -m)"
    if [ "$ARCH" = "x86_64" ]; then
        curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o "$HOME/.local/bin/cloudflared" 2>/dev/null && chmod +x "$HOME/.local/bin/cloudflared" || true
    elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
        curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -o "$HOME/.local/bin/cloudflared" 2>/dev/null && chmod +x "$HOME/.local/bin/cloudflared" || true
    fi
fi

if [ ! -f "$HOME/.config/gdr/config.toml" ] && [ -f "$SCRIPT_DIR/config.example.toml" ]; then
    cp "$SCRIPT_DIR/config.example.toml" "$HOME/.config/gdr/config.toml"
    echo "⚙️  Config template placed in ~/.config/gdr/config.toml"
fi

# Create convenient CLI launcher in ~/.local/bin
cat << EOF > "$HOME/.local/bin/gdr"
#!/usr/bin/env bash
# GDR Universal Terminal Launcher
exec "$SCRIPT_DIR/run.sh" "\$@"
EOF
chmod +x "$HOME/.local/bin/gdr"

# Also try system-wide /usr/local/bin if permitted
if [ -w "/usr/local/bin" ]; then
    ln -sf "$SCRIPT_DIR/run.sh" "/usr/local/bin/gdr" 2>/dev/null || cp "$HOME/.local/bin/gdr" "/usr/local/bin/gdr" 2>/dev/null || true
elif command -v sudo &>/dev/null && sudo -n true 2>/dev/null; then
    sudo ln -sf "$SCRIPT_DIR/run.sh" "/usr/local/bin/gdr" 2>/dev/null || true
fi

# Ensure ~/.local/bin is in PATH and alias is configured across shell configs
for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
    if [ -f "$rc" ]; then
        if ! grep -q 'PATH=.*\.local/bin' "$rc" 2>/dev/null; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
        fi
        if ! grep -q 'alias gdr=' "$rc" 2>/dev/null; then
            echo "alias gdr=\"$SCRIPT_DIR/run.sh\"" >> "$rc"
        fi
    fi
done

# Ensure run.sh is executable
chmod +x "$SCRIPT_DIR/run.sh" 2>/dev/null || true

echo ""
echo "=================================================================="
echo "🎉 Installation complete!"
echo ""
echo "🚀 Type 'gdr' in ANY terminal to launch immediately:"
echo "  • Open AI Command Center:  gdr"
echo "  • Voice assistant mode:   gdr --voice"
echo "  • System diagnostics:     gdr doctor"
echo "  • Instant task prompt:    gdr \"Check system disk and status\""
echo "=================================================================="
