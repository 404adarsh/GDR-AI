"""Process lifecycle and data-preserving management for GDR AI / GDR-IDE.
Handles graceful process stop/restart, PID tracking, and safe scoped resets
with automated backups.
"""

from datetime import datetime
import json
import logging
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
from typing import Dict, Any, List, Optional

from gdr.config import get_gdr_config_dir, load_config, save_config, DEFAULT_CONFIG

logger = logging.getLogger("gdr.system.lifecycle")

PID_FILE = get_gdr_config_dir() / "gdr_gui.pid"


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if the given port is actively bound."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.3)
    try:
        in_use = (sock.connect_ex((host, port)) == 0)
        return in_use
    finally:
        sock.close()


def find_pids_on_port(port: int) -> List[int]:
    """Find all process IDs bound to the specified TCP port."""
    pids: List[int] = []

    # 1. Windows netstat
    if sys.platform == "win32":
        try:
            res = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True)
            for line in res.stdout.splitlines():
                if f":{port}" in line and "LISTENING" in line:
                    parts = line.strip().split()
                    if parts and parts[-1].isdigit():
                        pids.append(int(parts[-1]))
        except Exception:
            pass

    # 2. Try lsof
    if not pids:
        try:
            res = subprocess.run(["lsof", "-t", "-i", f":{port}"], capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                for line in res.stdout.strip().splitlines():
                    line = line.strip()
                    if line.isdigit():
                        pids.append(int(line))
        except Exception:
            pass

    # 3. Try fuser without -k
    if not pids:
        try:
            res = subprocess.run(["fuser", f"{port}/tcp"], capture_output=True, text=True)
            output = (res.stdout + " " + res.stderr).strip()
            for token in output.split():
                clean = "".join(c for c in token if c.isdigit())
                if clean:
                    pids.append(int(clean))
        except Exception:
            pass

    # 4. Try reading pid file
    if not pids and PID_FILE.exists():
        try:
            txt = PID_FILE.read_text().strip()
            if txt.isdigit():
                pids.append(int(txt))
        except Exception:
            pass

    # Remove self PID and duplicates
    my_pid = os.getpid()
    return sorted(list(set(p for p in pids if p != my_pid)))


def record_gui_pid(pid: Optional[int] = None) -> None:
    """Store active GUI PID to pid file."""
    try:
        pid = pid or os.getpid()
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(pid))
    except Exception as e:
        logger.debug(f"Could not record GUI PID: {e}")


def clear_gui_pid() -> None:
    """Remove active GUI PID file."""
    try:
        if PID_FILE.exists():
            PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def graceful_restart_gui(port: int = 8844, timeout_seconds: float = 4.0) -> bool:
    """Gracefully stop any existing process listening on port, allowing SQLite WAL to flush.
    NEVER deletes or modifies persistent data or configuration.
    """
    pids = find_pids_on_port(port)
    if not pids:
        return True

    logger.info(f"Gracefully terminating existing GDR-IDE process(es) {pids} on port {port}...")
    print(f"🔄 Gracefully stopping existing GDR-IDE process (PID: {pids}) on port {port}...")

    # Step 1: Send SIGTERM to allow graceful shutdown and WAL checkpointing
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except Exception as e:
            logger.debug(f"Error sending SIGTERM to {pid}: {e}")

    # Step 2: Poll port and processes until released
    start_time = time.time()
    while time.time() - start_time < timeout_seconds:
        if not is_port_in_use(port):
            clear_gui_pid()
            time.sleep(0.5)
            print("✅ Previous process terminated cleanly. Port 8844 is now free.")
            return True
        time.sleep(0.2)

    # Step 3: If still occupying port, escalate to SIGKILL / taskkill
    remaining = find_pids_on_port(port)
    if remaining:
        print(f"⚠️ Process did not exit within {timeout_seconds}s. Escalating to SIGKILL for {remaining}...")
        for pid in remaining:
            try:
                sig_kill = getattr(signal, "SIGKILL", signal.SIGTERM)
                os.kill(pid, sig_kill)
            except Exception:
                pass
            if sys.platform == "win32":
                try:
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                except Exception:
                    pass
        time.sleep(0.5)

    clear_gui_pid()
    return not is_port_in_use(port)


