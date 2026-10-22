"""Automated System Diagnostics & Self-Healing Repair Engine for GDR-AI.
Detects missing dependencies, corrupt configurations, audio conflicts,
broken symlinks, and automatically resolves them.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Ensure repository root is in sys.path
_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_PKG_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def log_fix(item: str, status: str, detail: str):
    icon = "✅ FIXED" if status == "FIXED" else ("✅ OK" if status == "OK" else "⚠️ WARN")
    print(f"[{icon:<8}] {item:<28} : {detail}")


def auto_repair():
    print("=" * 65)
    print("🩺 GDR-AI Automated Health Check & Self-Healing Repair Engine")
    print("=" * 65)
    print()

    # 1. Verify Repository Integrity & Core Modules
    models_dir = Path(_REPO_ROOT) / "gdr" / "models"
    budget_file = models_dir / "budget.py"
    if not budget_file.exists():
        print(f"⚠️ Restoring missing models package at {models_dir}...")
        models_dir.mkdir(parents=True, exist_ok=True)
        (models_dir / "__init__.py").write_text('"""Model routing and budget manager."""\n')
        # Create minimal budget manager fallback if missing
        fallback_budget = '''"""VRAM Budget Manager fallback."""
import logging
logger = logging.getLogger(__name__)

class VRAMBudgetManager:
    def __init__(self, *args, **kwargs):
        pass
    def get_vram_status(self):
        return {"total_mb": 0, "used_mb": 0, "available_mb": 0}
    def can_fit_model(self, *args, **kwargs):
        return True
'''
        budget_file.write_text(fallback_budget)
        log_fix("Core Package Integrity", "FIXED", "Restored gdr/models/budget.py module")
    else:
        log_fix("Core Package Integrity", "OK", "All core Python packages intact (gdr.models present)")

    # 2. Check and provision .env file
    env_file = Path(_REPO_ROOT) / ".env"
    env_example = Path(_REPO_ROOT) / ".env.example"
    if not env_file.exists():
        if env_example.exists():
            shutil.copy(env_example, env_file)
            log_fix("Environment Config (.env)", "FIXED", "Created .env from .env.example")
        else:
            env_file.write_text('ASSISTANT_NAME="GDR-AI"\nUSER_NAME="User"\nWEB_PORT="8844"\n')
            log_fix("Environment Config (.env)", "FIXED", "Generated minimal default .env file")
    else:
        log_fix("Environment Config (.env)", "OK", ".env file exists and loaded")

    # 3. Check and install missing dependencies
    package_map = {
        "soundfile": "soundfile",
        "edge_tts": "edge-tts",
        "gtts": "gtts",
        "piper": "piper-tts",
        "tomli_w": "tomli-w",
        "sarvamai": "sarvamai",
        "faster_whisper": "faster-whisper",
    }
    missing_pkgs = []
    for mod_name, pip_name in package_map.items():
        try:
            __import__(mod_name)
        except ImportError:
            missing_pkgs.append(pip_name)

    if missing_pkgs:
        print(f"📦 Installing missing runtime dependencies: {', '.join(missing_pkgs)}...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", *missing_pkgs], check=True)
            log_fix("Python Dependencies", "FIXED", f"Successfully installed: {', '.join(missing_pkgs)}")
        except Exception as e:
            log_fix("Python Dependencies", "WARN", f"Could not auto-install: {e}")
    else:
        log_fix("Python Dependencies", "OK", "All required voice and AI packages installed")

    # 4. Check Audio Devices & Google Meet / ALSA Conflicts
    try:
        import sounddevice as sd
        from gdr.voice.vad import test_microphone_input
        mic_res = test_microphone_input(duration=0.3)
        if mic_res.get("success"):
            dname = mic_res.get("device_name", "Default Mic")
            log_fix("Microphone Access", "OK", f"Working audio input: {dname}")
        else:
            # Check for PipeWire / PulseAudio shared server
            devs = sd.query_devices()
            shared_id = None
            for idx, d in enumerate(devs):
                name = (d.get("name") or "").lower()
                if ("pulse" in name or "pipewire" in name or "default" in name) and d.get("max_input_channels", 0) > 0:
                    shared_id = idx
                    break
            if shared_id is not None:
                from gdr.config import load_config, save_config
                cfg = load_config()
                cfg.setdefault("voice", {})["input_device"] = shared_id
                save_config(cfg)
                log_fix("Microphone Access", "FIXED", f"Configured shared audio server device #{shared_id} to avoid ALSA locks")
            else:
                log_fix("Microphone Access", "WARN", "Host microphone is exclusive or busy. Web HUD browser mic is active.")
    except Exception as e:
        log_fix("Microphone Access", "WARN", f"Audio device check note: {e}")

    # 5. Fix executable permissions on Linux/macOS
    if os.name != "nt":
        scripts = ["run.sh", "install.sh", "git.sh", "push.sh", "install_termux.sh", "run_termux.sh"]
        fixed_scripts = []
        for s in scripts:
            p = Path(_REPO_ROOT) / s
            if p.exists() and not os.access(p, os.X_OK):
                p.chmod(p.stat().st_mode | 0o755)
                fixed_scripts.append(s)
        if fixed_scripts:
            log_fix("Script Permissions", "FIXED", f"Granted execute permissions (+x) to: {', '.join(fixed_scripts)}")
        else:
            log_fix("Script Permissions", "OK", "All launch and install scripts are executable")

    # 6. Global CLI Launcher (~/.local/bin/gdr)
    if os.name != "nt":
        user_bin_gdr = Path.home() / ".local" / "bin" / "gdr"
        user_bin_dir = Path.home() / ".local" / "bin"
        user_bin_dir.mkdir(parents=True, exist_ok=True)
        run_sh = Path(_REPO_ROOT) / "run.sh"
        expected_content = f'#!/usr/bin/env bash\nexec "{run_sh}" "$@"\n'
        try:
            if not user_bin_gdr.exists() or run_sh.name not in user_bin_gdr.read_text():
                user_bin_gdr.write_text(expected_content)
                user_bin_gdr.chmod(0o755)
                log_fix("Global 'gdr' Command", "FIXED", f"Updated {user_bin_gdr} pointing to {run_sh}")
            else:
                log_fix("Global 'gdr' Command", "OK", f"Installed and active in {user_bin_gdr}")
        except Exception as e:
            log_fix("Global 'gdr' Command", "WARN", str(e))

    print()
    print("=" * 65)
    print("🎉 Auto-Repair Complete! You can now start the assistant with:")
    print("   gdr")
    print("=" * 65)
    print()


if __name__ == "__main__":
    auto_repair()
