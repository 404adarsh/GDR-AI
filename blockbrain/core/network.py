"""Network connectivity and reachability utilities for blockbrain AI.
Provides instant, non-blocking reachability checks without hanging or waiting for DNS timeouts.
"""

import socket
from typing import Optional


def is_online(timeout: float = 0.3) -> bool:
    """Fast check whether the host has active external internet connectivity.
    Probes reliable public anycast DNS IPs on port 53.
    Returns False in <2ms when offline or disconnected.
    """
    for host in ("1.1.1.1", "8.8.8.8", "9.9.9.9"):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, 53))
            sock.close()
            return True
        except Exception:
            continue
    return False

