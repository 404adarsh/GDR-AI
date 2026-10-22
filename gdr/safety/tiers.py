"""Permission tiers for GDR AI.
- AUTO: read-only actions, file reading, research, draft creation.
- APPROVAL: sending emails/messages, deleting files, form submission, system modifications.
- NEVER: credential dumps, payment submissions, dangerous destructive root operations.
"""

from enum import Enum
from typing import Dict, Any, Optional
import os

class PermissionTier(str, Enum):
    AUTO = "AUTO"
    APPROVAL = "APPROVAL"
    NEVER = "NEVER"

# Explicit blocked commands for NEVER tier
_NEVER_PATTERNS = [
    "rm -rf /",
    "mkfs",
    ":(){ :|:& };:",
    "> /dev/sda",
    "dd if=",
    "chmod -R 777 /",
    "cat /etc/shadow",
    "userdel",
    "passwd root",
]


def classify_action(tool_name: str, args: Dict[str, Any], is_night_shift: bool = False) -> PermissionTier:
    """Classify an action into AUTO, APPROVAL, or NEVER tier."""
    name = tool_name.lower()

    # 1. Check for NEVER patterns
    if name in ("run_shell", "run_privileged", "run_sudo"):
        cmd = str(args.get("command", "")).strip()
        for pat in _NEVER_PATTERNS:
            if pat in cmd:
                return PermissionTier.NEVER

    # 2. Night Shift strictness
    if is_night_shift:
        # Overnight GDR must NEVER send emails/messages, submit forms, or purchase
        if "send" in name or "submit" in name or "buy" in name or "pay" in name:
            return PermissionTier.APPROVAL

    # 3. Sensitive tools that always require approval
    approval_tools = {
        "send_email",
        "delete_file",
        "browser_submit_form",
        "kill_process",
        "run_privileged",
        "run_sudo",
        "reboot_system",
        "shutdown_system",
        "send_telegram_message",
        "send_whatsapp_message",
        "browser_login",
    }

    if name in approval_tools:
        return PermissionTier.APPROVAL

    # 4. Check destructive args in shell
    if name == "run_shell":
        cmd = str(args.get("command", "")).lower()
        if any(w in cmd for w in ["rm ", "drop ", "truncate ", "kill -9", "shutdown", "reboot"]):
            return PermissionTier.APPROVAL

    return PermissionTier.AUTO

