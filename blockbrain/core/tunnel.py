"""Cloudflare Quick Tunnel Manager for GDR AI.
Manages automatic creation, status monitoring, and lifecycle of Cloudflare trycloudflare.com tunnels.
Provides terminal QR code generation and REST API backing.
"""

import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("gdr.core.tunnel")

LOG_FILE = Path("/tmp/cloudflared.log")
URL_FILE = Path("/tmp/gdr_tunnel_url.txt")

_CURRENT_TUNNEL_URL: Optional[str] = None
_TUNNEL_PROC: Optional[subprocess.Popen] = None
_START_TIME: Optional[float] = None


def find_cloudflared_bin() -> Optional[str]:
    """Locate the cloudflared binary in common paths."""
    found = shutil.which("cloudflared")
    if found:
        return found
    candidates = [
        str(Path.home() / ".local" / "bin" / "cloudflared"),
        "/usr/local/bin/cloudflared",
        "/usr/bin/cloudflared",
    ]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def get_active_url_from_log() -> Optional[str]:
    """Extract trycloudflare.com URL from log file."""
    if not LOG_FILE.exists():
        return None
    try:
        content = LOG_FILE.read_text(encoding="utf-8", errors="ignore")
        matches = re.findall(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", content)
        if matches:
            return matches[-1]
    except Exception as e:
        logger.debug(f"Error reading tunnel log: {e}")
    return None


def is_tunnel_process_alive() -> bool:
    """Check if any cloudflared process is running."""
    try:
        out = subprocess.run(["pgrep", "-f", "cloudflared tunnel"], capture_output=True, text=True)
        return out.returncode == 0 and bool(out.stdout.strip())
    except Exception:
        return False


def get_tunnel_status() -> Dict[str, Any]:
    """Get the current live status of the Cloudflare tunnel."""
    global _CURRENT_TUNNEL_URL, _START_TIME
    alive = is_tunnel_process_alive()
    if not alive:
        _CURRENT_TUNNEL_URL = None
        _START_TIME = None
        return {
            "active": False,
            "url": None,
            "port": 8844,
            "uptime_seconds": 0,
        }

    # If alive but URL not cached in memory, re-read from log or URL file
    if not _CURRENT_TUNNEL_URL:
        _CURRENT_TUNNEL_URL = get_active_url_from_log()
        if not _CURRENT_TUNNEL_URL and URL_FILE.exists():
            try:
                _CURRENT_TUNNEL_URL = URL_FILE.read_text(encoding="utf-8").strip()
            except Exception:
                pass

    uptime = int(time.time() - _START_TIME) if _START_TIME else 0
    return {
        "active": True,
        "url": _CURRENT_TUNNEL_URL,
        "port": 8844,
        "uptime_seconds": uptime,
    }


def start_tunnel(port: int = 8844, timeout_sec: int = 20) -> Tuple[bool, str, str]:
    """Start Cloudflare tunnel if not already running.
    Returns: (success: bool, url: str, message: str)
    """
    global _CURRENT_TUNNEL_URL, _TUNNEL_PROC, _START_TIME

    # Check if already running and URL is available
    status = get_tunnel_status()
    if status["active"] and status["url"]:
        _CURRENT_TUNNEL_URL = status["url"]
        return True, _CURRENT_TUNNEL_URL, "Tunnel already active."

    bin_path = find_cloudflared_bin()
    if not bin_path:
        return False, "", "cloudflared binary not found. Please install cloudflared in ~/.local/bin or PATH."

    # Remove old log to avoid stale URLs
    try:
        if LOG_FILE.exists():
            LOG_FILE.unlink()
    except Exception:
        pass

    # Launch daemon
    cmd = [bin_path, "tunnel", "--url", f"http://127.0.0.1:{port}", "--logfile", str(LOG_FILE)]
    try:
        _TUNNEL_PROC = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        _START_TIME = time.time()
    except Exception as e:
        return False, "", f"Failed to spawn cloudflared: {e}"

    # Poll for URL in log
    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        time.sleep(0.5)
        url = get_active_url_from_log()
        if url:
            _CURRENT_TUNNEL_URL = url
            try:
                URL_FILE.write_text(url, encoding="utf-8")
            except Exception:
                pass
            return True, url, "Tunnel started successfully."

    return False, "", "Timeout waiting for Cloudflare trycloudflare.com URL."


def stop_tunnel() -> bool:
    """Stop all running cloudflared tunnel processes."""
    global _CURRENT_TUNNEL_URL, _TUNNEL_PROC, _START_TIME
    _CURRENT_TUNNEL_URL = None
    _START_TIME = None
    try:
        subprocess.run(["pkill", "-f", "cloudflared tunnel"], capture_output=True)
        if URL_FILE.exists():
            try:
                URL_FILE.unlink()
            except Exception:
                pass
        return True
    except Exception as e:
        logger.error(f"Error stopping cloudflared: {e}")
        return False


def generate_ascii_qr(url: str) -> str:
    """Generate ASCII QR code string for terminal display."""
    if not url:
        return ""
    # Try qrenco.de via curl if available
    try:
        out = subprocess.check_output(
            ["curl", "-s", "--max-time", "3", f"https://qrenco.de/{url}"],
            text=True
        ).strip()
        if out and ("█" in out or "▄" in out):
            return out
    except Exception:
        pass

    # Fallback to python qrcode module if installed
    try:
        import io
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(url)
        f = io.StringIO()
        qr.print_ascii(out=f)
        f.seek(0)
        return f.read().strip()
    except Exception:
        pass

    return f"Scan URL: {url}"
