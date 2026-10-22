"""Base platform adapter and factory for GDR-AI Device Mesh."""

import os
import platform
import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List, Optional


class BasePlatformAdapter(ABC):
    """Abstract base adapter for cross-platform device operations."""

    @abstractmethod
    def get_platform_name(self) -> str:
        """Return standardized platform identifier ('linux', 'android_termux', 'windows', 'macos')."""
        pass

    def get_system_info(self) -> Dict[str, Any]:
        """Collect standardized system metrics: CPU, RAM, Disk, Uptime, OS."""
        cpu_pct = 0.0
        ram_pct = 0.0
        ram_total_gb = 0.0
        ram_free_gb = 0.0
        disk_free_gb = 0.0
        disk_total_gb = 0.0

        try:
            import psutil
            cpu_pct = round(psutil.cpu_percent(interval=0.1), 1)
            vmem = psutil.virtual_memory()
            ram_pct = round(vmem.percent, 1)
            ram_total_gb = round(vmem.total / (1024**3), 2)
            ram_free_gb = round(vmem.available / (1024**3), 2)
            disk = psutil.disk_usage(os.path.expanduser("~"))
            disk_free_gb = round(disk.free / (1024**3), 2)
            disk_total_gb = round(disk.total / (1024**3), 2)
        except Exception:
            # Fallback without psutil
            try:
                stat = os.statvfs(os.path.expanduser("~"))
                disk_free_gb = round((stat.f_bavail * stat.f_frsize) / (1024**3), 2)
                disk_total_gb = round((stat.f_blocks * stat.f_frsize) / (1024**3), 2)
            except Exception:
                pass

        return {
            "platform": self.get_platform_name(),
            "os_name": platform.system(),
            "os_release": platform.release(),
            "hostname": platform.node(),
            "architecture": platform.machine(),
            "cpu_percent": cpu_pct,
            "ram_percent": ram_pct,
            "ram_total_gb": ram_total_gb,
            "ram_free_gb": ram_free_gb,
            "disk_free_gb": disk_free_gb,
            "disk_total_gb": disk_total_gb,
            "uptime_seconds": round(time.time() - getattr(self, "_boot_time", time.time())),
        }

    def get_battery_status(self) -> Dict[str, Any]:
        """Return battery metrics if supported by device."""
        try:
            import psutil
            if hasattr(psutil, "sensors_battery"):
                b = psutil.sensors_battery()
                if b is not None:
                    return {
                        "supported": True,
                        "percentage": int(b.percent),
                        "charging": bool(b.power_plugged),
                        "secsleft": b.secsleft if b.secsleft > 0 else None,
                    }
        except Exception:
            pass
        return {"supported": False, "percentage": None, "charging": None}

    def resolve_approved_directories(self, raw_paths: List[str]) -> List[Path]:
        """Safely resolve path strings to existing canonical Path objects."""
        resolved: List[Path] = []
        for p_str in raw_paths:
            try:
                p = Path(os.path.expanduser(p_str)).resolve()
                if p.exists() and p.is_dir():
                    resolved.append(p)
            except Exception:
                continue
        return resolved

    def is_path_safe(self, target_path: Path, approved_dirs: List[Path]) -> bool:
        """Enforce strict directory traversal defense."""
        target_resolved = target_path.resolve()
        for root in approved_dirs:
            try:
                root_resolved = root.resolve()
                # Python 3.9+ is_relative_to
                if hasattr(target_resolved, "is_relative_to"):
                    if target_resolved.is_relative_to(root_resolved):
                        return True
                else:
                    target_resolved.relative_to(root_resolved)
                    return True
            except (ValueError, Exception):
                continue
        return False

    def search_files(self, query: str, approved_dirs: List[Path], max_results: int = 25) -> List[Dict[str, Any]]:
        """Search approved directories for files matching query."""
        results: List[Dict[str, Any]] = []
        q_lower = query.lower().strip()
        for root in approved_dirs:
            try:
                for dirpath, dirnames, filenames in os.walk(str(root)):
                    # Don't recurse into hidden or system cache folders
                    dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("__pycache__", "node_modules", ".venv")]
                    for fname in filenames:
                        if fname.startswith("."):
                            continue
                        if not q_lower or q_lower in fname.lower():
                            fpath = Path(dirpath) / fname
                            try:
                                stat = fpath.stat()
                                results.append({
                                    "filename": fname,
                                    "path": str(fpath),
                                    "size_bytes": stat.st_size,
                                    "modified_at": stat.st_mtime,
                                    "extension": fpath.suffix.lower(),
                                })
                                if len(results) >= max_results:
                                    return results
                            except Exception:
                                continue
            except Exception:
                continue
        return results

    def read_file(self, file_path_str: str, approved_dirs: List[Path], max_bytes: int = 500_000) -> Dict[str, Any]:
        """Read text or binary file from approved directory within bounds."""
        target = Path(os.path.expanduser(file_path_str)).resolve()
        if not self.is_path_safe(target, approved_dirs):
            return {
                "success": False,
                "error": f"Access denied: Path '{file_path_str}' is outside approved directories allowlist."
            }
        if not target.exists() or not target.is_file():
            return {"success": False, "error": f"File '{target.name}' not found or is a directory."}

        size = target.stat().st_size
        if size > max_bytes:
            return {
                "success": False,
                "error": f"File size ({round(size/1024, 1)} KB) exceeds safety limit ({round(max_bytes/1024, 1)} KB)."
            }

        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            import hashlib
            sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
            return {
                "success": True,
                "filename": target.name,
                "path": str(target),
                "size_bytes": size,
                "sha256": sha256,
                "content": content,
            }
        except Exception as e:
            return {"success": False, "error": f"Error reading file: {e}"}

    def execute_diagnostic(self, command: str) -> Dict[str, Any]:
        """Execute pre-approved, non-destructive diagnostic command."""
        # Strict security allowlist - NO raw shell injection permitted
        ALLOWLIST = [
            ["uptime"],
            ["df", "-h"],
            ["free", "-m"],
            ["ps", "aux"],
            ["uname", "-a"],
            ["whoami"],
            ["ping", "-c", "2", "8.8.8.8"],
        ]
        cmd_tokens = command.strip().split()
        if not cmd_tokens:
            return {"success": False, "error": "Empty command."}

        # Check against allowlist prefixes
        allowed = False
        for allowed_cmd in ALLOWLIST:
            if cmd_tokens[:len(allowed_cmd)] == allowed_cmd:
                allowed = True
                break

        if not allowed:
            return {
                "success": False,
                "error": f"Diagnostic command '{cmd_tokens[0]}' is outside the strict security allowlist."
            }

        try:
            proc = subprocess.run(
                cmd_tokens,
                capture_output=True,
                text=True,
                timeout=10,
                check=False
            )
            return {
                "success": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


def get_platform_adapter() -> BasePlatformAdapter:
    """Detect local runtime and return appropriate platform adapter."""
    # Check Android Termux first
    if bool("TERMUX_VERSION" in os.environ or os.path.exists("/data/data/com.termux") or shutil.which("termux-battery-status")):
        from gdr.mesh.platform.termux import TermuxPlatformAdapter
        return TermuxPlatformAdapter()

    sys_name = platform.system().lower()
    if sys_name == "linux":
        from gdr.mesh.platform.linux import LinuxPlatformAdapter
        return LinuxPlatformAdapter()
    elif sys_name == "windows":
        from gdr.mesh.platform.windows import WindowsPlatformAdapter
        return WindowsPlatformAdapter()
    elif sys_name == "darwin":
        from gdr.mesh.platform.macos import MacOSPlatformAdapter
        return MacOSPlatformAdapter()

    from gdr.mesh.platform.linux import LinuxPlatformAdapter
    return LinuxPlatformAdapter()

