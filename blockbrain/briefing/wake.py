"""Wake-from-suspend management and hardware limit documentation.
Uses Linux RTC (Real Time Clock) wake via rtcwake to wake laptop from suspend for alarms.
"""

from datetime import datetime
import shutil
import subprocess
from typing import Dict, Any, Tuple


def schedule_rtcwake(target_time: datetime) -> Tuple[bool, str]:
    """Schedule hardware RTC wake-from-suspend.
    Requires sudo rtcwake in allowlist.
    """
    now = datetime.now()
    if target_time <= now:
        return False, "Target time must be in the future."

    seconds = int((target_time - now).total_seconds())
    # Subtract 60 seconds so laptop wakes up 1 minute before alarm rings
    lead_seconds = max(10, seconds - 60)

    if not shutil.which("rtcwake"):
        return False, "rtcwake utility not found on system."

    try:
        # -m no: sets alarm time only without immediately suspending
        cmd = ["sudo", "-n", "rtcwake", "-m", "no", "-s", str(lead_seconds)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return True, f"RTC wake scheduled for {target_time.strftime('%Y-%m-%d %H:%M:%S')} (wake lead: {lead_seconds}s)."
        else:
            return False, f"rtcwake error: {res.stderr.strip() or 'requires sudo privilege'}"
    except Exception as e:
        return False, f"Execution error: {e}"


HARDWARE_LIMITS_DOC = """
### Hardware Limits & Always-On Deployment Options

1. **Laptop State Requirements**:
   - The laptop can be in **Suspend (Sleep)** mode: blockbrain AI configures the hardware RTC via `rtcwake` to wake the machine 60 seconds before your alarm.
   - If the laptop is **Powered completely OFF** (or battery runs out), no OS software can execute.
   - Closing the laptop lid: Ensure GNOME does not ignore RTC wake (`/etc/systemd/logind.conf` -> `HandleLidSwitch=suspend`).

2. **Always-On Options (Raspberry Pi or VPS)**:
   - For 100% reliable alarms even if your laptop is closed, unpowered, or travelling, run the `blockbraind` scheduler on a low-cost **Raspberry Pi (Zero 2W / Pi 4)** or a **$4/mo VPS** (e.g. Hetzner, DigitalOcean).
   - The Pi/VPS stays connected to Tailscale and executes Stage 2 (Telegram/phone push) and Stage 3 (Twilio phone call) unconditionally.
"""

