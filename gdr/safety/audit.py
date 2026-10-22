"""Append-only audit log for GDR AI.
Logs all tool actions, arguments, permission tiers, and execution results.
Stored at ~/.config/gdr/audit.log.
"""

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from gdr.safety.secrets import sanitize_text

AUDIT_DIR = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr"))
AUDIT_LOG_FILE = AUDIT_DIR / "audit.log"


def log_action(
    tool_name: str,
    args: Dict[str, Any],
    tier: str,
    status: str,
    message: str = "",
    undo_info: Optional[Dict[str, Any]] = None
):
    """Write an entry to the append-only audit log."""
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)

        # Sanitize arguments so secrets are never logged
        sanitized_args = {}
        for k, v in args.items():
            if isinstance(v, str):
                sanitized_args[k] = sanitize_text(v)
            else:
                sanitized_args[k] = v

        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "tier": tier,
            "status": status,
            "args": sanitized_args,
            "message": sanitize_text(message)[:500],
            "undo_info": undo_info or {},
        }

        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"⚠️ Audit logging error: {e}")


def get_recent_audit_logs(limit: int = 50) -> list:
    """Return the most recent audit log entries."""
    if not AUDIT_LOG_FILE.exists():
        return []
    try:
        entries = []
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
        return entries[-limit:]
    except Exception:
        return []


def log_audit_event(action: str, target: str, details: str, tier: str = "AUTO"):
    """Convenience helper to record an audit entry."""
    log_action(action, {"target": target}, tier, "EXECUTED", details)

