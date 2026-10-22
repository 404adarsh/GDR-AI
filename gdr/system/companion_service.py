"""Background Companion Service for Aarushi AI.
Runs continuously independent of any open browser tab or UI session.
Enforces single-instance PID locking, records native OS timeline events & heartbeats,
evaluates digital wellbeing break reminders, and provides graceful start/stop/status control.
"""

from datetime import datetime, date
import json
import logging
import os
from pathlib import Path
import signal
import sys
import threading
import time
from typing import Dict, Any, Optional, Tuple

from gdr.system.timeline import get_timeline_tracker, ActivityTimelineTracker

logger = logging.getLogger("gdr.system.companion")

CONFIG_DIR = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr"))
PID_FILE = CONFIG_DIR / "companion.pid"
STATUS_FILE = CONFIG_DIR / "companion_status.json"


def _is_process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            STILL_ACTIVE = 259
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            exit_code = ctypes.c_ulong()
            ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
            ctypes.windll.kernel32.CloseHandle(handle)
            return exit_code.value == STILL_ACTIVE
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


class CompanionService:
    """Manages the background daemon lifecycle and health loop."""

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or CONFIG_DIR
        self.pid_file = self.config_dir / "companion.pid"
        self.status_file = self.config_dir / "companion_status.json"
        self._stop_event = threading.Event()
        self._loop_thread: Optional[threading.Thread] = None
        self.timeline: Optional[ActivityTimelineTracker] = None

    def get_status(self) -> Dict[str, Any]:
        """Check if companion service is currently running."""
        pid = None
        running = False
        if self.pid_file.exists():
            try:
                pid = int(self.pid_file.read_text().strip())
                running = _is_process_alive(pid)
            except Exception:
                running = False

        if not running and self.pid_file.exists():
            # Clean up stale pid
            try:
                self.pid_file.unlink(missing_ok=True)
            except Exception:
                pass

        last_hb = None
        if self.status_file.exists():
            try:
                with open(self.status_file, "r") as f:
                    data = json.load(f)
                    last_hb = data.get("last_heartbeat")
            except Exception:
                pass

        return {
            "running": running,
            "pid": pid if running else None,
            "pid_file": str(self.pid_file),
            "last_heartbeat": last_hb,
            "timestamp": datetime.now().isoformat()
        }

    def start(self, foreground: bool = False) -> bool:
        """Start the companion service. If already running, returns False."""
        status = self.get_status()
        if status["running"]:
            logger.info(f"Companion service is already running on PID {status['pid']}.")
            return False

        if foreground:
            self.run_loop()
            return True

        # Launch in background process
        import subprocess
        root = Path(__file__).resolve().parent.parent.parent
        venv_py = root / ".venv" / "bin" / "python"
        if not venv_py.exists():
            venv_py = root / ".venv" / "Scripts" / "python.exe"
        cmd_py = str(venv_py if venv_py.exists() else sys.executable)

        self.config_dir.mkdir(parents=True, exist_ok=True)
        log_file = open(self.config_dir / "companion.log", "a")

        proc = subprocess.Popen(
            [cmd_py, "-m", "gdr.system.companion_service", "run-fg"],
            cwd=str(root),
            stdout=log_file,
            stderr=log_file,
            start_new_session=True
        )
        logger.info(f"Launched background companion daemon with PID {proc.pid}.")
        return True

    def stop(self, timeout_sec: float = 5.0) -> bool:
        """Stop the running companion daemon gracefully."""
        status = self.get_status()
        if not status["running"] or not status["pid"]:
            logger.info("Companion service is not running.")
            return True

        pid = status["pid"]
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception as e:
            logger.warning(f"Failed to send SIGTERM to {pid}: {e}")

        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            if not _is_process_alive(pid):
                if self.pid_file.exists():
                    self.pid_file.unlink(missing_ok=True)
                return True
            time.sleep(0.2)

        # Force kill if still hanging
        try:
            sig_kill = getattr(signal, "SIGKILL", signal.SIGTERM)
            os.kill(pid, sig_kill)
        except Exception:
            pass
        if sys.platform == "win32":
            try:
                import subprocess
                subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
            except Exception:
                pass
        if self.pid_file.exists():
            self.pid_file.unlink(missing_ok=True)
        return True

    def run_loop(self):
        """Main service loop executed by daemon process."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        current_pid = os.getpid()

        # Check existing PID
        if self.pid_file.exists():
            try:
                old_pid = int(self.pid_file.read_text().strip())
                if old_pid != current_pid and _is_process_alive(old_pid):
                    print(f"Error: Another companion instance is already running (PID {old_pid}).")
                    sys.exit(1)
            except Exception:
                pass

        # Write current PID
        self.pid_file.write_text(str(current_pid))

        def _handle_signal(signum, frame):
            logger.info(f"Received stop signal ({signum}). Exiting companion service.")
            self._stop_event.set()

        signal.signal(signal.SIGTERM, _handle_signal)
        signal.signal(signal.SIGINT, _handle_signal)

        self.timeline = get_timeline_tracker()
        logger.info(f"Aarushi Companion Service running on PID {current_pid}.")

        try:
            while not self._stop_event.is_set():
                now_ts = time.time()
                now_iso = datetime.now().isoformat()

                # 1. Update activity timeline heartbeat
                self.timeline.heartbeat(active=True)

                # 2. Check Digital Wellbeing & Break Reminders
                try:
                    from gdr.system.wellbeing import get_wellbeing_manager
                    wb = get_wellbeing_manager()
                    wb.record_active_tick(interval_seconds=30)
                    reminder = wb.check_break_due()
                    if reminder:
                        logger.info(f"Digital Wellbeing Break Reminder: {reminder}")
                        self.timeline.record_break_reminder(spoken=False)
                except Exception as e:
                    logger.debug(f"Wellbeing check error: {e}")

                # 3. Update status file
                status_payload = {
                    "pid": current_pid,
                    "last_heartbeat": now_iso,
                    "uptime_seconds": time.time() - self.timeline._service_start_time,
                    "device": self.timeline.device_id
                }
                try:
                    with open(self.status_file, "w") as f:
                        json.dump(status_payload, f, indent=2)
                except Exception:
                    pass

                # Sleep 30 seconds or until stopped
                self._stop_event.wait(timeout=30.0)

        finally:
            if self.timeline:
                self.timeline.record_shutdown(clean=True)
            if self.pid_file.exists():
                try:
                    self.pid_file.unlink(missing_ok=True)
                except Exception:
                    pass
            logger.info("Aarushi Companion Service stopped cleanly.")


_GLOBAL_COMPANION_SERVICE: Optional[CompanionService] = None


def get_companion_service() -> CompanionService:
    global _GLOBAL_COMPANION_SERVICE
    if _GLOBAL_COMPANION_SERVICE is None:
        _GLOBAL_COMPANION_SERVICE = CompanionService()
    return _GLOBAL_COMPANION_SERVICE


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        svc = get_companion_service()
        if cmd == "start":
            res = svc.start(foreground=False)
            print("Companion service started." if res else "Already running.")
        elif cmd in ("run-fg", "foreground"):
            svc.run_loop()
        elif cmd == "stop":
            svc.stop()
            print("Companion service stopped.")
        elif cmd == "status":
            print(json.dumps(svc.get_status(), indent=2))
        elif cmd == "restart":
            svc.stop()
            time.sleep(1.0)
            svc.start(foreground=False)
            print("Companion service restarted.")
        else:
            print(f"Unknown command: {cmd}")
    else:
        print(json.dumps(get_companion_service().get_status(), indent=2))

