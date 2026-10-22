"""Personal Desktop Assistant Capabilities for Aarushi AI.
Provides media control (play, pause, next, volume, music search),
safe file downloads and directory organization, and local app/folder launching.
Operates with strict path validation and platform-native integration.
"""

import logging
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
import webbrowser
from typing import List, Dict, Any, Optional

from gdr.tools.registry import tool

logger = logging.getLogger("gdr.tools.desktop_assistant")


# ==============================================================================
# 8.1 Music & Media Controls
# ==============================================================================

@tool(name="media_control", category="desktop", tier="AUTO")
def media_control_tool(action: str, query: Optional[str] = None, volume_percent: Optional[int] = None) -> str:
    """Control media playback (play, pause, next, previous, volume_up, volume_down, or search_music).
    Action can be: 'play', 'pause', 'play_pause', 'next', 'previous', 'volume_up', 'volume_down', 'search_music'.
    """
    system = platform.system().lower()
    act = action.strip().lower()

    if act == "search_music" or (query and act in ("play", "search")):
        # Search & open music via YouTube Music or YouTube
        encoded = urllib.parse.quote(query or "lofi beats")
        music_url = f"https://music.youtube.com/search?q={encoded}"
        webbrowser.open(music_url)
        return f"Opened YouTube Music search for '{query}'."

    # Linux playerctl integration
    if system == "linux":
        playerctl_bin = shutil.which("playerctl")
        if playerctl_bin:
            try:
                if act in ("play", "pause", "play-pause", "play_pause"):
                    cmd = [playerctl_bin, "play-pause"]
                elif act in ("next", "skip"):
                    cmd = [playerctl_bin, "next"]
                elif act in ("previous", "prev"):
                    cmd = [playerctl_bin, "previous"]
                elif act in ("volume_up", "volup"):
                    cmd = [playerctl_bin, "volume", "0.10+"]
                elif act in ("volume_down", "voldown"):
                    cmd = [playerctl_bin, "volume", "0.10-"]
                elif act == "set_volume" and volume_percent is not None:
                    vol_float = max(0.0, min(1.0, volume_percent / 100.0))
                    cmd = [playerctl_bin, "volume", str(vol_float)]
                else:
                    cmd = [playerctl_bin, "play-pause"]

                res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                if res.returncode == 0:
                    return f"Executed media command '{act}' successfully."
            except Exception as e:
                logger.debug(f"Playerctl call failed: {e}")

        # Fallback to pactl / amixer for volume if playerctl unavailable
        if act in ("volume_up", "volume_down"):
            pactl_bin = shutil.which("pactl")
            if pactl_bin:
                delta = "+5%" if act == "volume_up" else "-5%"
                subprocess.run([pactl_bin, "set-sink-volume", "@DEFAULT_SINK@", delta], capture_output=True)
                return f"Adjusted volume ({delta})."

    # macOS AppleScript integration
    elif system == "darwin":
        try:
            if act in ("play", "pause", "play_pause"):
                script = 'tell application "Music" to playpause'
            elif act == "next":
                script = 'tell application "Music" to next track'
            elif act == "previous":
                script = 'tell application "Music" to previous track'
            elif act == "volume_up":
                script = 'set volume output volume ((output volume of (get volume settings)) + 5)'
            elif act == "volume_down":
                script = 'set volume output volume ((output volume of (get volume settings)) - 5)'
            else:
                script = 'tell application "Music" to playpause'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
            return f"Executed media command '{act}' on macOS."
        except Exception as e:
            logger.debug(f"macOS osascript failed: {e}")

    # Windows integration
    elif system == "windows":
        if act == "volume_up":
            cmd = '(New-Object -ComObject WScript.Shell).SendKeys([char]175)'
            subprocess.run(["powershell", "-Command", cmd], capture_output=True)
            return "Volume increased."
        elif act == "volume_down":
            cmd = '(New-Object -ComObject WScript.Shell).SendKeys([char]174)'
            subprocess.run(["powershell", "-Command", cmd], capture_output=True)
            return "Volume decreased."
        elif act in ("play", "pause", "play_pause"):
            cmd = '(New-Object -ComObject WScript.Shell).SendKeys([char]179)'
            subprocess.run(["powershell", "-Command", cmd], capture_output=True)
            return "Toggled play/pause."

    return f"Media control '{act}' dispatched."