def create_scoped_backup(scope: str = "all") -> Optional[Path]:
    """Create a timestamped backup directory in ~/.config/gdr/backups/."""
    try:
        cfg_dir = get_gdr_config_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = cfg_dir / "backups" / f"backup_{scope}_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        copied = 0
        for fname in ["config.toml", "memory.db", "contacts.db", "activity_timeline.db", "jobs.db", "secrets.env"]:
            src = cfg_dir / fname
            if src.exists():
                dst = backup_dir / fname
                shutil.copy2(src, dst)
                copied += 1

        logger.info(f"Created safety backup at {backup_dir} ({copied} files)")
        return backup_dir
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return None


def safe_reset_application_data(
    scope: str = "all",
    confirmation: Optional[str] = None,
    interactive: bool = True
) -> Dict[str, Any]:
    """Safely reset application data with explicit confirmation and automatic backup.
    Scope options: 'conversations', 'memories', 'preferences', 'all'.
    Requires typed string 'RESET'.
    """
    valid_scopes = ("conversations", "memories", "preferences", "all")
    if scope not in valid_scopes:
        return {
            "success": False,
            "error": f"Invalid scope '{scope}'. Allowed: {', '.join(valid_scopes)}"
        }

    # Explicit confirmation check
    if confirmation != "RESET":
        if not interactive:
            return {
                "success": False,
                "error": "Confirmation required: pass --confirm RESET to confirm reset non-interactively."
            }

        scope_desc = {
            "conversations": "chat and voice conversation history",
            "memories": "all learned long-term memories, facts, and profile entries",
            "preferences": "user preferences and custom configuration in config.toml",
            "all": "all conversation history, memories, and user preferences (tokens & secrets preserved in backup)"
        }.get(scope, scope)

        print("\n" + "=" * 60)
        print("⚠️  [SAFETY WARNING] GDR-IDE DATA RESET")
        print("=" * 60)
        print(f"You have requested to reset: {scope.upper()} ({scope_desc}).")
        print("An automatic backup will be created before any changes.")
        print("To proceed with this reset, type RESET and press Enter.")
        print("To abort, press Enter or Ctrl+C.")
        print("-" * 60)

        try:
            user_input = input("Confirmation: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n❌ Reset aborted by user. No data was changed.")
            return {"success": False, "aborted": True}

        if user_input != "RESET":
            print("❌ Confirmation mismatch. Reset cancelled. No data was changed.")
            return {"success": False, "aborted": True}

    # Step 1: Create automated backup before any modification
    backup_path = create_scoped_backup(scope=scope)
    print(f"📦 Safety backup created at: {backup_path}")

    cfg_dir = get_gdr_config_dir()
    actions_taken = []

    # Step 2: Perform scoped reset
    from gdr.memory.store import get_memory_store
    store = get_memory_store()

    if scope in ("conversations", "all"):
        count = store.clear_chat_history()
        actions_taken.append(f"Cleared {count} conversation history messages")

    if scope in ("memories", "all"):
        try:
            with store._get_conn() as conn:
                conn.execute("DELETE FROM memories;")
                conn.commit()
            actions_taken.append("Cleared long-term memory store")
        except Exception as e:
            actions_taken.append(f"Memory clear error: {e}")

    if scope in ("preferences", "all"):
        try:
            save_config(DEFAULT_CONFIG)
            actions_taken.append("Reset config.toml to factory defaults")
        except Exception as e:
            actions_taken.append(f"Config reset error: {e}")

    print("✅ Reset completed successfully.")
    for act in actions_taken:
        print(f"   • {act}")
    print(f"💡 Your previous data is preserved in: {backup_path}\n")

    return {
        "success": True,
        "scope": scope,
        "backup_path": str(backup_path) if backup_path else None,
        "actions": actions_taken
    }
