"""Developer helper tools for blockbrain AI.
Provides git status, diff inspection, commit drafts, test runner, and code error explanation.
"""

import subprocess
from typing import Optional

from blockbrain.tools.registry import tool
from blockbrain.safety.untrusted import wrap_untrusted_content


@tool(name="git_status", description="Get current git status and changed files.", category="developer", tier="AUTO")
def git_status(repo_dir: str = ".") -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", repo_dir, "status", "--short", "--branch"],
            text=True,
            stderr=subprocess.STDOUT
        )
        return out if out.strip() else "Working tree clean."
    except subprocess.CalledProcessError as e:
        return f"Git error: {e.output}"
    except Exception as e:
        return f"Error: {e}"


@tool(name="git_diff", description="View current unstaged or staged git diff.", category="developer", tier="AUTO")
def git_diff(repo_dir: str = ".", staged: bool = False) -> str:
    cmd = ["git", "-C", repo_dir, "diff"]
    if staged:
        cmd.append("--cached")
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
        if not out.strip():
            return "No changes detected."
        return out[:10000]
    except Exception as e:
        return f"Git diff error: {e}"


@tool(name="run_project_tests", description="Run pytest test suite.", category="developer", tier="AUTO")
def run_project_tests(test_target: str = "tests") -> str:
    try:
        proc = subprocess.run(
            [".venv/bin/pytest", "-v", test_target],
            capture_output=True,
            text=True,
            timeout=120
        )
        return f"Exit code: {proc.returncode}\n\nOutput:\n{proc.stdout}\n{proc.stderr}"
    except Exception as e:
        return f"Error running tests: {e}"


@tool(name="explain_code_error", description="Analyze a stack trace or compiler error log.", category="developer", tier="AUTO")
def explain_code_error(error_text: str) -> str:
    lines = [l.strip() for l in error_text.splitlines() if l.strip()]
    if not lines:
        return "No error text provided."
    return wrap_untrusted_content("compiler/runtime error log", "\n".join(lines[:100]))

