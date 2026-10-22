"""Linux Platform Adapter for GDR-AI Device Mesh."""

import time
from gdr.mesh.platform.base import BasePlatformAdapter


class LinuxPlatformAdapter(BasePlatformAdapter):
    """Adapter for Linux desktops, servers, and Raspberry Pi."""

    def __init__(self):
        self._boot_time = time.time()
        try:
            with open("/proc/uptime", "r") as f:
                up_sec = float(f.readline().split()[0])
                self._boot_time = time.time() - up_sec
        except Exception:
            pass

    def get_platform_name(self) -> str:
        return "linux"

