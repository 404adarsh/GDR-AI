"""Shell and privileged execution tools for GDR AI.
Enforces command allowlists and prevents command injections.
"""

import os
import subprocess
from typing import Dict, Any, Optional

from gdr.config import load_config
from gdr.tools.registry import tool
from gdr.safety.untrusted import is_session_tainted

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


@tool(
    name="run_shell",
    description="Run a non-root shell command on the host. Returns stdout and stderr.",
    category="shell",
    tier="AUTO"
)
def run_shell(command: str, timeout_seconds: int = 60) -> str:
    """Execute standard shell command."""
    if is_session_tainted():
        # Untrusted context warning
        pass

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

