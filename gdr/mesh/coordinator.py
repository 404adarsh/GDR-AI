"""GDR-AI Mesh Coordinator.
Manages device registration, pairing code generation, token authentication,
device status tracking, capability verification, task lifecycle routing, and panic kill.
"""

import asyncio
import hashlib
import json
import logging
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from gdr.mesh.models import (
    PlatformType,
    DeviceStatus,
    TaskStatus,
    Device,
    DevicePermissions,
    MeshTask,
    PairingCode,
    STANDARD_CAPABILITIES,
)
from gdr.mesh.platform.base import get_platform_adapter

logger = logging.getLogger("gdr.mesh.coordinator")

FORBIDDEN_COMMAND_PATTERNS = [
    r"\brm\s+-(?:[a-zA-Z]*r[a-zA-Z]*f|[a-zA-Z]*f[a-zA-Z]*r)\s+/(?:$|\s|etc|var|usr|bin|boot|dev|sys|proc)",
    r"\bmkfs\b",
    r":\(\)\s*\{",
    r"\bdd\s+if=/dev/zero\s+of=/dev/sd",
    r"\bchmod\s+-R\s+777\s+/",
    r"\bchown\s+-R\s+.*\s+/",
    r">\s*/dev/sd[a-z]",
]

MAX_TERMINAL_OUTPUT_CHARS = 50_000


from gdr.config import get_gdr_config_dir


def _resolve_mesh_db(path: Optional[Path] = None) -> Path:
    if path:
        return path
    cfg_env = os.environ.get("GDR_CONFIG_DIR")
    if cfg_env:
        return Path(cfg_env) / "mesh.db"
    target = get_gdr_config_dir() / "mesh.db"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            with open(target, "a"):
                pass
        else:
            with open(target, "w"):
                pass
        return target
    except Exception:
        alt = Path("/tmp/gdr/mesh.db")
        alt.parent.mkdir(parents=True, exist_ok=True)
        return alt



