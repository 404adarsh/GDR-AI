"""Standalone Desktop Call Application Launcher for Aarushi AI / GDR-IDE.
Launches Focus Talking Mode as a dedicated, chrome-less native desktop calling window
with automated audio autoplay permissions and pre-configured microphone access.
"""

from datetime import datetime
import json
import logging
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys
import time
from typing import Dict, Any, List, Optional, Tuple

from gdr.config import get_gdr_config_dir

logger = logging.getLogger("gdr.system.desktop_app")


def get_desktop_profile_dir() -> Path:
    """Return dynamic path to dedicated browser profile for desktop call app."""
    return get_gdr_config_dir() / "desktop_call_profile"


def get_desktop_pid_file() -> Path:
    """Return dynamic path to desktop app PID lock file."""
    return get_gdr_config_dir() / "desktop_app.pid"


# Backwards compatibility properties / references
DESKTOP_PROFILE_DIR = get_desktop_profile_dir()
DESKTOP_PID_FILE = get_desktop_pid_file()


def is_port_bound(port: int, host: str = "127.0.0.1") -> bool:
    """Check if the local server port is active."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.3)
    try:
        return sock.connect_ex((host, port)) == 0
    finally:
        sock.close()


def find_desktop_browser_binary() -> Optional[Tuple[str, str]]:
    """Locate an installed browser capable of standalone --app window mode.
    Returns (browser_name, executable_path).
    """
    sys_name = platform.system().lower()

    if sys_name == "linux":
        candidates = [
            ("chromium", "chromium"),
            ("google-chrome", "google-chrome"),
            ("google-chrome-stable", "google-chrome-stable"),
            ("chromium-browser", "chromium-browser"),
            ("microsoft-edge", "microsoft-edge"),
            ("microsoft-edge-stable", "microsoft-edge-stable"),
            ("brave-browser", "brave-browser"),
        ]
        for name, cmd in candidates:
            path = shutil.which(cmd)
            if path and os.path.isfile(path) and os.access(path, os.X_OK):
                return (name, path)

    elif sys_name == "windows":
        candidates = [
            ("msedge", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            ("msedge", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            ("chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            ("chrome", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            ("brave", r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"),
        ]
        for name, path in candidates:
            if os.path.isfile(path):
                return (name, path)
        for name in ("msedge", "chrome", "brave"):
            p = shutil.which(name)
            if p:
                return (name, p)

    elif sys_name == "darwin":
        candidates = [
            ("google-chrome", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ("microsoft-edge", "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
            ("brave", "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
            ("chromium", "/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
        for name, path in candidates:
            if os.path.isfile(path):
                return (name, path)

    return None


def configure_desktop_profile_permissions(port: int = 8844) -> None:
    """Pre-seed Chromium/Chrome preferences so microphone permission is auto-granted
    for http://127.0.0.1:{port} without presenting annoying browser popups.
    """
    try:
        profile_dir = get_desktop_profile_dir()
        default_dir = profile_dir / "Default"
        default_dir.mkdir(parents=True, exist_ok=True)
        pref_file = default_dir / "Preferences"

        prefs: Dict[str, Any] = {}
        if pref_file.exists():
            try:
                prefs = json.loads(pref_file.read_text(encoding="utf-8"))
            except Exception:
                prefs = {}

        # Content settings: grant media_stream_mic permission
        content_settings = prefs.setdefault("profile", {}).setdefault("content_settings", {})
        exceptions = content_settings.setdefault("exceptions", {})
        mic_exceptions = exceptions.setdefault("media_stream_mic", {})

        key = f"http://127.0.0.1:{port},*"
        mic_exceptions[key] = {
            "last_modified": str(int(time.time() * 1000)),
            "setting": 1  # 1 = ALLOW
        }

        pref_file.write_text(json.dumps(prefs, indent=2), encoding="utf-8")
    except Exception as e:
        logger.debug(f"Could not pre-seed browser profile preferences: {e}")


def ensure_backend_running(port: int = 8844, max_wait_seconds: float = 6.0) -> bool:
    """Ensure the GDR background server is running on the given port."""
    if is_port_bound(port):
        return True

    logger.info(f"Starting GDR backend server on port {port}...")
    project_root = Path(__file__).resolve().parent.parent.parent
    venv_py = project_root / ".venv" / "bin" / "python"
    if not venv_py.exists():
        venv_py = Path(sys.executable)

    # Spawn daemon server process
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"

    cmd = [str(venv_py), "-m", "uvicorn", "gdr.web.server:app", "--host", "0.0.0.0", "--port", str(port)]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        from gdr.system.lifecycle import record_gui_pid
        record_gui_pid(proc.pid)
    except Exception as e:
        logger.error(f"Failed to start backend server: {e}")
        return False

    start = time.time()
    while time.time() - start < max_wait_seconds:
        if is_port_bound(port):
            time.sleep(0.3)
            return True
        time.sleep(0.2)

    return is_port_bound(port)


def launch_desktop_call_app(
    port: int = 8844,
    autostart_mode: bool = False,
    foreground: bool = True
) -> bool:
    """Launch Aarushi Desktop Call App as a dedicated chrome-less native window."""
    # Step 1: Single-instance check
    pid_file = get_desktop_pid_file()
    profile_dir = get_desktop_profile_dir()
    if pid_file.exists():
        try:
            old_pid = int(pid_file.read_text().strip())
            # Check if process is still alive
            os.kill(old_pid, 0)
            print(f"✨ Aarushi Desktop Call App is already active (PID: {old_pid}).")
            return True
        except (ProcessLookupError, ValueError):
            pid_file.unlink(missing_ok=True)
        except Exception:
            pass

    # Step 2: Ensure backend server is active
    if not ensure_backend_running(port=port):
        print(f"❌ Could not connect to local GDR server on port {port}.")
        return False

    # Step 3: Configure profile with auto-granted microphone permission
    configure_desktop_profile_permissions(port=port)

    # Step 4: Locate desktop browser binary
    browser = find_desktop_browser_binary()
    call_url = f"http://127.0.0.1:{port}/call"

    if browser:
        b_name, b_path = browser
        print(f"🌸 Launching Aarushi Desktop Call App via {b_name} standalone window...")
        app_args = [
            b_path,
            f"--app={call_url}",
            f"--user-data-dir={profile_dir}",
            "--use-fake-ui-for-media-stream",
            "--autoplay-policy=no-user-gesture-required",
            "--window-size=1220,840",
            "--window-position=center",
            "--class=AarushiCallApp",
            "--name=AarushiCallApp",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-pinch",
            "--disable-features=PreloadMediaEngagementData",
        ]

        try:
            proc = subprocess.Popen(
                app_args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=not foreground
            )
            pid_file.write_text(str(proc.pid))

            if foreground:
                try:
                    proc.wait()
                except KeyboardInterrupt:
                    proc.terminate()
                finally:
                    pid_file.unlink(missing_ok=True)
            return True
        except Exception as e:
            logger.error(f"Failed to launch desktop app window: {e}")

    # Fallback if no chromium-based browser available
    print(f"⚠️ Standalone window binary not found. Launching via system desktop opener at {call_url}...")
    import webbrowser
    webbrowser.open(call_url)
    return True
