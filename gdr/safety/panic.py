"""Kill switch (`gdr panic`).
Immediately terminates all running background tasks, daemon workers, browser instances, and audio playback.
"""

import os
from pathlib import Path
import subprocess
import signal

from gdr.voice.tts import stop_speaking

PANIC_LOCK_FILE = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr")) / "panic.lock"


def trigger_panic() -> str:
    """Execute immediate emergency stop."""
    results = []

    # 1. Stop audio playback
    try:
        stop_speaking()
        results.append("Audio playback halted.")
    except Exception as e:
        results.append(f"Audio stop error: {e}")

    # 2. Touch panic lock file so daemon loops break immediately
    try:
        PANIC_LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        PANIC_LOCK_FILE.touch()
        results.append("Panic lock activated (~/.config/gdr/panic.lock).")
    except Exception as e:
        results.append(f"Lock error: {e}")

    # 3. Kill chromium/playwright spawned by gdr
    try:
        subprocess.run(
            ["pkill", "-f", "playwright"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        results.append("Killed background browser processes.")
    except Exception:
        pass

    # 4. Notify daemon if running via systemctl --user
    try:
        res = subprocess.run(
            ["systemctl", "--user", "kill", "--signal=SIGUSR1", "gdrd.service"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if res.returncode == 0:
            results.append("Sent interrupt to gdrd daemon.")
    except Exception:
        pass

    msg = "🚨 EMERGENCY STOP TRIGGERED.\n" + "\n".join(f"  • {r}" for r in results)
    return msg


def clear_panic():
    """Clear panic lock so system can resume normal operations."""
    if PANIC_LOCK_FILE.exists():
        try:
            PANIC_LOCK_FILE.unlink()
            return True
        except Exception:
            return False
    return True


def is_panicked() -> bool:
    """Check if panic mode is active."""
    return PANIC_LOCK_FILE.exists()