class MeshCoordinator:
    """Central manager for GDR-AI multi-device mesh operations."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = _resolve_mesh_db(db_path)
        self._active_connections: Dict[str, Any] = {}  # device_id -> WebSocket
        self._pending_tasks: Dict[str, asyncio.Future] = {}  # task_id -> asyncio.Future
        self._pairing_codes: Dict[str, PairingCode] = {}  # code -> PairingCode
        self._pairing_attempts: List[float] = []  # timestamps for rate limiting
        self._lock = asyncio.Lock()
        self.local_adapter = get_platform_adapter()

        self._init_db()
        self._ensure_local_device()

    def _get_conn(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS mesh_devices (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        platform TEXT NOT NULL,
                        ip_address TEXT,
                        status TEXT NOT NULL,
                        last_seen REAL NOT NULL,
                        battery TEXT,
                        system_metrics TEXT,
                        capabilities TEXT,
                        permissions TEXT,
                        auth_token_hash TEXT,
                        created_at REAL NOT NULL,
                        latency_ms REAL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS mesh_tasks (
                        task_id TEXT PRIMARY KEY,
                        target_device_id TEXT NOT NULL,
                        capability TEXT NOT NULL,
                        parameters TEXT,
                        source_device_id TEXT,
                        status TEXT NOT NULL,
                        idempotency_key TEXT,
                        requires_approval INTEGER DEFAULT 0,
                        approved INTEGER DEFAULT 0,
                        result TEXT,
                        error TEXT,
                        created_at REAL NOT NULL,
                        completed_at REAL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS mesh_audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        device_id TEXT,
                        action TEXT NOT NULL,
                        details TEXT,
                        timestamp REAL NOT NULL
                    )
                """)
                # Migrations for existing tables
                for col, defn in [
                    ("idempotency_key", "TEXT"),
                    ("requires_approval", "INTEGER DEFAULT 0"),
                    ("approved", "INTEGER DEFAULT 0"),
                ]:
                    try:
                        conn.execute(f"ALTER TABLE mesh_tasks ADD COLUMN {col} {defn};")
                    except Exception:
                        pass
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to init mesh DB: {e}")

    def _ensure_local_device(self):
        """Register the primary host device in the mesh database."""
        try:
            with self._get_conn() as conn:
                row = conn.execute("SELECT id FROM mesh_devices WHERE id = 'local_primary'").fetchone()
                if not row:
                    plat = self.local_adapter.get_platform_name()
                    dev = Device(
                        id="local_primary",
                        name=f"Primary Host ({plat.capitalize()})",
                        platform=PlatformType(plat) if plat in [p.value for p in PlatformType] else PlatformType.LINUX,
                        status=DeviceStatus.ONLINE,
                        last_seen=time.time(),
                        capabilities=list(STANDARD_CAPABILITIES.keys()),
                        permissions=DevicePermissions(read_only=False, allow_shell_commands=True, allow_screen_interact=True, allow_process_control=True),
                        auth_token_hash=hashlib.sha256(b"local_primary_token").hexdigest(),
                    )
                    conn.execute("""
                        INSERT INTO mesh_devices (
                            id, name, platform, ip_address, status, last_seen,
                            battery, system_metrics, capabilities, permissions,
                            auth_token_hash, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        dev.id, dev.name, dev.platform.value, dev.ip_address, dev.status.value, dev.last_seen,
                        json.dumps(dev.battery), json.dumps(dev.system_metrics),
                        json.dumps(dev.capabilities), json.dumps(dev.permissions.to_dict()),
                        dev.auth_token_hash, dev.created_at
                    ))
                    conn.commit()
        except Exception:
            pass

    def log_audit(self, device_id: str, action: str, details: Any):
        """Record a security audit log event."""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT INTO mesh_audit_log (device_id, action, details, timestamp) VALUES (?, ?, ?, ?)",
                    (device_id, action, json.dumps(details) if not isinstance(details, str) else details, time.time())
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Audit log failure: {e}")

    def get_audit_logs(self, limit: int = 50, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve recent audit logs."""
        with self._get_conn() as conn:
            if device_id:
                rows = conn.execute("SELECT * FROM mesh_audit_log WHERE device_id = ? ORDER BY timestamp DESC LIMIT ?", (device_id, limit)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM mesh_audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            logs = []
            for r in rows:
                d = dict(r)
                try:
                    d["details"] = json.loads(d["details"]) if d["details"] else {}
                except Exception:
                    pass
                logs.append(d)
            return logs

    # --------------------------------------------------------------------------
    # Pairing and Enrollment
    # --------------------------------------------------------------------------

    def generate_pairing_code(
        self,
        requester_name: str = "New Device",
        requester_platform: PlatformType = PlatformType.UNKNOWN,
        requested_permissions: Optional[DevicePermissions] = None,
        ttl_seconds: int = 300
    ) -> Tuple[str, PairingCode]:
        """Generate a cryptographically secure 6-digit pairing code with 5-minute expiry."""
        now = time.time()
        self._pairing_codes = {k: v for k, v in self._pairing_codes.items() if not v.is_expired()}

        # Rate-limiting: max 6 pairing codes per 60 seconds
        self._pairing_attempts = [t for t in self._pairing_attempts if (now - t) < 60]
        if len(self._pairing_attempts) >= 6:
            raise ValueError("Rate limit exceeded for pairing code creation. Please wait 60 seconds.")
        self._pairing_attempts.append(now)

        code = f"{secrets.randbelow(900000) + 100000:06d}"
        pairing = PairingCode(
            code=code,
            expires_at=now + ttl_seconds,
            requester_name=requester_name,
            requester_platform=requester_platform,
            requested_permissions=requested_permissions or DevicePermissions(),
        )
        self._pairing_codes[code] = pairing
        self.log_audit("coordinator", "pairing_code_generated", {"code": code, "expires_in": ttl_seconds})
        return code, pairing

    def verify_and_pair(
        self,
        code: str,
        device_name: str,
        platform_name: str,
        ip_address: str = "127.0.0.1",
        capabilities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Validate pairing code, enroll the device, and issue a long-lived auth token."""
        code_str = code.strip()
        pairing = self._pairing_codes.get(code_str)

        if not pairing:
            self.log_audit("coordinator", "pairing_failed_unknown_code", {"code": code_str, "ip": ip_address})
            return {"success": False, "error": "Invalid pairing code."}

        if pairing.is_expired():
            self._pairing_codes.pop(code_str, None)
            self.log_audit("coordinator", "pairing_failed_expired_code", {"code": code_str})
            return {"success": False, "error": "Pairing code has expired. Please generate a new code."}

        pairing.used = True
        self._pairing_codes.pop(code_str, None)

        dev_id = f"dev_{secrets.token_hex(6)}"
        raw_token = pairing.device_token
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        try:
            plat = PlatformType(platform_name.lower())
        except Exception:
            plat = PlatformType.UNKNOWN

        # Default capabilities tailored to platform
        default_caps = ["system.read", "filesystem.read", "notifications.send"]
        if plat in (PlatformType.LINUX, PlatformType.ANDROID_TERMUX, PlatformType.MACOS):
            default_caps.append("terminal.execute")
        if plat in (PlatformType.LINUX, PlatformType.WINDOWS, PlatformType.MACOS):
            default_caps.append("screen.capture")

        dev = Device(
            id=dev_id,
            name=device_name.strip() or f"{plat.value.capitalize()} Node",
            platform=plat,
            ip_address=ip_address,
            status=DeviceStatus.ONLINE,
            last_seen=time.time(),
            capabilities=capabilities or default_caps,
            permissions=pairing.requested_permissions,
            auth_token_hash=token_hash,
            created_at=time.time(),
        )

        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO mesh_devices (
                    id, name, platform, ip_address, status, last_seen,
                    battery, system_metrics, capabilities, permissions,
                    auth_token_hash, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dev.id, dev.name, dev.platform.value, dev.ip_address, dev.status.value, dev.last_seen,
                json.dumps(dev.battery), json.dumps(dev.system_metrics),
                json.dumps(dev.capabilities), json.dumps(dev.permissions.to_dict()),
                dev.auth_token_hash, dev.created_at
            ))
            conn.commit()

        self.log_audit(dev_id, "device_paired", {"name": dev.name, "platform": dev.platform.value, "ip": ip_address})
        return {
            "success": True,
            "device_id": dev_id,
            "device_name": dev.name,
            "device_token": raw_token,
            "permissions": dev.permissions.to_dict(),
        }

    def authenticate_token(self, token: str) -> Optional[Device]:
        """Authenticate an incoming device connection via Bearer token."""
        if not token or not token.strip():
            return None
        token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM mesh_devices WHERE auth_token_hash = ?", (token_hash,)).fetchone()
            if not row or row["status"] == DeviceStatus.REVOKED.value:
                return None
            return self._row_to_device(row)

    def revoke_device(self, device_id: str) -> bool:
        """Revoke device authorization and immediately disconnect its active session."""
        if device_id == "local_primary":
            return False

        with self._get_conn() as conn:
            conn.execute("UPDATE mesh_devices SET status = ? WHERE id = ?", (DeviceStatus.REVOKED.value, device_id))
            conn.commit()

        ws = self._active_connections.pop(device_id, None)
        if ws:
            try:
                asyncio.create_task(ws.close(code=1008, reason="Device Revoked"))
            except Exception:
                pass

        self.log_audit(device_id, "device_revoked", {})
        return True

    def rename_device(self, device_id: str, new_name: str) -> bool:
        """Update the human-readable display name of a device."""
        clean = new_name.strip()
        if not clean:
            return False
        with self._get_conn() as conn:
            conn.execute("UPDATE mesh_devices SET name = ? WHERE id = ?", (clean, device_id))
            conn.commit()
            updated = conn.total_changes > 0
        if updated:
            self.log_audit(device_id, "device_renamed", {"new_name": clean})
        return updated

    def remove_device(self, device_id: str) -> bool:
        """Unenroll and delete a device record completely."""
        if device_id == "local_primary":
            return False
        self.revoke_device(device_id)
        with self._get_conn() as conn:
            conn.execute("DELETE FROM mesh_devices WHERE id = ?", (device_id,))
            conn.commit()
        self.log_audit(device_id, "device_removed", {})
        return True

    # --------------------------------------------------------------------------
    # Device Management & Telemetry
    # --------------------------------------------------------------------------

    def list_devices(self) -> List[Dict[str, Any]]:
        """Return all enrolled devices with real-time status and active metrics."""
        devices = []
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM mesh_devices ORDER BY created_at ASC").fetchall()
            for r in rows:
                dev = self._row_to_device(r)
                if dev.id == "local_primary":
                    dev.system_metrics = self.local_adapter.get_system_info()
                    dev.battery = self.local_adapter.get_battery_status()
                    dev.last_seen = time.time()
                    dev.status = DeviceStatus.ONLINE
                elif dev.id in self._active_connections:
                    dev.status = DeviceStatus.ONLINE
                elif not dev.is_active():
                    dev.status = DeviceStatus.OFFLINE
                devices.append(dev.to_dict())
        return devices

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Return a single device by ID."""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM mesh_devices WHERE id = ?", (device_id,)).fetchone()
            if not row:
                return None
            dev = self._row_to_device(row)
            if dev.id == "local_primary":
                dev.status = DeviceStatus.ONLINE
            elif dev.id in self._active_connections:
                dev.status = DeviceStatus.ONLINE
            elif not dev.is_active():
                dev.status = DeviceStatus.OFFLINE
            return dev.to_dict()

    def update_device_permissions(self, device_id: str, new_permissions: Dict[str, Any]) -> bool:
        """Update permissions for a specific device node."""
        perms = DevicePermissions.from_dict(new_permissions)
        with self._get_conn() as conn:
            conn.execute("UPDATE mesh_devices SET permissions = ? WHERE id = ?", (json.dumps(perms.to_dict()), device_id))
            conn.commit()
        self.log_audit(device_id, "permissions_updated", perms.to_dict())
        return True

    def update_device_heartbeat(self, device_id: str, metrics: Dict[str, Any], battery: Dict[str, Any], latency_ms: Optional[float] = None):
        """Update telemetry and timestamp for a connected node."""
        with self._get_conn() as conn:
            conn.execute("""
                UPDATE mesh_devices SET
                    last_seen = ?,
                    system_metrics = ?,
                    battery = ?,
                    latency_ms = COALESCE(?, latency_ms),
                    status = CASE WHEN status = 'revoked' THEN 'revoked' ELSE 'online' END
                WHERE id = ?
            """, (time.time(), json.dumps(metrics), json.dumps(battery), latency_ms, device_id))
            conn.commit()

    # --------------------------------------------------------------------------
    # WebSocket Connection Registration
    # --------------------------------------------------------------------------

    def register_connection(self, device_id: str, websocket: Any):
        # Handle duplicate sessions cleanly
        existing_ws = self._active_connections.pop(device_id, None)
        if existing_ws:
            try:
                asyncio.create_task(existing_ws.close(code=1000, reason="Superseded by new session"))
            except Exception:
                pass

        self._active_connections[device_id] = websocket
        with self._get_conn() as conn:
            conn.execute("UPDATE mesh_devices SET status = 'online', last_seen = ? WHERE id = ?", (time.time(), device_id))
            conn.commit()
        self.log_audit(device_id, "agent_connected", {})

    def unregister_connection(self, device_id: str):
        self._active_connections.pop(device_id, None)
        with self._get_conn() as conn:
            conn.execute("UPDATE mesh_devices SET status = 'offline' WHERE id = ? AND status != 'revoked'", (device_id,))
            conn.commit()
        self.log_audit(device_id, "agent_disconnected", {})

    # --------------------------------------------------------------------------
    # Cross-Device Task Routing & Execution
    # --------------------------------------------------------------------------

    def get_task_by_idempotency_key(self, key: str) -> Optional[Dict[str, Any]]:
        """Look up prior task execution by idempotency key to prevent double execution."""
        if not key:
            return None
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM mesh_tasks WHERE idempotency_key = ?", (key,)).fetchone()
            if not row:
                return None
            d = dict(row)
            try:
                d["parameters"] = json.loads(d["parameters"]) if d["parameters"] else {}
            except Exception:
                pass
            try:
                d["result"] = json.loads(d["result"]) if d["result"] else d["result"]
            except Exception:
                pass
            return d

    async def dispatch_task(
        self,
        target_device_id: str,
        capability: str,
        parameters: Dict[str, Any],
        source_device_id: str = "coordinator",
        timeout: float = 30.0,
        idempotency_key: Optional[str] = None,
        approved: bool = False
    ) -> Dict[str, Any]:
        """Dispatch a task to a local or remote mesh device and await results with strict security gates."""
        # 1. Check idempotency
        if idempotency_key:
            cached = self.get_task_by_idempotency_key(idempotency_key)
            if cached and cached["status"] in (TaskStatus.COMPLETED.value, TaskStatus.RUNNING.value):
                return {
                    "success": cached["status"] == TaskStatus.COMPLETED.value,
                    "task_id": cached["task_id"],
                    "target_device_id": cached["target_device_id"],
                    "status": cached["status"],
                    "result": cached.get("result"),
                    "error": cached.get("error"),
                    "idempotent_cached": True
                }

        task_id = f"task_{secrets.token_hex(6)}"
        task = MeshTask(
            task_id=task_id,
            target_device_id=target_device_id,
            capability=capability,
            parameters=parameters,
            source_device_id=source_device_id,
            status=TaskStatus.QUEUED,
            idempotency_key=idempotency_key,
            approved=approved,
            timeout_seconds=timeout,
        )

        # 2. Verify target device exists and is not revoked
        dev = self.get_device(target_device_id)
        if not dev:
            return {"success": False, "task_id": task_id, "error": f"Device '{target_device_id}' is not enrolled in the mesh."}

        if dev["status"] == DeviceStatus.REVOKED.value:
            return {"success": False, "task_id": task_id, "error": f"Device '{dev['name']}' has been REVOKED from the mesh."}

        # 3. Check capability permission on device
        perms = dev.get("permissions") or {}
        cap_def = STANDARD_CAPABILITIES.get(capability)
        if cap_def:
            req_perm = cap_def.required_permission
            if not perms.get(req_perm, True):
                self.log_audit(target_device_id, "task_rejected_permission_denied", {
                    "capability": capability, "required_permission": req_perm
                })
                return {
                    "success": False,
                    "task_id": task_id,
                    "error": f"Permission denied: Device '{dev['name']}' lacks '{req_perm}' for capability '{capability}'."
                }

            # Check approval requirement
            if cap_def.requires_approval and not approved:
                task.status = TaskStatus.WAITING_APPROVAL
                self._save_task(task)
                return {
                    "success": False,
                    "task_id": task_id,
                    "status": "waiting_approval",
                    "requires_approval": True,
                    "error": f"Action '{capability}' on device '{dev['name']}' requires explicit confirmation."
                }

        # 4. Security check for terminal command execution
        if capability in ("terminal.execute", "terminal", "shell"):
            cmd = parameters.get("command", "")
            for pattern in FORBIDDEN_COMMAND_PATTERNS:
                if re.search(pattern, cmd, re.IGNORECASE):
                    self.log_audit(target_device_id, "terminal_command_blocked_security_policy", {"command": cmd})
                    return {
                        "success": False,
                        "task_id": task_id,
                        "error": "Command blocked by security policy: Potentially destructive system command."
                    }

        # 5. Local execution on coordinator host
        if target_device_id in ("local_primary", "localhost", "local"):
            task.status = TaskStatus.RUNNING
            self._save_task(task)
            return await self._execute_locally(task)

        # 6. Remote execution over WebSocket
        ws = self._active_connections.get(target_device_id)
        if not ws:
            task.status = TaskStatus.DEVICE_DISCONNECTED
            task.error = f"Device '{dev['name']}' ({dev['platform']}) is currently OFFLINE."
            self._save_task(task)
            return {
                "success": False,
                "task_id": task_id,
                "error": task.error
            }

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self._pending_tasks[task_id] = fut

        task.status = TaskStatus.DISPATCHED
        self._save_task(task)

        payload = {
            "type": "task_request",
            "task_id": task_id,
            "capability": capability,
            "parameters": parameters,
            "timeout": timeout,
        }

        try:
            await ws.send_text(json.dumps(payload))
            response_data = await asyncio.wait_for(fut, timeout=timeout)
            task.status = TaskStatus.COMPLETED if response_data.get("success") else TaskStatus.FAILED
            task.result = response_data.get("result")
            task.error = response_data.get("error")
            task.completed_at = time.time()
            self._save_task(task)
            return {
                "success": task.status == TaskStatus.COMPLETED,
                "task_id": task_id,
                "target_device_id": target_device_id,
                "result": task.result,
                "error": task.error
            }
        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            task.error = f"Operation on device '{target_device_id}' timed out after {timeout}s."
            task.completed_at = time.time()
            self._save_task(task)
            return {"success": False, "task_id": task_id, "error": task.error}
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.error = "Task was cancelled."
            task.completed_at = time.time()
            self._save_task(task)
            return {"success": False, "task_id": task_id, "error": "Task cancelled."}
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()
            self._save_task(task)
            return {"success": False, "task_id": task_id, "error": str(e)}
        finally:
            self._pending_tasks.pop(task_id, None)

    def handle_agent_task_result(self, task_id: str, result_data: Dict[str, Any]):
        """Callback when agent finishes a dispatched task over WebSocket."""
        fut = self._pending_tasks.get(task_id)
        if fut and not fut.done():
            fut.set_result(result_data)

    async def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Cancel an in-flight or queued task."""
        fut = self._pending_tasks.pop(task_id, None)
        if fut and not fut.done():
            fut.cancel()

        target_id = None
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM mesh_tasks WHERE task_id = ?", (task_id,)).fetchone()
            if not row:
                return {"success": False, "error": f"Task '{task_id}' not found."}
            target_id = row["target_device_id"]
            conn.execute("UPDATE mesh_tasks SET status = 'cancelled', completed_at = ? WHERE task_id = ?", (time.time(), task_id))
            conn.commit()

        if target_id:
            ws = self._active_connections.get(target_id)
            if ws:
                try:
                    await ws.send_text(json.dumps({"type": "task_cancel", "task_id": task_id}))
                except Exception:
                    pass

        self.log_audit(target_id or "unknown", "task_cancelled", {"task_id": task_id})
        return {"success": True, "task_id": task_id, "status": "cancelled"}

    async def panic_kill_all(self) -> Dict[str, Any]:
        """Emergency stop: cancel all in-flight tasks and signal all connected agents."""
        cancelled = []
        for task_id, fut in list(self._pending_tasks.items()):
            if not fut.done():
                fut.cancel()
                cancelled.append(task_id)
        self._pending_tasks.clear()

        try:
            with self._get_conn() as conn:
                conn.execute(
                    "UPDATE mesh_tasks SET status = 'cancelled', completed_at = ? WHERE status IN ('queued', 'dispatched', 'pending', 'running', 'waiting_approval')",
                    (time.time(),)
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to cancel tasks in DB: {e}")

        signaled = []
        for dev_id, ws in list(self._active_connections.items()):
            try:
                await ws.send_text(json.dumps({"type": "panic_kill", "timestamp": time.time()}))
                signaled.append(dev_id)
            except Exception:
                pass

        self.log_audit("coordinator", "mesh_panic_kill", {
            "cancelled_tasks": cancelled,
            "signaled_devices": signaled
        })

        return {
            "success": True,
            "cancelled_tasks_count": len(cancelled),
            "cancelled_task_ids": cancelled,
            "signaled_devices": signaled,
            "message": f"Panic Kill executed: {len(cancelled)} task(s) cancelled, {len(signaled)} device agent(s) signaled."
        }

    async def _execute_locally(self, task: MeshTask) -> Dict[str, Any]:
        """Execute task on the local primary machine using the platform adapter."""
        cap = task.capability
        params = task.parameters
        dev_info = self.get_device("local_primary")
        approved_dirs = self.local_adapter.resolve_approved_directories(
            (dev_info.get("permissions") or {}).get("allowed_directories", ["~/Downloads", "~/Documents"])
        )

        try:
            if cap in ("sys_info", "system_info", "system.read"):
                res = self.local_adapter.get_system_info()
                task.status = TaskStatus.COMPLETED
                task.result = res
            elif cap in ("battery_status", "battery"):
                res = self.local_adapter.get_battery_status()
                task.status = TaskStatus.COMPLETED
                task.result = res
            elif cap in ("file_search", "search_files", "filesystem.read"):
                q = params.get("query", "")
                res = self.local_adapter.search_files(q, approved_dirs)
                task.status = TaskStatus.COMPLETED
                task.result = res
            elif cap in ("file_read", "read_file"):
                fpath = params.get("path", "")
                res = self.local_adapter.read_file(fpath, approved_dirs)
                task.status = TaskStatus.COMPLETED if res.get("success") else TaskStatus.FAILED
                task.result = res.get("content") if res.get("success") else None
                task.error = res.get("error")
            elif cap in ("diagnostic_check", "diagnostic"):
                cmd = params.get("command", "uptime")
                res = self.local_adapter.execute_diagnostic(cmd)
                task.status = TaskStatus.COMPLETED if res.get("success") else TaskStatus.FAILED
                task.result = res.get("stdout") if res.get("success") else None
                task.error = res.get("error") or res.get("stderr")
            elif cap in ("terminal.execute", "terminal", "shell"):
                cmd = params.get("command", "")
                import subprocess
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=params.get("timeout", 20))
                out = (proc.stdout or proc.stderr)[:MAX_TERMINAL_OUTPUT_CHARS]
                task.status = TaskStatus.COMPLETED if proc.returncode == 0 else TaskStatus.FAILED
                task.result = out
                task.error = proc.stderr if proc.returncode != 0 else None
            elif cap in ("notifications.send", "notification"):
                title = params.get("title", "GDR-AI")
                msg = params.get("message", "")
                import shutil
                if shutil.which("notify-send"):
                    subprocess.run(["notify-send", title, msg], check=False)
                task.status = TaskStatus.COMPLETED
                task.result = f"Notification delivered: '{title}: {msg}'"
            else:
                task.status = TaskStatus.FAILED
                task.error = f"Unsupported capability '{cap}' on local primary node."

            task.completed_at = time.time()
            self._save_task(task)
            return {
                "success": task.status == TaskStatus.COMPLETED,
                "task_id": task.task_id,
                "target_device_id": "local_primary",
                "result": task.result,
                "error": task.error
            }
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()
            self._save_task(task)
            return {"success": False, "task_id": task.task_id, "error": str(e)}

    def _save_task(self, task: MeshTask):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO mesh_tasks (
                        task_id, target_device_id, capability, parameters,
                        source_device_id, status, idempotency_key, requires_approval,
                        approved, result, error, created_at, completed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task.task_id, task.target_device_id, task.capability,
                    json.dumps(task.parameters), task.source_device_id,
                    task.status.value, task.idempotency_key,
                    1 if task.requires_approval else 0,
                    1 if task.approved else 0,
                    json.dumps(task.result) if not isinstance(task.result, (str, type(None))) else task.result,
                    task.error, task.created_at, task.completed_at
                ))
                conn.commit()
        except Exception as e:
            logger.warning(f"Error saving task {task.task_id}: {e}")

    def _row_to_device(self, row: sqlite3.Row) -> Device:
        try:
            plat = PlatformType(row["platform"])
        except Exception:
            plat = PlatformType.UNKNOWN

        try:
            st = DeviceStatus(row["status"])
        except Exception:
            st = DeviceStatus.OFFLINE

        try:
            battery = json.loads(row["battery"]) if row["battery"] else {}
        except Exception:
            battery = {}

        try:
            metrics = json.loads(row["system_metrics"]) if row["system_metrics"] else {}
        except Exception:
            metrics = {}

        try:
            caps = json.loads(row["capabilities"]) if row["capabilities"] else []
        except Exception:
            caps = []

        try:
            perms_dict = json.loads(row["permissions"]) if row["permissions"] else {}
            perms = DevicePermissions.from_dict(perms_dict)
        except Exception:
            perms = DevicePermissions()

        return Device(
            id=row["id"],
            name=row["name"],
            platform=plat,
            ip_address=row["ip_address"] or "127.0.0.1",
            status=st,
            last_seen=row["last_seen"],
            battery=battery,
            system_metrics=metrics,
            capabilities=caps,
            permissions=perms,
            auth_token_hash=row["auth_token_hash"] or "",
            created_at=row["created_at"],
            latency_ms=row["latency_ms"],
        )


_COORDINATOR: Optional[MeshCoordinator] = None


def get_mesh_coordinator() -> MeshCoordinator:
    global _COORDINATOR
    if _COORDINATOR is None:
        _COORDINATOR = MeshCoordinator()
    return _COORDINATOR
