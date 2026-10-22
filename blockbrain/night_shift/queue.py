"""Night Shift task queue and execution engine for blockbrain AI.
Runs background tasks overnight with strict permission tiers (AUTO, APPROVAL, NEVER),
step budgets, retries, and morning summary reports.
"""

from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
from typing import List, Dict, Any, Optional

DB_DIR = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain"))
NIGHT_DB_PATH = DB_DIR / "night_shift.db"
APPROVALS_FILE = DB_DIR / "approval_queue.json"


class NightShiftStore:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or NIGHT_DB_PATH
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS night_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal TEXT NOT NULL,
                deadline TEXT,
                tier TEXT NOT NULL DEFAULT 'AUTO',
                step_budget INTEGER NOT NULL DEFAULT 50,
                retries_left INTEGER NOT NULL DEFAULT 3,
                status TEXT NOT NULL DEFAULT 'pending',
                report TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );
            """)
            conn.commit()

    def add_task(self, goal: str, deadline: str = "07:00", tier: str = "AUTO", step_budget: int = 50) -> int:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
            INSERT INTO night_tasks (goal, deadline, tier, step_budget, retries_left, status, created_at)
            VALUES (?, ?, ?, ?, 3, 'pending', ?)
            """, (goal, deadline, tier, step_budget, datetime.now().isoformat()))
            conn.commit()
            return cur.lastrowid

    def list_tasks(self) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM night_tasks ORDER BY id DESC")
            return [dict(r) for r in cur.fetchall()]

    def update_task(self, task_id: int, status: str, report: str = ""):
        with self._get_conn() as conn:
            conn.execute("""
            UPDATE night_tasks
            SET status = ?, report = ?, completed_at = ?
            WHERE id = ?
            """, (status, report, datetime.now().isoformat(), task_id))
            conn.commit()


def queue_for_approval(tool_name: str, args: Dict[str, Any], reason: str = "") -> str:
    """Store an action requiring morning approval."""
    APPROVALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    items = []
    if APPROVALS_FILE.exists():
        try:
            with open(APPROVALS_FILE, "r") as f:
                items = json.load(f)
        except Exception:
            items = []

    item_id = f"appr_{len(items)+1}_{int(datetime.now().timestamp())}"
    items.append({
        "id": item_id,
        "tool": tool_name,
        "args": args,
        "reason": reason,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    })

    with open(APPROVALS_FILE, "w") as f:
        json.dump(items, f, indent=2)

    return item_id


def list_pending_approvals() -> List[Dict[str, Any]]:
    if not APPROVALS_FILE.exists():
        return []
    try:
        with open(APPROVALS_FILE, "r") as f:
            items = json.load(f)
        return [i for i in items if i.get("status") == "pending"]
    except Exception:
        return []


def resolve_approval(item_id: str, approved: bool) -> bool:
    if not APPROVALS_FILE.exists():
        return False
    try:
        with open(APPROVALS_FILE, "r") as f:
            items = json.load(f)

        target = None
        for i in items:
            if i.get("id") == item_id and i.get("status") == "pending":
                i["status"] = "approved" if approved else "denied"
                target = i
                break

        if not target:
            return False

        with open(APPROVALS_FILE, "w") as f:
            json.dump(items, f, indent=2)

        if approved:
            # Execute approved action
            from blockbrain.tools.registry import execute_tool
            execute_tool(target["tool"], **target["args"])

        return True
    except Exception as e:
        print(f"⚠️ Resolve approval error: {e}")
        return False

