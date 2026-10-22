"""System diagnostics, hardware monitors, and control tools for GDR AI on Linux.
"""

import os
from pathlib import Path
import shutil
import subprocess
from typing import Dict, Any, Optional

from gdr.tools.registry import tool


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


@tool(name="get_current_time", description="Get accurate current time, date, day of week, and timezone information.", category="system", tier="AUTO")
def get_current_time_tool(timezone: str = "Asia/Kolkata") -> str:
    from gdr.core.time_service import get_time_service
    ts = get_time_service()
    res = ts.get_current_time(timezone)
    return res["summary"]


@tool(name="calculate_time_duration", description="Calculate duration between two time strings (e.g. '10:30 AM' and '2:15 PM'), handling midnight crossings.", category="system", tier="AUTO")
def calculate_time_duration_tool(start_time: str, end_time: str) -> str:
    from gdr.core.time_service import get_time_service
    ts = get_time_service()
    res = ts.calculate_duration(start_time, end_time)
    return f"Duration: {res['formatted_en']} ({res['formatted_hi']}). Total: {res['total_minutes']} minutes."


@tool(name="compare_timezones", description="Compare a specific time between two timezones (e.g., IST vs London).", category="system", tier="AUTO")
def compare_timezones_tool(time_str: str, tz_from: str = "Asia/Kolkata", tz_to: str = "Europe/London") -> str:
    from gdr.core.time_service import get_time_service
    ts = get_time_service()
    res = ts.compare_timezones(time_str, tz_from, tz_to)
    return res["explanation"]


@tool(name="time_until", description="Calculate the remaining time until a target deadline or future event.", category="system", tier="AUTO")
def time_until_tool(target_datetime: str, timezone: str = "Asia/Kolkata") -> str:
    from gdr.core.time_service import get_time_service
    ts = get_time_service()
    res = ts.time_until(target_datetime, timezone)
    return f"Time until {res['target_datetime']}: {res['summary']}."


@tool(name="run_complex_background_task", description="Run a complex long-running job (download, build, installation, heavy shell task) asynchronously in background with live 5-10s progress notifications while remaining responsive to chat.", category="system", tier="AUTO")
def run_complex_background_task_tool(command: str, description: str = "", estimated_seconds: int = 30) -> str:
    import threading
    import time
    from gdr.core.tasks import get_task_tracker
    tracker = get_task_tracker()
    task = tracker.register_task(name=description or command[:35], description=description or command, total_steps=max(5, estimated_seconds))

    def _runner():
        start = time.time()
        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                executable="/bin/bash",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            while proc.poll() is None:
                elapsed = int(time.time() - start)
                tracker.update_progress(
                    task.task_id,
                    completed_steps=min(task.total_steps - 1, elapsed),
                    status_message=f"Executing ({elapsed}s elapsed)"
                )
                time.sleep(5.0)
            out, err = proc.communicate()
            if proc.returncode == 0:
                tracker.complete_task(task.task_id, result_message=f"Success: {out[:200] if out else 'Done'}")
            else:
                tracker.fail_task(task.task_id, error_message=f"Exit {proc.returncode}: {err[:200] if err else 'Failed'}")
        except Exception as e:
            tracker.fail_task(task.task_id, error_message=str(e))

    t = threading.Thread(target=_runner, daemon=True, name=f"BgTask-{task.task_id}")
    t.start()
    return f"🚀 Started background task '{task.name}'. Progress updates will report every 5-10s. You can continue talking to me simultaneously!"


@tool(name="get_background_tasks_progress", description="Check live progress of all simultaneous background tasks ('how much it did, how much it left').", category="system", tier="AUTO")
def get_background_tasks_progress_tool() -> str:
    from gdr.core.tasks import get_task_tracker
    return get_task_tracker().get_overall_summary()


