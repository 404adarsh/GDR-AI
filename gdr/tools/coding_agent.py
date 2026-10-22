"""Coding and Workspace Agent for GDR AI (Phase 13).
Restricted strictly to allowlisted project folders.
Blocks secret files (.env, id_rsa, .pem, credentials).
Plans tasks, creates git feature branches, runs tests, generates diffs,
and enforces explicit user approval before commit/push.
"""

from dataclasses import dataclass
from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
import subprocess
from typing import Dict, Any, List, Optional, Tuple

from gdr.config import load_config
from gdr.safety.policy_engine import get_policy_engine, PolicyCard, ActionDecision

logger = logging.getLogger("gdr.coding_agent")

BLOCKED_PATTERNS = [
    r"\.env(?:\..*)?$",
    r"id_rsa(?:\..*)?$",
    r"id_ed25519(?:\..*)?$",
    r".*\.pem$",
    r".*\.key$",
    r"credentials\.json$",
    r"token\.json$",
    r".*secret.*",
    r"\.bash_history$",
]


class WorkspaceSecurityViolation(PermissionError):
    pass


class CodingAgent:
    """Safely executes programming tasks within designated project directories."""

    def __init__(self, allowed_directories: Optional[List[Path]] = None):
        cfg = load_config()
        configured_dirs = cfg.get("workspace", {}).get("allowed_directories", [os.getcwd()])
        self.allowed_directories = [Path(d).resolve() for d in (allowed_directories or configured_dirs)]
        self.policy_engine = get_policy_engine()

    def validate_path(self, target_path: Path) -> Path:
        """Ensure path is within allowlist and does not target protected secrets."""
        resolved = target_path.resolve()

        # Check secret file pattern blocking
        name = resolved.name
        for pat in BLOCKED_PATTERNS:
            if re.match(pat, name, re.IGNORECASE):
                logger.error(f"Access BLOCKED to secret credential file: {name}")
                raise WorkspaceSecurityViolation(f"Access to secret/credential file '{name}' is forbidden.")

        # Check allowlist
        is_allowed = any(
            resolved == allowed or allowed in resolved.parents
            for allowed in self.allowed_directories
        )
        if not is_allowed:
            logger.error(f"Access BLOCKED to path outside workspace: {resolved}")
            raise WorkspaceSecurityViolation(f"Path '{resolved}' is outside allowlisted workspace directories.")

        return resolved

    def run_coding_task(
        self,
        project_dir: Path,
        task_description: str,
        file_edits: Dict[str, str],
        test_command: Optional[str] = None,
        branch_name_prefix: str = "gdr"
    ) -> Dict[str, Any]:
        """Execute a structured coding task:
        1. Validates directory
        2. Creates a clean git feature branch
        3. Applies file edits
        4. Runs test runner
        5. Generates git diff
        6. Submits diff to Policy Engine (ASK decision, waiting for user approval).
        """
        proj = self.validate_path(project_dir)

        # Generate clean branch name
        clean_slug = re.sub(r"[^a-zA-Z0-9]+", "-", task_description.lower())[:30].strip("-")
        branch_name = f"{branch_name_prefix}/{clean_slug}-{int(datetime.now().timestamp())}"

        # 1. Create git branch
        is_git_repo = (proj / ".git").is_dir()
        if is_git_repo:
            try:
                subprocess.run(
                    ["git", "checkout", "-b", branch_name],
                    cwd=str(proj),
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                logger.warning(f"Git checkout failed ({e}), continuing in place.")

        # 2. Apply edits (validating each file)
        modified_files = []
        for rel_path, new_content in file_edits.items():
            full_path = self.validate_path(proj / rel_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(new_content, encoding="utf-8")
            modified_files.append(rel_path)

        # 3. Run sandboxed tests
        test_output = ""
        test_passed = True
        if test_command:
            try:
                res = subprocess.run(
                    test_command,
                    shell=True,
                    cwd=str(proj),
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                test_output = res.stdout + ("\nSTDERR:\n" + res.stderr if res.stderr else "")
                test_passed = (res.returncode == 0)
            except Exception as e:
                test_output = f"Test execution failed: {e}"
                test_passed = False

        # 4. Generate diff
        diff_text = ""
        if is_git_repo:
            try:
                # Intent to add so git diff includes newly created files
                subprocess.run(["git", "add", "-N", "."], cwd=str(proj), capture_output=True)
                diff_res = subprocess.run(
                    ["git", "diff"],
                    cwd=str(proj),
                    capture_output=True,
                    text=True
                )
                diff_text = diff_res.stdout
            except Exception:
                diff_text = f"Modified files: {', '.join(modified_files)}"
        else:
            diff_text = f"Non-git workspace. Modified files: {', '.join(modified_files)}"

        # 5. Build Policy Card: coding tasks require explicit approval before commit/push
        policy_card = PolicyCard(
            action_name="commit_and_merge_coding_task",
            target=str(proj),
            summary=f"Coding task on branch '{branch_name}': {task_description}",
            decision=ActionDecision.ASK,
            reason="Coding changes alter codebase and require review before committing or pushing.",
            diff_preview=diff_text[:4000],
            can_edit=True
        )

        return {
            "branch": branch_name,
            "modified_files": modified_files,
            "tests_passed": test_passed,
            "test_output": test_output.strip(),
            "diff": diff_text,
            "policy_card": policy_card,
            "status": "waiting_for_approval",
        }