# ==============================================================================
# 8.2 File Downloads and Safe Organization
# ==============================================================================

@tool(name="download_file", category="desktop", tier="AUTO")
def download_file_tool(
    url: str,
    destination_dir: str = "~/Downloads",
    filename: Optional[str] = None,
    overwrite: bool = False,
    max_mb: int = 500
) -> str:
    """Download a file from a specified URL safely to the given directory."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return f"Error: Only HTTP and HTTPS URLs are permitted. Provided scheme: {parsed.scheme}"

    dest_path = Path(os.path.expanduser(destination_dir)).resolve()
    dest_path.mkdir(parents=True, exist_ok=True)

    if not filename:
        raw_name = os.path.basename(parsed.path)
        filename = raw_name if raw_name and "." in raw_name else f"download_{int(datetime.now().timestamp())}.dat"

    # Sanitize filename
    clean_filename = re.sub(r'[^\w\.-]', '_', filename)
    target_file = dest_path / clean_filename

    if target_file.exists() and not overwrite:
        return f"File '{clean_filename}' already exists at {dest_path}. Set overwrite=true to replace."

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; GDR-IDE/2.0)"})
    bytes_downloaded = 0
    max_bytes = max_mb * 1024 * 1024

    try:
        with urllib.request.urlopen(req, timeout=30) as resp, open(target_file, "wb") as out:
            while True:
                chunk = resp.read(65536)
                if not chunk:
                    break
                bytes_downloaded += len(chunk)
                if bytes_downloaded > max_bytes:
                    target_file.unlink(missing_ok=True)
                    return f"Error: Download exceeded maximum permitted size ({max_mb} MB)."
                out.write(chunk)

        mb_size = round(bytes_downloaded / (1024 * 1024), 2)
        return f"Successfully downloaded '{clean_filename}' ({mb_size} MB) to {target_file}."
    except Exception as e:
        if target_file.exists():
            target_file.unlink(missing_ok=True)
        return f"Download failed: {str(e)}"


@tool(name="organize_folder", category="desktop", tier="APPROVAL")
def organize_folder_tool(directory_path: str) -> str:
    """Organize files in a user-approved folder into categorized subfolders (Documents, Images, Archives, Code, Media)."""
    target_dir = Path(os.path.expanduser(directory_path)).resolve()
    if not target_dir.exists() or not target_dir.is_dir():
        return f"Directory '{directory_path}' does not exist or is not a folder."

    CATEGORY_EXTS = {
        "Images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp"},
        "Documents": {".pdf", ".docx", ".doc", ".txt", ".md", ".xlsx", ".pptx", ".csv"},
        "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".yaml", ".toml", ".sh", ".rs", ".go"},
        "Archives": {".zip", ".tar", ".gz", ".7z", ".rar", ".bz2"},
        "Media": {".mp3", ".wav", ".mp4", ".mkv", ".flac", ".ogg", ".webm"},
    }

    moved_count = 0
    for item in list(target_dir.iterdir()):
        if item.is_file() and not item.name.startswith("."):
            ext = item.suffix.lower()
            matched_folder = None
            for folder_name, exts in CATEGORY_EXTS.items():
                if ext in exts:
                    matched_folder = folder_name
                    break

            if matched_folder:
                dest_subfolder = target_dir / matched_folder
                dest_subfolder.mkdir(parents=True, exist_ok=True)
                dest_file = dest_subfolder / item.name
                if not dest_file.exists():
                    shutil.move(str(item), str(dest_file))
                    moved_count += 1

    return f"Organized {moved_count} file{'s' if moved_count != 1 else ''} in {target_dir}."


# ==============================================================================
# 8.3 Local Computer Operations
# ==============================================================================

@tool(name="open_application_or_folder", category="desktop", tier="AUTO")
def open_application_or_folder_tool(target: str) -> str:
    """Open a local folder, file, or application safely using platform-native launchers."""
    target_clean = target.strip()
    system = platform.system().lower()

    # Check if target is a file or directory path
    path_obj = Path(os.path.expanduser(target_clean)).resolve()
    if path_obj.exists():
        if system == "linux":
            subprocess.Popen(["xdg-open", str(path_obj)], start_new_session=True)
        elif system == "darwin":
            subprocess.Popen(["open", str(path_obj)], start_new_session=True)
        elif system == "windows":
            os.startfile(str(path_obj))
        return f"Opened '{path_obj}' in system default application."

    # Otherwise treat as an application name
    app_lower = target_clean.lower()
    app_map = {
        "terminal": ["x-terminal-emulator"] if system == "linux" else (["open", "-a", "Terminal"] if system == "darwin" else ["cmd.exe"]),
        "calculator": ["gnome-calculator", "kcalc"] if system == "linux" else (["open", "-a", "Calculator"] if system == "darwin" else ["calc.exe"]),
        "browser": ["xdg-open", "https://google.com"] if system == "linux" else (["open", "https://google.com"] if system == "darwin" else ["start", "https://google.com"]),
        "vscode": ["code"],
        "code": ["code"],
    }

    cmd = app_map.get(app_lower)
    if not cmd:
        # Check if binary is in PATH
        found_bin = shutil.which(target_clean)
        if found_bin:
            cmd = [found_bin]

    if cmd:
        try:
            subprocess.Popen(cmd, start_new_session=True)
            return f"Launched application '{target_clean}'."
        except Exception as e:
            return f"Failed to launch '{target_clean}': {e}"

    return f"Application or path '{target_clean}' was not found on the local system."


@tool(name="install_software_package", category="desktop", tier="APPROVAL", requires_approval=True)
def install_software_package(package_name: str, method: str = "auto") -> str:
    """Safely install a software package using official system package managers (apt, brew, winget) with pre-checks and health verification."""
    clean_pkg = package_name.strip()
    if not clean_pkg:
        return "Error: package_name cannot be empty."

    sys_name = platform.system().lower()

    # 1. Pre-check: Is the package/binary already installed?
    existing_bin = shutil.which(clean_pkg)
    if existing_bin:
        try:
            ver_res = subprocess.run([clean_pkg, "--version"], capture_output=True, text=True, timeout=5)
            ver_output = (ver_res.stdout or ver_res.stderr or "").strip().splitlines()
            ver_str = ver_output[0] if ver_output else "Installed"
            return f"Package '{clean_pkg}' is already installed at {existing_bin} ({ver_str})."
        except Exception:
            return f"Package '{clean_pkg}' is already installed at {existing_bin}."

    # 2. Select package manager
    if sys_name == "linux":
        if shutil.which("apt-get"):
            cmd = ["sudo", "apt-get", "install", "-y", clean_pkg]
        elif shutil.which("dnf"):
            cmd = ["sudo", "dnf", "install", "-y", clean_pkg]
        elif shutil.which("pacman"):
            cmd = ["sudo", "pacman", "-S", "--noconfirm", clean_pkg]
        else:
            return f"No supported Linux package manager found to install '{clean_pkg}'."
    elif sys_name == "darwin":
        if shutil.which("brew"):
            cmd = ["brew", "install", clean_pkg]
        else:
            return f"Homebrew is not installed on macOS to install '{clean_pkg}'."
    elif sys_name == "windows":
        if shutil.which("winget"):
            cmd = ["winget", "install", clean_pkg, "--silent"]
        else:
            return f"winget is not available on Windows to install '{clean_pkg}'."
    else:
        return f"Unsupported operating system: {sys_name}"

    # 3. Execute installation
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if res.returncode != 0:
            err = (res.stderr or res.stdout or "").strip()
            return f"Installation of '{clean_pkg}' failed (exit code {res.returncode}): {err[:300]}"

        # 4. Post-installation health verification
        installed_bin = shutil.which(clean_pkg)
        health_info = ""
        if installed_bin:
            try:
                v = subprocess.run([installed_bin, "--version"], capture_output=True, text=True, timeout=5)
                lines = (v.stdout or v.stderr or "").strip().splitlines()
                health_info = f" Version: {lines[0]}" if lines else ""
            except Exception:
                pass
        return f"✅ Successfully installed '{clean_pkg}' via {' '.join(cmd[:2])}.{health_info} Binary: {installed_bin or 'system library'}"
    except Exception as e:
        return f"Error executing installation for '{clean_pkg}': {e}"

