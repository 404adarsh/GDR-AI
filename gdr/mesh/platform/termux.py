"""Android Termux Platform Adapter for GDR-AI Device Mesh."""

import json
import os
import shutil
import subprocess
import time
from typing import Dict, Any
from gdr.mesh.platform.base import BasePlatformAdapter


class TermuxPlatformAdapter(BasePlatformAdapter):
    """Adapter for Android running Termux with Termux:API support."""

    def __init__(self):
        self._boot_time = time.time()
        try:
            with open("/proc/uptime", "r") as f:
                up_sec = float(f.readline().split()[0])
                self._boot_time = time.time() - up_sec
        except Exception:
            pass

    def get_platform_name(self) -> str:
        return "android_termux"

    def get_battery_status(self) -> Dict[str, Any]:
        """Query native Android battery via termux-battery-status."""
        if shutil.which("termux-battery-status"):
            try:
                proc = subprocess.run(
                    ["termux-battery-status"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    data = json.loads(proc.stdout)
                    return {
                        "supported": True,
                        "percentage": data.get("percentage"),
                        "charging": data.get("status") == "CHARGING" or data.get("plugged") != "UNPLUGGED",
                        "status": data.get("status", "Unknown"),
                        "temperature": data.get("temperature", 0.0),
                        "health": data.get("health", "GOOD"),
                    }
            except Exception:
                pass
        return super().get_battery_status()

    def get_system_info(self) -> Dict[str, Any]:
        info = super().get_system_info()
        info["android_environment"] = {
            "termux_version": os.environ.get("TERMUX_VERSION", "Unknown"),
            "termux_api_installed": bool(shutil.which("termux-battery-status")),
            "storage_permission_note": "Ensure 'termux-setup-storage' was run to access ~/storage/shared",
            "background_policy": "Android may kill idle tasks when screen off unless 'termux-wake-lock' is active",
        }
        return info

