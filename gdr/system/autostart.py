"""Cross-Platform Autostart Management for Aarushi AI.
Supports per-user autostart on Linux (systemd user unit & XDG desktop entry),
macOS (LaunchAgent plist), and Windows (Startup folder shortcut / launcher).
Provides status detection, interactive configuration with remembered preference,
enabling, disabling, and repairing.
"""

from datetime import datetime
import json
import logging
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("gdr.system.autostart")


def get_config_dir() -> Path:
    return Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr"))


def get_autostart_state_file() -> Path:
    return get_config_dir() / "autostart_state.json"


CONFIG_DIR = get_config_dir()
AUTOSTART_STATE_FILE = get_autostart_state_file()


def _get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _get_launcher_path() -> Path:
    root = _get_project_root()
    system = platform.system().lower()
    if system == "windows":
        run_bat = root / "run.bat"
        if run_bat.exists():
            return run_bat
    run_sh = root / "run.sh"
    if run_sh.exists():
        return run_sh
    # Fallback to python entrypoint
    venv_py = root / ".venv" / "bin" / "python"
    if not venv_py.exists():
        venv_py = root / ".venv" / "Scripts" / "python.exe"
    return venv_py if venv_py.exists() else Path(sys.executable)


def _load_saved_preference() -> Optional[bool]:
    """Read saved preference from state file or config."""
    try:
        state_file = get_autostart_state_file()
        if state_file.exists():
            with open(state_file, "r") as f:
                data = json.load(f)
                return data.get("enabled")
    except Exception:
        pass
    return None


