"""Network connectivity and reachability utilities for GDR AI.
Provides instant, non-blocking reachability checks without hanging or waiting for DNS timeouts.
"""

import socket
from typing import Optional


def is_online(timeout: float = 1.2) -> bool:
    """Fast check whether the host has active external internet connectivity.
    Probes standard HTTPS (port 443) endpoints. Unlike TCP port 53, port 443
    is never blocked by college/home router firewalls or ISPs.
    """
    endpoints = [
        ("api.sarvam.ai", 443),
        ("1.1.1.1", 443),
        ("8.8.8.8", 443),
        ("www.google.com", 443),
    ]
    for host, port in endpoints:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.close()
            return True
        except Exception:
            continue
    return False

