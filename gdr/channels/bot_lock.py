"""Inter-process lock supervisor for bot channel runners (Telegram, MarkanM).
Ensures that across any number of CLI commands, GUI launches, or background services,
exactly one active polling consumer runs per bot token without competing getUpdates conflicts.
"""

import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger("gdr.channels.bot_lock")


def _get_lock_dir() -> Path:
    import tempfile
    temp_dir = Path(tempfile.gettempdir())
    candidates = []
    if "GDR_RUNTIME_DIR" in os.environ:
        candidates.append(Path(os.environ["GDR_RUNTIME_DIR"]))
    candidates.append(Path.home() / ".config" / "gdr" / "locks")
    if "XDG_RUNTIME_DIR" in os.environ:
        candidates.append(Path(os.environ["XDG_RUNTIME_DIR"]) / "gdr_locks")
    uid = os.getuid() if hasattr(os, "getuid") else "user"
    candidates.append(temp_dir / f".gdr_locks_{uid}")

    for cand in candidates:
        try:
            cand.mkdir(parents=True, exist_ok=True)
            test_file = cand / ".test_write"
            test_file.touch(exist_ok=True)
            test_file.unlink(missing_ok=True)
            return cand
        except Exception:
            continue

    fallback = temp_dir / ".gdr_locks"
    fallback.mkdir(parents=True, exist_ok=True)
    return fallback


def _is_pid_alive(pid: int) -> bool:
    """Check if process with PID is currently running on Windows or Unix."""
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        try:
            import ctypes
            SYNCHRONIZE = 0x00100000
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE, False, pid)
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but owned by another user or elevated
        return True
    except Exception:
        return False


class BotProcessLock:
    """Acquires and manages an inter-process file lock for a bot polling worker."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.lock_file = _get_lock_dir() / f"{service_name}.lock"
        self._is_owner = False

    def acquire(self, owner_description: str = "gdr-service") -> Tuple[bool, Dict[str, Any]]:
        """Attempt to acquire exclusive ownership of this bot worker.
        Returns:
            (acquired: bool, info: dict)
        """
        my_pid = os.getpid()

        # Check existing lock file
        if self.lock_file.exists():
            try:
                content = self.lock_file.read_text(encoding="utf-8").strip()
                data = json.loads(content)
                existing_pid = int(data.get("pid", 0))

                if existing_pid == my_pid:
                    self._is_owner = True
                    return True, {"pid": my_pid, "owner": owner_description, "status": "reacquired"}

                if _is_pid_alive(existing_pid):
                    logger.info(
                        f"🔒 {self.service_name.capitalize()} bot polling is already active in PID {existing_pid} "
                        f"({data.get('owner', 'unknown')}). Skipping duplicate polling worker."
                    )
                    return False, {
                        "pid": existing_pid,
                        "owner": data.get("owner", "unknown"),
                        "status": "active_elsewhere",
                        "started_at": data.get("started_at")
                    }
                else:
                    logger.debug(f"Stale lock for {self.service_name} found (PID {existing_pid} is dead). Overriding.")
            except Exception as e:
                logger.debug(f"Could not parse existing lock file for {self.service_name}: {e}")

        # Write lock file
        try:
            lock_data = {
                "service": self.service_name,
                "pid": my_pid,
                "owner": owner_description,
                "started_at": time.time(),
                "started_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            self.lock_file.write_text(json.dumps(lock_data, indent=2), encoding="utf-8")
            self._is_owner = True
            logger.info(f"🔑 Acquired exclusive bot lock for {self.service_name} (PID {my_pid}).")
            return True, lock_data
        except Exception as e:
            logger.warning(f"Could not write lock file for {self.service_name}: {e}")
            return False, {"error": str(e)}

    def release(self) -> bool:
        """Release lock if owned by the current process."""
        my_pid = os.getpid()
        if not self.lock_file.exists():
            self._is_owner = False
            return True

        try:
            content = self.lock_file.read_text(encoding="utf-8").strip()
            data = json.loads(content)
            if int(data.get("pid", 0)) == my_pid:
                self.lock_file.unlink(missing_ok=True)
                self._is_owner = False
                logger.debug(f"🔓 Released bot lock for {self.service_name} (PID {my_pid}).")
                return True
        except Exception as e:
            logger.debug(f"Error releasing lock for {self.service_name}: {e}")
        return False

    def get_owner_info(self) -> Optional[Dict[str, Any]]:
        """Retrieve current lock owner information."""
        if not self.lock_file.exists():
            return None
        try:
            content = self.lock_file.read_text(encoding="utf-8").strip()
            data = json.loads(content)
            existing_pid = int(data.get("pid", 0))
            if _is_pid_alive(existing_pid):
                return data
        except Exception:
            pass
        return None
