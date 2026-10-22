"""Daily Digital Activity Timeline & OS Lifecycle Tracking for GDR AI.
Accurately records OS boots, service starts, sleep/wake cycles, active/idle time,
and session timelines using native operating-system signals with zero extra C-dependencies.
Differentiates genuine machine boots from application/service restarts.
"""

from datetime import datetime, date, timedelta
import json
import logging
import os
from pathlib import Path
import platform
import re
import sqlite3
import subprocess
import time
from typing import List, Dict, Any, Optional, Tuple

from gdr.tools.registry import tool

from gdr.config import get_gdr_config_dir

logger = logging.getLogger("gdr.system.timeline")


def _resolve_timeline_db(path: Optional[Path] = None) -> Path:
    if path:
        return path
    cfg_env = os.environ.get("GDR_CONFIG_DIR")
    if cfg_env:
        return Path(cfg_env) / "activity_timeline.db"
    target = get_gdr_config_dir() / "activity_timeline.db"
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        return target
    except Exception:
        alt = Path(__file__).resolve().parent.parent / "data" / "activity_timeline.db"
        alt.parent.mkdir(parents=True, exist_ok=True)
        return alt



def get_native_os_boot_time() -> Tuple[float, str]:
    """Determine native OS boot time using zero-dependency platform primitives."""
    system = platform.system().lower()
    now = time.time()

    # 1. Linux: /proc/uptime (uptime in seconds)
    if system == "linux" and os.path.exists("/proc/uptime"):
        try:
            with open("/proc/uptime", "r") as f:
                uptime_sec = float(f.read().split()[0])
            return (now - uptime_sec, "proc_uptime")
        except Exception:
            pass

    # 2. macOS / Darwin: sysctl -n kern.boottime
    if system == "darwin":
        try:
            out = subprocess.check_output(["sysctl", "-n", "kern.boottime"], text=True).strip()
            # format: { sec = 1729410968, usec = ... }
            m = re.search(r"sec\s*=\s*(\d+)", out)
            if m:
                return (float(m.group(1)), "sysctl_boottime")
        except Exception:
            pass

    # 3. Windows: GetTickCount64 via ctypes
    if system == "windows":
        try:
            import ctypes
            tick_ms = ctypes.windll.kernel32.GetTickCount64()
            return (now - (tick_ms / 1000.0), "windows_tickcount64")
        except Exception:
            pass

    # 4. Fallback command-line 'uptime -s' or 'who -b'
    try:
        out = subprocess.check_output(["uptime", "-s"], text=True, stderr=subprocess.DEVNULL).strip()
        dt = datetime.strptime(out, "%Y-%m-%d %H:%M:%S")
        return (dt.timestamp(), "uptime_command")
    except Exception:
        pass

    return (now, "fallback_now")


