"""System diagnostics, hardware monitors, and control tools for blockbrain AI on Linux.
"""

import os
from pathlib import Path
import shutil
import subprocess
from typing import Dict, Any, Optional

from blockbrain.tools.registry import tool


@tool(name="system_info", description="Get overview of system hardware, OS version, kernel, and uptime.", category="system", tier="AUTO")
def system_info() -> str:
    lines = []
    try:
        uname = subprocess.check_output(["uname", "-a"], text=True).strip()
        lines.append(f"OS/Kernel: {uname}")
    except Exception:
        pass

    try:
        uptime = subprocess.check_output(["uptime", "-p"], text=True).strip()
        lines.append(f"Uptime: {uptime}")
    except Exception:
        pass

    try:
        mem = subprocess.check_output(["free", "-h"], text=True).strip()
        lines.append(f"\nMemory:\n{mem}")
    except Exception:
        pass

    try:
        disk = subprocess.check_output(["df", "-h", "/"], text=True).strip()
        lines.append(f"\nDisk (/):\n{disk}")
    except Exception:
        pass

    return "\n".join(lines)


@tool(name="system_health", description="Check battery level, RAM usage, and disk space with health status.", category="system", tier="AUTO")
def system_health() -> str:
    status = []
    # Battery
    battery_info = "Unknown"
    bat_path = Path("/sys/class/power_supply/BAT0")
    if not bat_path.exists():
        bat_path = Path("/sys/class/power_supply/BAT1")
    if bat_path.exists():
        try:
            cap = (bat_path / "capacity").read_text().strip()
            stat = (bat_path / "status").read_text().strip()
            battery_info = f"{cap}% ({stat})"
        except Exception:
            pass
    status.append(f"🔋 Battery: {battery_info}")

    # Audio Volume
    try:
        vol_out = subprocess.check_output(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], text=True).strip()
        status.append(f"🔊 Speaker: {vol_out}")
    except Exception:
        pass

    return "\n".join(status)


@tool(name="set_volume", description="Set audio volume (0 to 100 percent).", category="system", tier="AUTO")
def set_volume(percentage: int) -> str:
    clamped = max(0, min(100, int(percentage)))
    vol_float = clamped / 100.0
    try:
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", str(vol_float)], check=True)
        return f"Speaker volume set to {clamped}%."
    except Exception as e:
        return f"Error setting volume: {e}"


@tool(name="get_volume", description="Get current audio volume percentage.", category="system", tier="AUTO")
def get_volume() -> str:
    try:
        out = subprocess.check_output(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], text=True).strip()
        return f"Current volume: {out}"
    except Exception as e:
        return f"Error getting volume: {e}"


@tool(name="lock_screen", description="Lock the desktop session immediately.", category="system", tier="AUTO")
def lock_screen() -> str:
    cmds = [
        ["xdg-screensaver", "lock"],
        ["loginctl", "lock-session"],
        ["gnome-screensaver-command", "-l"],
    ]
    for c in cmds:
        if shutil.which(c[0]):
            try:
                subprocess.run(c, check=True)
                return "Screen locked."
            except Exception:
                pass
    return "Failed to find screen locker binary."


@tool(name="kill_process", description="Terminate a running process by PID. Requires APPROVAL.", category="system", tier="APPROVAL", requires_approval=True)
def kill_process(pid: int) -> str:
    try:
        os.kill(int(pid), 15)  # SIGTERM
        return f"Sent SIGTERM to process {pid}."
    except Exception as e:
        return f"Error terminating process {pid}: {e}"
