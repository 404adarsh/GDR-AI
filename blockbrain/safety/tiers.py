"""Permission tiers, Granular Security Modes, and Unified Terminal Approval Gate for BlockBrain AI.

Permission Modes (Section 10):
- READ_ONLY: Observation tools only (screen reflection, file reads, system diagnostics). All writes/execs blocked.
- LIMITED: Harmless reads/searches auto-approved; file writes, terminal, and external actions require approval.
- TRUSTED: Routine desktop actions auto-approved; terminal and destructive operations ALWAYS require approval.

Terminal Security Gate (Section 9):
- Un-truncated command inspection
- Allow Once, Allow Always (exact-match whitelist), and Deny options
- High-visibility hazard detection for dangerous commands (RCE, shutdown, disk wipe, iptables, crontab, rm -rf, etc.)
- Zero self-approval enforcement via cryptographic UI nonce
- Ephemeral single-use execution_token for safe execution without re-blocking
- Panic Kill immediate cancellation
"""

from enum import Enum
import hmac
import json
import logging
import os
from pathlib import Path
import re
import secrets
import time
from typing import Dict, Any, List, Optional, Tuple, Union
import uuid

from blockbrain.safety.audit import log_action

logger = logging.getLogger("blockbrain.safety.tiers")

CONFIG_DIR = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain"))
PERMISSIONS_FILE = CONFIG_DIR / "permissions.json"


class PermissionTier(str, Enum):
    AUTO = "AUTO"
    APPROVAL = "APPROVAL"
    NEVER = "NEVER"


class PermissionMode(str, Enum):
    READ_ONLY = "READ_ONLY"
    LIMITED = "LIMITED"
    TRUSTED = "TRUSTED"


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

# Comprehensive Dangerous command patterns (Section 9 & Amendment 2)
# Evaluated with regex so flags, spacing, and pipe variations cannot bypass detection.
_DANGEROUS_PATTERNS: List[Tuple[str, str]] = [
    # 1. Remote Code Execution (RCE)
    (r"(curl|wget)\b.*?\|\s*(sudo\s+)?(ba|z)?sh\b", "Remote code execution piped directly to shell"),
    (r"(curl|wget)\b.*?\|\s*(sudo\s+)?python[0-9.]*\b", "Remote code execution piped to python runtime"),
    # 2. System Halt / Reboot
    (r"\b(shutdown|reboot|poweroff|init\s+[06])\b", "System shutdown or reboot command"),
    (r"\bsystemctl\s+(poweroff|reboot|halt)\b", "Systemd power state alteration"),
    # 3. Direct Disk & Filesystem Destruction
    (r">\s*/dev/(sd[a-z]|nvme[0-9]|vd[a-z])", "Direct block device overwrite"),
    (r"dd\b.*?\bof=/dev/(sd[a-z]|nvme[0-9]|vd[a-z])", "Raw disk block overwrite via dd"),
    (r"\b(mkfs|format|wipefs|parted|fdisk|gdisk)\b", "Filesystem formatting or partition destruction"),
    # 4. User & Account Tampering
    (r"\bcrontab\s+-r\b", "Destructive crontab removal"),
    (r"\b(userdel|groupdel)\b", "User or group deletion"),
    (r"\bpasswd(\s+root|\s+-d)?\b", "Root or system password modification"),
    # 5. Network & Firewall Disabling
    (r"\b(iptables|ip6tables)\s+-F\b", "Firewall rules flush"),
    (r"\bufw\s+disable\b", "Host firewall deactivation"),
    (r"\bnft\s+flush\b", "Nftables rules flush"),
    # 6. Deletion, Superuser & Git Rewriting
    (r"\brm\s+-(rf?|fr?)\b", "Recursive unrecoverable file deletion"),
    (r"\bsudo\b", "Privileged superuser execution"),
    (r"\bkill\s+-9\b", "Forced ungraceful process termination"),
    (r"\bkillall\b", "Mass process termination"),
    (r"\bgit\s+push\b.*?(-f\b|--force\b)", "Remote git history overwrite"),
    (r"\bgit\s+reset\s+--hard\b", "Local uncommitted work deletion"),
    (r"\bchmod\s+(-R\s+)?777\b", "Insecure global permission assignment"),
]

