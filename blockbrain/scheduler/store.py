"""Persistent SQLite job store for blockbrain AI scheduler.
Survives system reboots and preserves pending reminders, timers, and recurring routines.
"""

from datetime import datetime
import os
from pathlib import Path
import sqlite3
from typing import List, Dict, Any, Optional

DB_DIR = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain"))
DB_PATH = DB_DIR / "jobs.db"


class JobStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                prompt TEXT NOT NULL,
                schedule_type TEXT NOT NULL,     -- 'at', 'in', 'cron'
                schedule_expr TEXT NOT NULL,     -- timestamp or cron expression
                next_run_at TEXT NOT NULL,       -- ISO timestamp
                last_run_at TEXT,
                status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'completed', 'cancelled'
                is_reminder_only INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            );
            """)
            conn.commit()

    def add_job(
        self,
        description: str,
        prompt: str,
        schedule_type: str,
        schedule_expr: str,
        next_run_at: datetime,
        is_reminder_only: bool = True
    ) -> int:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO jobs (description, prompt, schedule_type, schedule_expr, next_run_at, status, is_reminder_only, created_at)
            VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)
            """, (
                description,
                prompt,
                schedule_type,
                schedule_expr,
                next_run_at.isoformat(),
                1 if is_reminder_only else 0,
                datetime.now().isoformat()
            ))
            conn.commit()
            return cur.lastrowid

    def get_due_jobs(self) -> List[Dict[str, Any]]:
        now_str = datetime.now().isoformat()
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            SELECT * FROM jobs
            WHERE status = 'pending' AND next_run_at <= ?
            ORDER BY next_run_at ASC
            """, (now_str,))
            return [dict(row) for row in cur.fetchall()]

    def list_jobs(self, include_completed: bool = False) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            if include_completed:
                cur.execute("SELECT * FROM jobs ORDER BY next_run_at ASC")
            else:
                cur.execute("SELECT * FROM jobs WHERE status = 'pending' ORDER BY next_run_at ASC")
            return [dict(row) for row in cur.fetchall()]

    def update_job_status(self, job_id: int, status: str, next_run_at: Optional[datetime] = None):
        with self._get_conn() as conn:
            if next_run_at:
                conn.execute("""
                UPDATE jobs
                SET status = ?, next_run_at = ?, last_run_at = ?
                WHERE id = ?
                """, (status, next_run_at.isoformat(), datetime.now().isoformat(), job_id))
            else:
                conn.execute("""
                UPDATE jobs
                SET status = ?, last_run_at = ?
                WHERE id = ?
                """, (status, datetime.now().isoformat(), job_id))
            conn.commit()

    def delete_job(self, job_id: int) -> bool:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
            conn.commit()
            return cur.rowcount > 0

    def snooze_job(self, job_id: int, minutes: int = 10) -> Optional[datetime]:
        from datetime import timedelta
        new_time = datetime.now() + timedelta(minutes=minutes)
        with self._get_conn() as conn:
            conn.execute("""
            UPDATE jobs
            SET status = 'pending', next_run_at = ?
            WHERE id = ?
            """, (new_time.isoformat(), job_id))
            conn.commit()
        return new_time


_JOB_STORE = None


def get_job_store() -> JobStore:
    global _JOB_STORE
    if _JOB_STORE is None:
        _JOB_STORE = JobStore()
    return _JOB_STORE

