"""Push notification dispatcher for blockbrain AI.
Supports Linux desktop notifications (notify-send), ntfy.sh, and Pushover.
"""

import shutil
import subprocess
from typing import Optional
import requests

from blockbrain.config import load_config
from blockbrain.safety.secrets import get_secret


def send_push(title: str, message: str, priority: str = "normal", topic: Optional[str] = None) -> bool:
    """Send push notification across configured notification channels."""
    cfg = load_config()
    backend = cfg.get("channels", {}).get("push_backend", "desktop")

    success = False

    # 1. Desktop notification via notify-send
    if shutil.which("notify-send"):
        try:
            urgency = "critical" if priority in ("high", "urgent") else "normal"
            subprocess.run(
                ["notify-send", "-u", urgency, "-a", "blockbrain AI", title, message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            success = True
        except Exception:
            pass

    # 2. ntfy.sh push
    ntfy_topic = topic or cfg.get("channels", {}).get("ntfy_topic", "blockbrain-alerts")
    if ntfy_topic:
        try:
            requests.post(
                f"https://ntfy.sh/{ntfy_topic}",
                data=message.encode("utf-8"),
                headers={
                    "Title": title,
                    "Priority": "5" if priority in ("high", "urgent") else "3",
                    "Tags": "robot,alarm"
                },
                timeout=5
            )
            success = True
        except Exception:
            pass

    return success

