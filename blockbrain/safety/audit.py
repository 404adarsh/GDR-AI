"""Tamper-evident, append-only audit log for BlockBrain AI.
Logs all tool actions, arguments, permission tiers, and execution results with
cryptographic SHA-256 hash chaining (Merkle-style integrity).
Stored at ~/.config/blockbrain/audit.log with restricted 0o600 permissions.
"""

from datetime import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List

from blockbrain.safety.secrets import sanitize_text

logger = logging.getLogger("blockbrain.safety.audit")

AUDIT_DIR = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain"))
AUDIT_LOG_FILE = AUDIT_DIR / "audit.log"
GENESIS_HASH = "0" * 64


def _get_last_entry_hash() -> str:
    """Read the last entry's hash to link the cryptographic chain."""
    if not AUDIT_LOG_FILE.exists():
        return GENESIS_HASH
    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
            if not lines:
                return GENESIS_HASH
            last_entry = json.loads(lines[-1])
            return last_entry.get("entry_hash", GENESIS_HASH)
    except Exception:
        return GENESIS_HASH


def log_action(
    tool_name: str,
    args: Dict[str, Any],
    tier: str,
    status: str,
    message: str = "",
    undo_info: Optional[Dict[str, Any]] = None
):
    """Write an entry with SHA-256 hash chaining to the append-only audit log."""
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)

        # Sanitize arguments so secrets are never logged
        sanitized_args = {}
        for k, v in args.items():
            if isinstance(v, str):
                sanitized_args[k] = sanitize_text(v)
            else:
                sanitized_args[k] = v

        prev_hash = _get_last_entry_hash()

        payload = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "tier": tier,
            "status": status,
            "args": sanitized_args,
            "message": sanitize_text(message)[:500],
            "undo_info": undo_info or {},
            "prev_hash": prev_hash,
        }

        # Calculate cryptographic hash over previous hash + sorted payload content
        payload_bytes = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        entry_hash = hashlib.sha256(prev_hash.encode("utf-8") + payload_bytes).hexdigest()
        payload["entry_hash"] = entry_hash

        line = json.dumps(payload, ensure_ascii=False) + "\n"

        # Ensure file has strict 0o600 permissions
        file_exists = AUDIT_LOG_FILE.exists()
        with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)

        if not file_exists:
            try:
                os.chmod(AUDIT_LOG_FILE, 0o600)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Audit logging error: {e}")


def verify_audit_log_integrity() -> Tuple[bool, str]:
    """Verify cryptographic SHA-256 hash chain across all log entries.
    
    Returns (True, message) if valid, or (False, error) if tampering or truncation detected.
    """
    if not AUDIT_LOG_FILE.exists():
        return True, "Audit log does not exist yet (clean)."

    try:
        with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        if not lines:
            return True, "Audit log is empty."

        expected_prev = GENESIS_HASH
        for idx, line in enumerate(lines):
            try:
                entry = json.loads(line)
            except Exception as e:
                return False, f"Tampering/Corruption detected: Invalid JSON on line {idx + 1} ({e})"

            actual_prev = entry.get("prev_hash")
            actual_entry_hash = entry.get("entry_hash")

            if actual_prev != expected_prev:
                return False, (
                    f"Integrity broken at line {idx + 1}: prev_hash mismatch. "
                    f"Expected '{expected_prev[:12]}...', found '{actual_prev[:12] if actual_prev else 'None'}...'"
                )

            # Recompute hash without entry_hash
            payload_copy = dict(entry)
            payload_copy.pop("entry_hash", None)
            payload_bytes = json.dumps(payload_copy, sort_keys=True, ensure_ascii=False).encode("utf-8")
            recalculated = hashlib.sha256(expected_prev.encode("utf-8") + payload_bytes).hexdigest()

            if recalculated != actual_entry_hash:
                return False, (
                    f"Tampering detected at line {idx + 1}: hash mismatch. "
                    f"Payload was modified! Recalculated '{recalculated[:12]}...' vs stored '{actual_entry_hash[:12]}...'"
                )

            expected_prev = actual_entry_hash

        return True, f"Audit log verified: {len(lines)} entries intact with valid hash chain."
    except Exception as e:
        return False, f"Integrity check error: {e}"


def get_recent_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
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

