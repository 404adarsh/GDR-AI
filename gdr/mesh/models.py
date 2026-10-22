"""Data models and schemas for GDR-AI Multi-Device Mesh.
Defines connection states, capability definitions, task lifecycles, and security permissions.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
import time
from typing import Dict, Any, List, Optional
import uuid


class PlatformType(str, Enum):
    LINUX = "linux"
    ANDROID_TERMUX = "android_termux"
    WINDOWS = "windows"
    MACOS = "macos"
    UNKNOWN = "unknown"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTED = "connected"
    PAIRING = "pairing"
    RECONNECTING = "reconnecting"
    BUSY = "busy"
    PERMISSION_REQUIRED = "permission_required"
    ERROR = "error"
    REVOKED = "revoked"


class TaskStatus(str, Enum):
    QUEUED = "queued"
    AUTHORIZED = "authorized"
    DISPATCHED = "dispatched"
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    DEVICE_DISCONNECTED = "device_disconnected"


@dataclass
class CapabilityDefinition:
    """Formal definition of a capability with security and platform constraints."""
    name: str
    platforms: List[PlatformType]
    description: str
    required_permission: str
    requires_approval: bool = False
    read_only: bool = True
    destructive: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "platforms": [p.value for p in self.platforms],
            "description": self.description,
            "required_permission": self.required_permission,
            "requires_approval": self.requires_approval,
            "read_only": self.read_only,
            "destructive": self.destructive,
        }


# Authoritative Capability Registry
STANDARD_CAPABILITIES: Dict[str, CapabilityDefinition] = {
    "system.read": CapabilityDefinition(
        name="system.read",
        platforms=[PlatformType.LINUX, PlatformType.ANDROID_TERMUX, PlatformType.WINDOWS, PlatformType.MACOS],
        description="Inspect hardware status, battery level, CPU, RAM, and disk utilization.",
        required_permission="allow_diagnostics",
        requires_approval=False,
        read_only=True,
    ),
    "filesystem.read": CapabilityDefinition(
        name="filesystem.read",
        platforms=[PlatformType.LINUX, PlatformType.ANDROID_TERMUX, PlatformType.WINDOWS, PlatformType.MACOS],
        description="Search and read files within user-approved directories.",
        required_permission="allow_file_transfer",
        requires_approval=False,
        read_only=True,
    ),
    "filesystem.write": CapabilityDefinition(
        name="filesystem.write",
        platforms=[PlatformType.LINUX, PlatformType.ANDROID_TERMUX, PlatformType.WINDOWS, PlatformType.MACOS],
        description="Write, edit, or create files within user-approved directories.",
        required_permission="allow_file_transfer",
        requires_approval=True,
        read_only=False,
    ),
    "terminal.execute": CapabilityDefinition(
        name="terminal.execute",
        platforms=[PlatformType.LINUX, PlatformType.ANDROID_TERMUX, PlatformType.MACOS, PlatformType.WINDOWS],
        description="Execute authorized shell scripts or terminal commands.",
        required_permission="allow_shell_commands",
        requires_approval=True,
        read_only=False,
        destructive=False,
    ),
    "screen.capture": CapabilityDefinition(
        name="screen.capture",
        platforms=[PlatformType.LINUX, PlatformType.WINDOWS, PlatformType.MACOS],
        description="Capture screenshot or OCR text of the visible desktop window.",
        required_permission="allow_screen_capture",
        requires_approval=False,
        read_only=True,
    ),
    "screen.interact": CapabilityDefinition(
        name="screen.interact",
        platforms=[PlatformType.LINUX, PlatformType.WINDOWS, PlatformType.MACOS],
        description="Simulate mouse clicks or key inputs into an authorized desktop window.",
        required_permission="allow_screen_interact",
        requires_approval=True,
        read_only=False,
    ),
    "process.inspect": CapabilityDefinition(
        name="process.inspect",
        platforms=[PlatformType.LINUX, PlatformType.ANDROID_TERMUX, PlatformType.WINDOWS, PlatformType.MACOS],
        description="List and inspect running processes.",
        required_permission="allow_diagnostics",
        requires_approval=False,
        read_only=True,
    ),
    "process.terminate": CapabilityDefinition(
        name="process.terminate",
        platforms=[PlatformType.LINUX, PlatformType.ANDROID_TERMUX, PlatformType.WINDOWS, PlatformType.MACOS],
        description="Terminate a running process by PID.",
        required_permission="allow_process_control",
        requires_approval=True,
        read_only=False,
        destructive=True,
    ),
    "notifications.send": CapabilityDefinition(
        name="notifications.send",
        platforms=[PlatformType.LINUX, PlatformType.ANDROID_TERMUX, PlatformType.WINDOWS, PlatformType.MACOS],
        description="Display system or mobile notification toast on target device.",
        required_permission="allow_notifications",
        requires_approval=False,
        read_only=False,
    ),
}


@dataclass
class DevicePermissions:
    """Explicit permission gates granted to a specific device node."""
    allowed_directories: List[str] = field(default_factory=lambda: ["~/Downloads", "~/Documents"])
    read_only: bool = True
    allow_diagnostics: bool = True
    allow_file_transfer: bool = True
    allow_shell_commands: bool = False
    allow_screen_capture: bool = True
    allow_screen_interact: bool = False
    allow_process_control: bool = False
    allow_notifications: bool = True
    confirmed_capabilities: List[str] = field(default_factory=lambda: [
        "sys_info",
        "battery_status",
        "file_search",
        "file_read",
        "diagnostic_check",
        "system.read",
        "filesystem.read",
        "notifications.send",
    ])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "DevicePermissions":
        if not data:
            return cls()
        return cls(
            allowed_directories=data.get("allowed_directories", ["~/Downloads", "~/Documents"]),
            read_only=bool(data.get("read_only", True)),
            allow_diagnostics=bool(data.get("allow_diagnostics", True)),
            allow_file_transfer=bool(data.get("allow_file_transfer", True)),
            allow_shell_commands=bool(data.get("allow_shell_commands", False)),
            allow_screen_capture=bool(data.get("allow_screen_capture", True)),
            allow_screen_interact=bool(data.get("allow_screen_interact", False)),
            allow_process_control=bool(data.get("allow_process_control", False)),
            allow_notifications=bool(data.get("allow_notifications", True)),
            confirmed_capabilities=data.get("confirmed_capabilities", [
                "sys_info", "battery_status", "file_search", "file_read",
                "diagnostic_check", "system.read", "filesystem.read", "notifications.send"
            ]),
        )


@dataclass
class Device:
    """Enrolled Device representation in the Mesh."""
    id: str
    name: str
    platform: PlatformType
    owner_user_id: str = "primary_user"
    ip_address: str = "127.0.0.1"
    status: DeviceStatus = DeviceStatus.OFFLINE
    last_seen: float = field(default_factory=time.time)
    battery: Dict[str, Any] = field(default_factory=lambda: {"percentage": None, "charging": False})
    system_metrics: Dict[str, Any] = field(default_factory=lambda: {"cpu_percent": 0.0, "ram_percent": 0.0, "disk_free_gb": 0.0})
    capabilities: List[str] = field(default_factory=lambda: [
        "sys_info", "battery_status", "file_search", "file_read",
        "system.read", "filesystem.read", "notifications.send"
    ])
    permissions: DevicePermissions = field(default_factory=DevicePermissions)
    auth_token_hash: str = ""
    created_at: float = field(default_factory=time.time)
    latency_ms: Optional[float] = None
    client_version: str = "2.0.0"

    def is_active(self, heartbeat_timeout: float = 65.0) -> bool:
        if self.status in (DeviceStatus.REVOKED, DeviceStatus.OFFLINE):
            return False
        return (time.time() - self.last_seen) <= heartbeat_timeout

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["platform"] = self.platform.value if isinstance(self.platform, PlatformType) else str(self.platform)
        if self.status == DeviceStatus.REVOKED:
            d["status"] = DeviceStatus.REVOKED.value
        else:
            d["status"] = DeviceStatus.ONLINE.value if self.is_active() else DeviceStatus.OFFLINE.value
        d.pop("auth_token_hash", None)
        return d


@dataclass
class PairingCode:
    """Short-lived pairing credential for enrolling a remote device."""
    code: str
    expires_at: float
    requester_name: str
    requester_platform: PlatformType
    requested_permissions: DevicePermissions = field(default_factory=DevicePermissions)
    created_at: float = field(default_factory=time.time)
    single_use: bool = True
    used: bool = False
    device_token: str = field(default_factory=lambda: f"gdr_mesh_tok_{uuid.uuid4().hex}")

    def is_expired(self) -> bool:
        return time.time() > self.expires_at or self.used


@dataclass
class MeshTask:
    """Traceable, idempotent cross-device task dispatch with execution history."""
    task_id: str
    target_device_id: str
    capability: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    source_device_id: str = "coordinator"
    status: TaskStatus = TaskStatus.QUEUED
    idempotency_key: Optional[str] = None
    requires_approval: bool = False
    approved: bool = False
    approved_by: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    timeout_seconds: float = 45.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, TaskStatus) else str(self.status)
        return d