# In-memory runtime state
_CURRENT_MODE = PermissionMode.LIMITED
_TOOL_TOGGLES: Dict[str, bool] = {
    "filesystem": True,
    "terminal": True,
    "github": False,
    "browser": False,
    "google_workspace": False,
    "n8n": False,
}
# Strict exact commands permitted in Allow Always (Amendment 3)
_ALLOW_ALWAYS_COMMANDS: List[str] = [
    "ls",
    "pwd",
    "git status",
    "git diff",
    "git branch",
    "python3 --version",
    "cargo --version",
    "echo",
]
_PENDING_TERMINAL_APPROVALS: Dict[str, Dict[str, Any]] = {}


def _save_persisted_permissions() -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "mode": _CURRENT_MODE.value,
            "tool_toggles": _TOOL_TOGGLES,
            "allow_always": _ALLOW_ALWAYS_COMMANDS,
        }
        with open(PERMISSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.warning(f"Failed to persist permissions: {e}")


def _load_persisted_permissions() -> None:
    global _CURRENT_MODE, _TOOL_TOGGLES, _ALLOW_ALWAYS_COMMANDS
    if not PERMISSIONS_FILE.exists():
        return
    try:
        with open(PERMISSIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            mode_val = data.get("mode", "LIMITED")
            _CURRENT_MODE = PermissionMode(mode_val) if mode_val in PermissionMode._value2member_map_ else PermissionMode.LIMITED
            if "tool_toggles" in data and isinstance(data["tool_toggles"], dict):
                _TOOL_TOGGLES.update(data["tool_toggles"])
            if "allow_always" in data and isinstance(data["allow_always"], list):
                _ALLOW_ALWAYS_COMMANDS = data["allow_always"]
    except Exception as e:
        logger.warning(f"Failed to load permissions: {e}")


# Initialize from disk
_load_persisted_permissions()


def get_permission_mode() -> PermissionMode:
    return _CURRENT_MODE


def set_permission_mode(mode: PermissionMode) -> PermissionMode:
    global _CURRENT_MODE
    _CURRENT_MODE = mode
    _save_persisted_permissions()
    return _CURRENT_MODE


def get_tool_toggles() -> Dict[str, bool]:
    return dict(_TOOL_TOGGLES)


def set_tool_toggle(tool_category: str, enabled: bool) -> Dict[str, bool]:
    _TOOL_TOGGLES[tool_category] = enabled
    _save_persisted_permissions()
    return dict(_TOOL_TOGGLES)


def is_dangerous_command(cmd: str) -> Tuple[bool, str]:
    """Check if command matches dangerous system-level patterns using regex."""
    clean = cmd.strip()
    for pattern, reason in _DANGEROUS_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            return True, reason
    return False, ""


def is_command_allowed_always(cmd: str) -> bool:
    """Check if command matches user-approved Allow Always whitelist.
    
    STRICT EXACT MATCH ONLY (Amendment 3):
    1. Dangerous commands can NEVER be auto-approved.
    2. clean == rule only. Loose prefix matching is strictly forbidden.
    """
    clean = cmd.strip()
    is_danger, _ = is_dangerous_command(clean)
    if is_danger:
        return False

    return clean in _ALLOW_ALWAYS_COMMANDS


def add_allow_always_command(command: str) -> bool:
    """Add a verified, safe command to the exact-match Allow Always store."""
    clean = command.strip()
    is_danger, _ = is_dangerous_command(clean)
    if is_danger or not clean:
        return False
    if clean not in _ALLOW_ALWAYS_COMMANDS:
        _ALLOW_ALWAYS_COMMANDS.append(clean)
        _save_persisted_permissions()
        return True
    return False


def get_file_action_spec(path: Union[str, Path]) -> str:
    """Compute canonical action_spec for file operations, following symlinks and resolving paths."""
    resolved = Path(os.path.expanduser(str(path))).resolve()
    return f"file_edit:{resolved}"


def create_terminal_approval(command: str) -> Dict[str, Any]:
    """Register a pending command awaiting interactive user approval with a cryptographic nonce."""
    clean = command.strip()
    is_danger, reason = is_dangerous_command(clean)
    approval_id = f"term_{uuid.uuid4().hex[:8]}"
    ui_nonce = secrets.token_hex(32)

    entry = {
        "id": approval_id,
        "type": "terminal",
        "command": clean,
        "is_dangerous": is_danger,
        "danger_reason": reason,
        "status": "pending",
        "ui_nonce": ui_nonce,
        "execution_token": None,
        "created_at": time.time(),
    }
    _PENDING_TERMINAL_APPROVALS[approval_id] = entry
    log_action("terminal_approval_requested", {"command": clean, "is_dangerous": is_danger, "approval_id": approval_id}, "APPROVAL", "PENDING")
    return entry


def get_terminal_approval(approval_id: str) -> Optional[Dict[str, Any]]:
    """Return a fresh copy of an approval entry from the unified store."""
    entry = _PENDING_TERMINAL_APPROVALS.get(approval_id)
    return dict(entry) if entry else None


def resolve_terminal_approval(approval_id: str, action: str, ui_nonce: str) -> Optional[Dict[str, Any]]:
    """Validate ui_nonce, resolve approval, and issue a single-use execution_token.
    
    Enforces Zero Self-Approval (Amendment 4):
    Must match cryptographic nonce generated by server and sent exclusively to HUD.
    """
    entry = _PENDING_TERMINAL_APPROVALS.get(approval_id)
    if not entry:
        return None

    # Cryptographic nonce check
    stored_nonce = entry.get("ui_nonce", "")
    if not hmac.compare_digest(stored_nonce, ui_nonce):
        log_action("zero_self_approval_blocked", {"approval_id": approval_id}, "APPROVAL", "VIOLATION")
        return None

    # Read-Only Mode hard enforcement: Approving any execution or mutation is strictly forbidden
    if _CURRENT_MODE == PermissionMode.READ_ONLY and action in ("allow_once", "allow_always"):
        log_action("resolve_approval_blocked_read_only", {"approval_id": approval_id, "action": action}, "READ_ONLY", "BLOCKED")
        return None

    cmd = entry["command"]
    if action in ("allow_once", "allow_always"):
        execution_token = f"exec_{uuid.uuid4().hex}"
        entry["status"] = action
        entry["execution_token"] = execution_token
        entry["resolved_at"] = time.time()

        if action == "allow_always" and not entry.get("is_dangerous", False):
            add_allow_always_command(cmd)

        log_action("terminal_approval_resolved", {"command": cmd, "action": action, "approval_id": approval_id}, "APPROVAL", "ALLOWED")
        return dict(entry)
    else:
        entry["status"] = "denied"
        entry["resolved_at"] = time.time()
        log_action("terminal_approval_resolved", {"command": cmd, "action": "deny", "approval_id": approval_id}, "APPROVAL", "DENIED")
        return dict(entry)


def verify_and_consume_approval_token(token: str, command: str) -> bool:
    """Validate and immediately consume a single-use execution_token in the unified store."""
    if not token:
        return False
    clean = command.strip()
    for app_id, entry in list(_PENDING_TERMINAL_APPROVALS.items()):
        if entry.get("execution_token") == token:
            if entry.get("command") == clean and entry.get("status") in ("allow_once", "allow_always"):
                # Single-use: consume and destroy
                _PENDING_TERMINAL_APPROVALS.pop(app_id, None)
                return True
    return False


def expire_terminal_approval(approval_id: str) -> Optional[Dict[str, Any]]:
    """Explicitly clean up timed-out approval to prevent store unbounded growth."""
    entry = _PENDING_TERMINAL_APPROVALS.pop(approval_id, None)
    if entry:
        entry["status"] = "timed_out"
        log_action("terminal_approval_timed_out", {"command": entry["command"], "approval_id": approval_id}, "APPROVAL", "TIMED_OUT")
    return entry


def get_pending_terminal_approvals() -> List[Dict[str, Any]]:
    return [dict(e) for e in _PENDING_TERMINAL_APPROVALS.values()]


def clear_pending_terminal_approvals() -> int:
    """Flush and cancel all pending approvals (e.g. on Panic Kill or restart)."""
    count = len(_PENDING_TERMINAL_APPROVALS)
    for app_id, entry in list(_PENDING_TERMINAL_APPROVALS.items()):
        log_action("terminal_approval_cancelled", {"command": entry["command"], "approval_id": app_id}, "APPROVAL", "CANCELLED")
    _PENDING_TERMINAL_APPROVALS.clear()
    return count


# Multi-Action Tool Governance Specification (Action-Aware Security Rule)
# Maps tool_name -> (action_parameter_name, set_of_safe_read_only_actions)
# Rule: Any action NOT in this safe set is treated as mutating / state-modifying.
# Safe actions MUST be explicit — empty string or missing action fails safe (never assumed harmless).
_MULTI_ACTION_SAFE_ACTIONS: Dict[str, Tuple[str, set]] = {
    "git_branch": ("action", {"list", "show", "current"}),
    "git_pr": ("action", {"view", "list", "show"}),
    "media_control": ("action", {"status", "get_status", "metadata", "get_track", "info"}),
    "control_hardware": ("action", {"get", "status", "query", "check", "info"}),
}


def classify_action(tool_name: str, args: Dict[str, Any], is_night_shift: bool = False) -> PermissionTier:
    """Classify an action into AUTO, APPROVAL, or NEVER tier based on active PermissionMode."""
    name = tool_name.lower()

    # 1. Check for NEVER patterns
    if name in ("run_shell", "run_privileged", "run_sudo"):
        cmd = str(args.get("command", "")).strip()
        for pat in _NEVER_PATTERNS:
            if pat in cmd:
                return PermissionTier.NEVER

    # 2. READ_ONLY Mode check (Section 10 & Hard Security Gate)
    if _CURRENT_MODE == PermissionMode.READ_ONLY:
        # Action-aware inspection for multi-action tools
        if name in _MULTI_ACTION_SAFE_ACTIONS:
            arg_key, safe_actions = _MULTI_ACTION_SAFE_ACTIONS[name]
            act = str(args.get(arg_key, "")).lower().strip()
            if act not in safe_actions:
                # Modifying action under multiplexed tool is strictly NEVER in Read-Only
                return PermissionTier.NEVER
            return PermissionTier.AUTO

        read_only_allowed = {
            "take_screenshot",
            "reflect_screen",
            "read_file",
            "list_directory",
            "read_document",
            "get_weather",
            "get_battery_status",
            "get_clipboard_content",
            "test_website_health",
            "ping_host",
            "git_status",
            "git_diff",
            "git_pr_view",
            "get_volume",
            "system_info",
            "system_health",
        }
        if name not in read_only_allowed:
            # Zero-tolerance: in Read-Only mode, any mutating or external action is NEVER permitted
            return PermissionTier.NEVER
        return PermissionTier.AUTO

    # 3. Night Shift strictness
    if is_night_shift:
        if "send" in name or "submit" in name or "buy" in name or "pay" in name:
            return PermissionTier.APPROVAL

    # 4. Multi-action tools in normal/limited modes (action-aware permissioning)
    if name in _MULTI_ACTION_SAFE_ACTIONS:
        arg_key, safe_actions = _MULTI_ACTION_SAFE_ACTIONS[name]
        act = str(args.get(arg_key, "")).lower().strip()
        if act not in safe_actions:
            return PermissionTier.APPROVAL
        return PermissionTier.AUTO

    # 5. Sensitive and state-modifying tools that always require approval
    approval_tools = {
        "send_email",
        "write_file",
        "append_file",
        "delete_file",
        "git_commit",
        "git_push",
        "git_merge",
        "git_clone",
        "git_pull",
        "git_branch_create",
        "git_branch_switch",
        "git_pr_create",
        "git_pr_comment",
        "set_clipboard_content",
        "launch_application",
        "schedule_reminder",
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
        # Strict security rule: git_push with force=True is NEVER permitted
        if name == "git_push" and bool(args.get("force", False)):
            return PermissionTier.NEVER
        return PermissionTier.APPROVAL

    # 6. Shell execution is always gated unless matched by Allow Always whitelist
    if name == "run_shell":
        cmd = str(args.get("command", "")).strip()
        if is_command_allowed_always(cmd):
            return PermissionTier.AUTO
        return PermissionTier.APPROVAL

    return PermissionTier.AUTO