class ActivityTimelineTracker:
    """Tracks OS lifecycle, application sessions, user activity, and digital wellbeing events."""

    def __init__(self, db_path: Optional[Path] = None, device_id: Optional[str] = None):
        self.db_path = _resolve_timeline_db(db_path)
        self.device_id = device_id or platform.node() or "local_machine"
        self._service_start_time = time.time()
        self._init_db()
        self._init_lifecycle()

    def _get_conn(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS timeline_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    boot_session_id TEXT NOT NULL,
                    service_session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    iso_time TEXT NOT NULL,
                    date_str TEXT NOT NULL,
                    reliability TEXT DEFAULT 'measured',
                    details_json TEXT
                );
                """)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS boot_sessions (
                    boot_session_id TEXT PRIMARY KEY,
                    os_boot_time REAL NOT NULL,
                    device_id TEXT NOT NULL,
                    first_detected REAL NOT NULL,
                    last_heartbeat REAL,
                    clean_shutdown INTEGER DEFAULT 0
                );
                """)
                conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    date_str TEXT PRIMARY KEY,
                    boot_count INTEGER DEFAULT 0,
                    total_active_seconds REAL DEFAULT 0.0,
                    total_idle_seconds REAL DEFAULT 0.0,
                    service_uptime_seconds REAL DEFAULT 0.0,
                    ide_active_seconds REAL DEFAULT 0.0,
                    breaks_taken INTEGER DEFAULT 0,
                    projects_json TEXT,
                    summary_text TEXT,
                    updated_at TEXT
                );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tl_date ON timeline_events(date_str);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tl_boot ON timeline_events(boot_session_id);")
                conn.commit()
        except Exception as e:
            logger.error(f"Error initializing timeline DB: {e}")

    def _init_lifecycle(self):
        """Differentiate genuine OS boot from companion service / application restart."""
        boot_ts, source = get_native_os_boot_time()
        # Round to integer second for reliable matching across re-queries
        self.current_boot_id = f"boot_{int(boot_ts)}_{self.device_id}"
        self.service_session_id = f"svc_{int(self._service_start_time)}_{os.getpid()}"

        try:
            with self._get_conn() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM boot_sessions WHERE boot_session_id = ?", (self.current_boot_id,))
                existing_session = cur.fetchone()

                today_str = date.today().isoformat()
                now_str = datetime.now().isoformat()

                if not existing_session:
                    # Check if there was an earlier session that died without clean shutdown
                    cur.execute("SELECT * FROM boot_sessions ORDER BY first_detected DESC LIMIT 1")
                    last_session = cur.fetchone()
                    if last_session and not last_session["clean_shutdown"]:
                        last_hb = last_session["last_heartbeat"] or last_session["first_detected"]
                        inferred_iso = datetime.fromtimestamp(last_hb).isoformat()
                        conn.execute("""
                        INSERT INTO timeline_events (boot_session_id, service_session_id, event_type, timestamp, iso_time, date_str, reliability, details_json)
                        VALUES (?, ?, 'os_shutdown', ?, ?, ?, 'inferred', ?)
                        """, (
                            last_session["boot_session_id"],
                            "inferred_prev",
                            last_hb,
                            inferred_iso,
                            datetime.fromtimestamp(last_hb).strftime("%Y-%m-%d"),
                            json.dumps({"reason": "power_loss_or_restart_inferred", "last_heartbeat": last_hb})
                        ))

                    # This is a TRUE new OS boot event!
                    boot_iso = datetime.fromtimestamp(boot_ts).isoformat()
                    boot_date = datetime.fromtimestamp(boot_ts).strftime("%Y-%m-%d")

                    conn.execute("""
                    INSERT INTO boot_sessions (boot_session_id, os_boot_time, device_id, first_detected, last_heartbeat, clean_shutdown)
                    VALUES (?, ?, ?, ?, ?, 0)
                    """, (self.current_boot_id, boot_ts, self.device_id, time.time(), time.time()))

                    conn.execute("""
                    INSERT INTO timeline_events (boot_session_id, service_session_id, event_type, timestamp, iso_time, date_str, reliability, details_json)
                    VALUES (?, ?, 'os_boot', ?, ?, ?, 'measured', ?)
                    """, (
                        self.current_boot_id,
                        self.service_session_id,
                        boot_ts,
                        boot_iso,
                        today_str,
                        json.dumps({"source": source, "boot_time": boot_iso, "boot_date": boot_date, "device": self.device_id})
                    ))

                    # Increment daily boot count (recorded for boot_date and today)
                    for d_str in set([boot_date, today_str]):
                        conn.execute("""
                        INSERT INTO daily_summaries (date_str, boot_count, updated_at)
                        VALUES (?, 1, ?)
                        ON CONFLICT(date_str) DO UPDATE SET
                            boot_count = boot_count + 1,
                            updated_at = excluded.updated_at
                        """, (d_str, now_str))

                    # Also log Aarushi service start
                    conn.execute("""
                    INSERT INTO timeline_events (boot_session_id, service_session_id, event_type, timestamp, iso_time, date_str, reliability, details_json)
                    VALUES (?, ?, 'service_start', ?, ?, ?, 'measured', ?)
                    """, (
                        self.current_boot_id,
                        self.service_session_id,
                        self._service_start_time,
                        now_str,
                        today_str,
                        json.dumps({"service": "Aarushi Companion", "pid": os.getpid()})
                    ))
                else:
                    # Same boot session ID: this is a SERVICE RESTART or APP START, NOT an OS boot!
                    conn.execute("""
                    INSERT INTO timeline_events (boot_session_id, service_session_id, event_type, timestamp, iso_time, date_str, reliability, details_json)
                    VALUES (?, ?, 'service_restart', ?, ?, ?, 'measured', ?)
                    """, (
                        self.current_boot_id,
                        self.service_session_id,
                        self._service_start_time,
                        now_str,
                        today_str,
                        json.dumps({"service": "Aarushi Companion", "pid": os.getpid(), "note": "Service restarted; OS remained running"})
                    ))

                conn.commit()
        except Exception as e:
            logger.error(f"Error in lifecycle initialization: {e}")

    def record_event(
        self,
        event_type: str,
        details: Optional[Dict[str, Any]] = None,
        reliability: str = "measured",
        timestamp: Optional[float] = None
    ) -> int:
        """Record an activity event in the timeline."""
        ts = timestamp or time.time()
        iso = datetime.fromtimestamp(ts).isoformat()
        date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        details_str = json.dumps(details or {})

        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO timeline_events (boot_session_id, service_session_id, event_type, timestamp, iso_time, date_str, reliability, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (self.current_boot_id, self.service_session_id, event_type, ts, iso, date_str, reliability, details_str))
            event_id = cur.lastrowid or 0
            conn.commit()
            return event_id

    def heartbeat(self, active: bool = True, project: Optional[str] = None):
        """Update heartbeat timestamp and session statistics."""
        now = time.time()
        today_str = date.today().isoformat()
        now_str = datetime.now().isoformat()

        try:
            with self._get_conn() as conn:
                conn.execute("""
                UPDATE boot_sessions SET last_heartbeat = ? WHERE boot_session_id = ?
                """, (now, self.current_boot_id))

                # Update daily stats (assuming ~60s heartbeat window)
                active_inc = 60.0 if active else 0.0
                idle_inc = 0.0 if active else 60.0

                conn.execute("""
                INSERT INTO daily_summaries (date_str, total_active_seconds, total_idle_seconds, service_uptime_seconds, updated_at)
                VALUES (?, ?, ?, 60.0, ?)
                ON CONFLICT(date_str) DO UPDATE SET
                    total_active_seconds = total_active_seconds + excluded.total_active_seconds,
                    total_idle_seconds = total_idle_seconds + excluded.total_idle_seconds,
                    service_uptime_seconds = service_uptime_seconds + 60.0,
                    updated_at = excluded.updated_at
                """, (today_str, active_inc, idle_inc, now_str))

                if project:
                    # Track project touch
                    cur = conn.cursor()
                    cur.execute("SELECT projects_json FROM daily_summaries WHERE date_str = ?", (today_str,))
                    row = cur.fetchone()
                    projs = []
                    if row and row["projects_json"]:
                        try:
                            projs = json.loads(row["projects_json"])
                        except Exception:
                            projs = []
                    if project not in projs:
                        projs.append(project)
                        conn.execute("UPDATE daily_summaries SET projects_json = ? WHERE date_str = ?", (json.dumps(projs), today_str))

                conn.commit()
        except Exception as e:
            logger.error(f"Error updating heartbeat: {e}")

    def record_user_activity(self, activity_type: str = "coding_session", project: Optional[str] = None):
        """Record an explicit work or coding session."""
        self.record_event(activity_type, details={"project": project, "active": True})
        self.heartbeat(active=True, project=project)

    def record_break_reminder(self, spoken: bool = False):
        """Record that a break reminder was displayed or spoken."""
        self.record_event("break_reminder", details={"spoken": spoken})

    def record_break_taken(self, duration_minutes: int = 5):
        """Record user taking a restful break."""
        today_str = date.today().isoformat()
        self.record_event("break_taken", details={"duration_minutes": duration_minutes})
        try:
            with self._get_conn() as conn:
                conn.execute("""
                UPDATE daily_summaries SET breaks_taken = breaks_taken + 1 WHERE date_str = ?
                """, (today_str,))
                conn.commit()
        except Exception:
            pass

    def record_sleep(self):
        """Record system sleep event."""
        self.record_event("sleep", details={"status": "entered_sleep"})

    def record_wake(self):
        """Record system wake event."""
        self.record_event("wake", details={"status": "woke_up"})

    def record_shutdown(self, clean: bool = True):
        """Record clean shutdown."""
        now = time.time()
        self.record_event("service_stop", details={"clean": clean})
        try:
            with self._get_conn() as conn:
                conn.execute("""
                UPDATE boot_sessions SET clean_shutdown = ? WHERE boot_session_id = ?
                """, (1 if clean else 0, self.current_boot_id))
                conn.commit()
        except Exception:
            pass

    def get_events(self, date_str: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve timeline events for a date."""
        target_date = date_str or date.today().isoformat()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT * FROM timeline_events WHERE date_str = ? ORDER BY timestamp ASC LIMIT ?
            """, (target_date, limit))
            return [dict(r) for r in cur.fetchall()]

    def get_daily_stats(self, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Get summarized daily statistics."""
        target_date = date_str or date.today().isoformat()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM daily_summaries WHERE date_str = ?", (target_date,))
            row = cur.fetchone()
            if row:
                d = dict(row)
                if d.get("projects_json"):
                    try:
                        d["projects"] = json.loads(d["projects_json"])
                    except Exception:
                        d["projects"] = []
                else:
                    d["projects"] = []
                return d
            return {
                "date_str": target_date,
                "boot_count": 0,
                "total_active_seconds": 0.0,
                "total_idle_seconds": 0.0,
                "service_uptime_seconds": 0.0,
                "breaks_taken": 0,
                "projects": []
            }

    def format_readable_timeline(self, date_str: Optional[str] = None) -> List[str]:
        """Format timeline events into human-readable lines as requested in prompt."""
        events = self.get_events(date_str)
        readable = []
        name_map = {
            "os_boot": "Computer boot detected",
            "service_start": "Aarushi started",
            "service_restart": "Aarushi restarted",
            "app_start": "GDR-IDE opened",
            "coding_session": "Coding session active",
            "break_reminder": "Break reminder displayed",
            "break_taken": "Break taken",
            "sleep": "Computer entered sleep",
            "wake": "Computer woke up",
            "service_stop": "Aarushi stopped",
            "os_shutdown": "Computer shutdown",
            "user_active": "Activity recorded"
        }

        for ev in events:
            try:
                dt = datetime.fromtimestamp(ev["timestamp"])
                time_part = dt.strftime("%H:%M")
                label = name_map.get(ev["event_type"], ev["event_type"].replace("_", " ").capitalize())
                readable.append(f"{time_part} — {label}")
            except Exception:
                continue

        return readable

    def answer_activity_query(self, query: str) -> str:
        """Answer natural language questions about startup, running time, shutdowns, and projects."""
        low = query.lower().strip()
        stats = self.get_daily_stats()
        today_events = self.get_events()

        boot_events = [e for e in today_events if e["event_type"] == "os_boot"]
        shutdown_events = [e for e in today_events if e["event_type"] in ("os_shutdown", "service_stop")]

        # 1. When did I turn on my PC today?
        if any(k in low for k in ["turn on", "started my pc", "booted", "turn on my pc", "pc turn on", "computer start"]):
            if boot_events:
                first_boot = boot_events[0]
                dt = datetime.fromtimestamp(first_boot["timestamp"])
                return f"You turned on your PC today at {dt.strftime('%I:%M %p')}."
            boot_ts, _ = get_native_os_boot_time()
            dt = datetime.fromtimestamp(boot_ts)
            return f"Your PC was booted at {dt.strftime('%I:%M %p')} today."

        # 2. How many times did I start my computer today?
        if any(k in low for k in ["how many times", "times did i start", "boot count"]):
            count = stats.get("boot_count", len(boot_events))
            if count == 0:
                count = 1  # current running session
            return f"Your computer was started {count} time{'s' if count != 1 else ''} today."

        # 3. How long has my PC been running? / Uptime
        if any(k in low for k in ["how long", "running", "uptime", "up time"]):
            boot_ts, _ = get_native_os_boot_time()
            uptime_seconds = max(0, time.time() - boot_ts)
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            if hours > 0:
                return f"Your PC has been running for approximately {hours} hour{'s' if hours != 1 else ''} and {minutes} minute{'s' if minutes != 1 else ''}."
            return f"Your PC has been running for approximately {minutes} minute{'s' if minutes != 1 else ''}."

        # 4. When did I shut it down?
        if any(k in low for k in ["shut it down", "shutdown", "turn off", "shut down"]):
            if shutdown_events:
                last_sd = shutdown_events[-1]
                dt = datetime.fromtimestamp(last_sd["timestamp"])
                rel = f" (inferred from last heartbeat)" if last_sd.get("reliability") == "inferred" else ""
                return f"Last recorded shutdown was at {dt.strftime('%I:%M %p')}{rel}."
            return "No computer shutdown has been recorded so far today; the machine is currently active."

        # 5. Time spent in GDR-IDE or active time
        if any(k in low for k in ["time did i spend", "screen time", "active time", "hours spent"]):
            active_sec = stats.get("total_active_seconds", 0.0)
            hours = int(active_sec // 3600)
            minutes = int((active_sec % 3600) // 60)
            return f"You have spent approximately {hours}h {minutes}m of active time today."

        # 6. Projects worked on today
        if any(k in low for k in ["projects", "what did i work on", "work on today"]):
            projs = stats.get("projects", [])
            if projs:
                return f"Projects you worked on today: {', '.join(projs)}."
            return "No specific projects have been logged yet today."

        # Default summary
        readable = self.format_readable_timeline()
        if readable:
            return "Here is your activity timeline for today:\n" + "\n".join(readable[-10:])
        return "Timeline tracking is active. No major lifecycle events recorded yet today."


_GLOBAL_TIMELINE_TRACKER: Optional[ActivityTimelineTracker] = None


def get_timeline_tracker() -> ActivityTimelineTracker:
    global _GLOBAL_TIMELINE_TRACKER
    if _GLOBAL_TIMELINE_TRACKER is None:
        _GLOBAL_TIMELINE_TRACKER = ActivityTimelineTracker()
    return _GLOBAL_TIMELINE_TRACKER


# ==============================================================================
# LLM Accessible Tool
# ==============================================================================

@tool(name="query_activity_timeline", category="system", tier="AUTO")
def query_activity_timeline_tool(question: str) -> str:
    """Answer questions about computer boot time, uptime, shutdowns, active time, or daily activity timeline."""
    tracker = get_timeline_tracker()
    return tracker.answer_activity_query(question)