def _save_preference(enabled: bool, mechanism: str, target_path: str):
    """Persist preference and autostart metadata."""
    try:
        cfg_dir = get_config_dir()
        cfg_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "enabled": enabled,
            "mechanism": mechanism,
            "target_path": str(target_path),
            "platform": platform.system().lower(),
            "updated_at": datetime.now().isoformat()
        }
        state_file = get_autostart_state_file()
        with open(state_file, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to save autostart state: {e}")


# ==============================================================================
# Platform Implementations
# ==============================================================================

class _LinuxAutostartMeta(type):
    _xdg_dir: Optional[Path] = None
    _desktop_file: Optional[Path] = None
    _systemd_dir: Optional[Path] = None
    _service_file: Optional[Path] = None

    @property
    def XDG_DIR(cls) -> Path:
        return cls._xdg_dir if cls._xdg_dir is not None else cls.get_xdg_dir()

    @XDG_DIR.setter
    def XDG_DIR(cls, val: Optional[Path]) -> None:
        cls._xdg_dir = val

    @property
    def DESKTOP_FILE(cls) -> Path:
        return cls._desktop_file if cls._desktop_file is not None else cls.get_desktop_file()

    @DESKTOP_FILE.setter
    def DESKTOP_FILE(cls, val: Optional[Path]) -> None:
        cls._desktop_file = val

    @property
    def SYSTEMD_DIR(cls) -> Path:
        return cls._systemd_dir if cls._systemd_dir is not None else cls.get_systemd_dir()

    @SYSTEMD_DIR.setter
    def SYSTEMD_DIR(cls, val: Optional[Path]) -> None:
        cls._systemd_dir = val

    @property
    def SERVICE_FILE(cls) -> Path:
        return cls._service_file if cls._service_file is not None else cls.get_service_file()

    @SERVICE_FILE.setter
    def SERVICE_FILE(cls, val: Optional[Path]) -> None:
        cls._service_file = val


class LinuxAutostart(metaclass=_LinuxAutostartMeta):
    @classmethod
    def get_xdg_dir(cls) -> Path:
        if cls._xdg_dir is not None:
            return cls._xdg_dir
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "autostart"

    @classmethod
    def get_desktop_file(cls) -> Path:
        if cls._desktop_file is not None:
            return cls._desktop_file
        return cls.get_xdg_dir() / "gdr-aarushi.desktop"

    @classmethod
    def get_systemd_dir(cls) -> Path:
        if cls._systemd_dir is not None:
            return cls._systemd_dir
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        return base / "systemd" / "user"

    @classmethod
    def get_service_file(cls) -> Path:
        if cls._service_file is not None:
            return cls._service_file
        return cls.get_systemd_dir() / "gdr-aarushi.service"

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        desktop_file = cls.get_desktop_file()
        service_file = cls.get_service_file()
        has_desktop = desktop_file.exists()
        has_service = service_file.exists()
        saved = _load_saved_preference()
        enabled = (has_desktop or has_service) if saved is None else saved
        mech = "xdg_desktop" if has_desktop else ("systemd_user" if has_service else "none")
        target = str(desktop_file if has_desktop else (service_file if has_service else ""))
        return {
            "enabled": bool(enabled and (has_desktop or has_service or saved)),
            "installed": bool(has_desktop or has_service),
            "mechanism": mech,
            "path": target,
            "platform": "linux"
        }

    @classmethod
    def enable(cls) -> bool:
        launcher = _get_launcher_path()
        root = _get_project_root()
        xdg_dir = cls.get_xdg_dir()
        desktop_file = cls.get_desktop_file()

        try:
            xdg_dir.mkdir(parents=True, exist_ok=True)
            desktop_content = f"""[Desktop Entry]
Type=Application
Name=Aarushi AI Companion
Comment=Personal AI Companion Calling Application
Exec="{launcher}" --call
# Aarushi companion mode options: --call, --background
Path="{root}"
Terminal=false
Categories=Utility;Development;AudioVideo;
X-GNOME-Autostart-enabled=true
"""
            desktop_file.write_text(desktop_content)
            desktop_file.chmod(0o755)
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not write desktop entry to {desktop_file}: {e}")

        # Also write systemd user unit if directory is available
        try:
            systemd_dir = cls.get_systemd_dir()
            service_file = cls.get_service_file()
            systemd_dir.mkdir(parents=True, exist_ok=True)
            service_content = f"""[Unit]
Description=Aarushi AI Companion Background Service
After=network.target

[Service]
Type=simple
WorkingDirectory={root}
ExecStart="{launcher}" --background
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=default.target
"""
            service_file.write_text(service_content)
            # Try systemctl enable if systemd user daemon is active
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
            subprocess.run(["systemctl", "--user", "enable", "gdr-aarushi.service"], capture_output=True)
        except Exception:
            pass

        _save_preference(True, "xdg_desktop", str(desktop_file))
        return True

    @classmethod
    def disable(cls) -> bool:
        desktop_file = cls.get_desktop_file()
        service_file = cls.get_service_file()
        try:
            if desktop_file.exists():
                desktop_file.unlink(missing_ok=True)
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not remove {desktop_file}: {e}")

        try:
            if service_file.exists():
                subprocess.run(["systemctl", "--user", "disable", "gdr-aarushi.service"], capture_output=True)
                service_file.unlink(missing_ok=True)
                subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        except Exception:
            pass
        _save_preference(False, "none", "")
        return True


class DarwinAutostart:
    AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
    PLIST_FILE = AGENTS_DIR / "com.gdr.aarushi.plist"

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        has_plist = cls.PLIST_FILE.exists()
        saved = _load_saved_preference()
        enabled = has_plist if saved is None else saved
        return {
            "enabled": bool(enabled and has_plist),
            "installed": has_plist,
            "mechanism": "launchd_agent",
            "path": str(cls.PLIST_FILE if has_plist else ""),
            "platform": "darwin"
        }

    @classmethod
    def enable(cls) -> bool:
        launcher = _get_launcher_path()
        root = _get_project_root()
        cls.AGENTS_DIR.mkdir(parents=True, exist_ok=True)

        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.gdr.aarushi</string>
    <key>ProgramArguments</key>
    <array>
        <string>{launcher}</string>
        <string>--call</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{root}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""
        cls.PLIST_FILE.write_text(plist_content)
        _save_preference(True, "launchd_agent", str(cls.PLIST_FILE))
        return True

    @classmethod
    def disable(cls) -> bool:
        if cls.PLIST_FILE.exists():
            try:
                subprocess.run(["launchctl", "unload", str(cls.PLIST_FILE)], capture_output=True)
            except Exception:
                pass
            cls.PLIST_FILE.unlink(missing_ok=True)
        _save_preference(False, "none", "")
        return True


class WindowsAutostart:
    @classmethod
    def _get_startup_folder(cls) -> Path:
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        startup_dir = cls._get_startup_folder()
        bat_file = startup_dir / "GDR-Aarushi.bat"
        vbs_file = startup_dir / "GDR-Aarushi.vbs"
        has_entry = bat_file.exists() or vbs_file.exists()
        saved = _load_saved_preference()
        enabled = has_entry if saved is None else saved
        return {
            "enabled": bool(enabled and has_entry),
            "installed": has_entry,
            "mechanism": "windows_startup_folder",
            "path": str(bat_file if bat_file.exists() else (vbs_file if vbs_file.exists() else "")),
            "platform": "windows"
        }

    @classmethod
    def enable(cls) -> bool:
        launcher = _get_launcher_path()
        root = _get_project_root()
        startup_dir = cls._get_startup_folder()
        startup_dir.mkdir(parents=True, exist_ok=True)

        bat_file = startup_dir / "GDR-Aarushi.bat"
        content = f"""@echo off
REM Aarushi AI Companion Windows Autostart Entry
cd /d "{root}"
start "" "{launcher}" --call
"""
        bat_file.write_text(content)
        _save_preference(True, "windows_startup_folder", str(bat_file))
        return True

    @classmethod
    def disable(cls) -> bool:
        startup_dir = cls._get_startup_folder()
        for f in [startup_dir / "GDR-Aarushi.bat", startup_dir / "GDR-Aarushi.vbs"]:
            if f.exists():
                f.unlink(missing_ok=True)
        _save_preference(False, "none", "")
        return True


# ==============================================================================
# Shared Public API
# ==============================================================================

def get_platform_handler():
    system = platform.system().lower()
    if system == "linux":
        return LinuxAutostart
    elif system == "darwin":
        return DarwinAutostart
    elif system == "windows":
        return WindowsAutostart
    return LinuxAutostart


def get_autostart_status() -> Dict[str, Any]:
    """Return status of autostart configuration across platforms."""
    handler = get_platform_handler()
    return handler.get_status()


def enable_autostart() -> bool:
    """Enable automatic startup upon user sign-in."""
    handler = get_platform_handler()
    return handler.enable()


def disable_autostart() -> bool:
    """Disable automatic startup."""
    handler = get_platform_handler()
    return handler.disable()


def repair_autostart() -> bool:
    """Re-validate and re-write autostart configuration."""
    status = get_autostart_status()
    if status.get("enabled"):
        disable_autostart()
        return enable_autostart()
    return True


def prompt_autostart_configuration(interactive: bool = True) -> bool:
    """Interactive wizard prompt asking the user if Aarushi should start on boot.
    Pre-fills current preference when run again.
    """
    status = get_autostart_status()
    curr_setting = "Enabled" if status.get("enabled") else "Disabled"

    print("\n" + "-" * 56)
    print("🚀 Aarushi Auto-Start Configuration")
    print(f"   Current setting: {curr_setting}")
    print("   Would you like Aarushi to start automatically")
    print("   whenever you sign in to your computer?")
    print("   • Yes: Aarushi will be ready in the background.")
    print("   • No : Aarushi will only launch when you run 'gdr'.")
    print("-" * 56)

    if not interactive:
        return status.get("enabled", False)

    default_choice = "Y" if status.get("enabled") else "N"
    prompt_str = f"Enable automatic startup? [Y/N/S] (default: {default_choice}): "

    try:
        choice = input(prompt_str).strip().upper()
    except (EOFError, KeyboardInterrupt):
        print("\nKeeping existing setting.")
        return status.get("enabled", False)

    if not choice:
        choice = default_choice

    if choice == "Y":
        enable_autostart()
        print("✅ Automatic startup has been ENABLED.")
        return True
    elif choice == "N":
        disable_autostart()
        print("⏸️  Automatic startup has been DISABLED (manual startup only).")
        return False
    else:
        print(f"⏩ Skipped. Keeping current setting ({curr_setting}).")
        return status.get("enabled", False)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "enable":
            enable_autostart()
            print("Autostart enabled.")
        elif cmd == "disable":
            disable_autostart()
            print("Autostart disabled.")
        elif cmd == "status":
            print(json.dumps(get_autostart_status(), indent=2))
        elif cmd == "repair":
            repair_autostart()
            print("Autostart repaired.")
        elif cmd in ("--prompt", "prompt", "configure"):
            prompt_autostart_configuration(interactive=True)
        else:
            print(f"Unknown command: {cmd}")
    else:
        prompt_autostart_configuration(interactive=True)

