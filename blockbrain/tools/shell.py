"""Shell and privileged execution tools for blockbrain AI.
Enforces command allowlists and prevents command injections.
"""

import os
import subprocess
from typing import Dict, Any, Optional

from blockbrain.config import load_config
from blockbrain.tools.registry import tool
from blockbrain.safety.untrusted import is_session_tainted

MAX_TOOL_OUTPUT = 25000  # Generous output limit to prevent aggressive truncation


def _truncate_output(text: str, limit: int = MAX_TOOL_OUTPUT) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return (
        f"{text[:half]}\n\n"
        f"... [Output truncated: {len(text)} chars total. Showing first {half} and last {half} chars] ...\n\n"
        f"{text[-half:]}"
    )


def _execute_subprocess(command: str, timeout_seconds: int) -> str:
    """Execute raw bash subprocess and format output."""
    try:
        proc = subprocess.run(
            command,
            shell=True,
            executable="/bin/bash",
            capture_output=True,
            text=True,
            timeout=timeout_seconds
        )
        out = proc.stdout
        err = proc.stderr
        code = proc.returncode

        res = []
        if out:
            res.append(out)
        if err:
            res.append(f"[stderr]:\n{err}")
        res.append(f"[exit code: {code}]")

        return _truncate_output("\n".join(res))
    except subprocess.TimeoutExpired:
        return f"Error: Command timed out after {timeout_seconds}s."
    except Exception as e:
        return f"Execution error: {e}"


@tool(
    name="run_shell",
    description="Run a non-root shell command on the host. Requires user APPROVAL for all non-whitelisted or dangerous commands.",
    category="shell",
    tier="APPROVAL",
    requires_approval=True
)
def run_shell(command: str, timeout_seconds: int = 60, approval_token: Optional[str] = None) -> str:
    """Execute standard shell command with mandatory permission and hazard gating."""
    clean = command.strip()
    if not clean:
        return "No command provided"

    # Firewall: Tamper protection for audit.log
    if "audit.log" in clean and any(op in clean for op in (">", "rm ", "truncate", "mv ", "chmod ")):
        return "❌ Security Violation: Direct modification of audit.log is strictly forbidden."

    from blockbrain.safety.tiers import (
        get_permission_mode,
        PermissionMode,
        is_dangerous_command,
        is_command_allowed_always,
        create_terminal_approval,
        verify_and_consume_approval_token,
    )
    from blockbrain.safety.audit import log_action

    # 1. Read-Only Mode strictly blocks terminal execution
    if get_permission_mode() == PermissionMode.READ_ONLY:
        log_action("run_shell", {"command": clean}, "READ_ONLY", "BLOCKED", "Read-only mode enforcement")
        return "❌ Action blocked: Terminal execution is strictly disabled in Read-Only Mode."

    # 2. Check for dangerous patterns
    is_danger, danger_reason = is_dangerous_command(clean)

    # 3. Verified UI Approval Token check (from interactive user click)
    if approval_token and verify_and_consume_approval_token(approval_token, clean):
        log_action("run_shell", {"command": clean}, "APPROVAL", "EXECUTED_WITH_TOKEN")
        return _execute_subprocess(clean, timeout_seconds)

    # 4. Strict Allow Always exact match check (NEVER allowed if command is dangerous)
    if is_command_allowed_always(clean) and not is_danger:
        log_action("run_shell", {"command": clean}, "AUTO", "EXECUTED_ALLOW_ALWAYS")
        return _execute_subprocess(clean, timeout_seconds)

    # 5. Halt & Block: Command cannot execute without verified user click
    appr = create_terminal_approval(clean)
    log_action("run_shell", {"command": clean, "is_dangerous": is_danger}, "APPROVAL", "BLOCKED_WAITING_APPROVAL")

    if is_danger:
        return (
            f"🛑 BLOCKED: Dangerous command '{clean}' requires interactive user approval ({danger_reason}).\n"
            f"An approval request has been dispatched to the BlockBrain HUD (Approval ID: {appr['id']})."
        )
    return (
        f"⚠️ APPROVAL REQUIRED: Shell command '{clean}' requires interactive confirmation.\n"
        f"Please approve or deny this command in the BlockBrain HUD (Approval ID: {appr['id']})."
    )


@tool(
    name="run_privileged",
    description="Run an administrative command via sudo against an approved allowlist. Requires APPROVAL.",
    category="shell",
    tier="APPROVAL",
    requires_approval=True
)
def run_privileged(command: str) -> str:
    """Execute privileged command if prefix is in sudo allowlist."""
    cfg = load_config()
    allowlist = cfg.get("safety", {}).get("sudo_allowlist", [])

    clean_cmd = command.strip()
    is_allowed = any(clean_cmd.startswith(prefix) for prefix in allowlist)

    if not is_allowed:
        return (
            f"❌ Command rejected. '{clean_cmd}' is NOT in the sudo allowlist.\n"
            f"Allowed prefixes: {allowlist}"
        )

    try:
        proc = subprocess.run(
            ["sudo", "-n"] + clean_cmd.split(),
            capture_output=True,
            text=True,
            timeout=60
        )
        return _truncate_output(f"Output:\n{proc.stdout}\nErrors:\n{proc.stderr}\nCode: {proc.returncode}")
    except Exception as e:
        return f"Privileged execution error: {e}"

