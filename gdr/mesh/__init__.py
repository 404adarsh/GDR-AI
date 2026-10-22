"""GDR-AI Secure Multi-Device AI Mesh Package.
Enables cross-device device connectivity, state synchronization,
and distributed task execution across Android Termux, Linux, Windows, and macOS.
"""

from gdr.mesh.models import (
    PlatformType,
    DeviceStatus,
    TaskStatus,
    Device,
    DevicePermissions,
    MeshTask,
    PairingCode,
)

__all__ = [
    "PlatformType",
    "DeviceStatus",
    "TaskStatus",
    "Device",
    "DevicePermissions",
    "MeshTask",
    "PairingCode",
]

