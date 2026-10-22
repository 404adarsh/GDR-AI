"""Acceptance Test 12: Coding and Workspace Agent.
Verifies:
1. Workspace directory allowlist enforcement.
2. Blocking of secret files (.env, credentials, pem keys).
3. Branch creation, code modification, test running, and diff generation.
4. Policy Engine gating with ASK decision (waiting for user approval).
"""

from pathlib import Path
import subprocess
import pytest
from gdr.tools.coding_agent import CodingAgent, WorkspaceSecurityViolation
from gdr.safety.policy_engine import ActionDecision


def test_acceptance_12_coding_agent_flow_and_approval(tmp_path):
    # Initialize a mock git project inside tmp_path
    project_dir = tmp_path / "project_x"
    project_dir.mkdir(parents=True)

    # Initialize git repo in project_dir
    subprocess.run(["git", "init"], cwd=str(project_dir), check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "TestUser"], cwd=str(project_dir), check=True)
    subprocess.run(["git", "config", "user.email", "test@domain.com"], cwd=str(project_dir), check=True)

    # Initial file
    init_file = project_dir / "calculator.py"
    init_file.write_text("def add(a, b):\n    return a + b\n")
    subprocess.run(["git", "add", "."], cwd=str(project_dir), check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=str(project_dir), check=True)

    # Initialize coding agent with project_dir allowlisted
    agent = CodingAgent(allowed_directories=[project_dir])

    # 1. Test Secret Blocking (.env and id_rsa must raise WorkspaceSecurityViolation)
    with pytest.raises(WorkspaceSecurityViolation):
        agent.validate_path(project_dir / ".env")

    with pytest.raises(WorkspaceSecurityViolation):
        agent.validate_path(project_dir / "id_rsa")

    # 2. Test Path Outside Workspace
    outside_dir = tmp_path / "unauthorized_dir"
    outside_dir.mkdir()
    with pytest.raises(WorkspaceSecurityViolation):
        agent.validate_path(outside_dir / "file.txt")

    # 3. Acceptance Test 12: "Add a function and tests to project X"
    task = "Add multiply function and unit tests"
    file_edits = {
        "calculator.py": (
            "def add(a, b):\n    return a + b\n\n"
            "def multiply(a, b):\n    return a * b\n"
        ),
        "test_calc.py": (
            "import unittest\n"
            "from calculator import add, multiply\n\n"
            "class TestCalc(unittest.TestCase):\n"
            "    def test_multiply(self):\n"
            "        self.assertEqual(multiply(3, 4), 12)\n"
            "        self.assertEqual(add(2, 2), 4)\n\n"
            "if __name__ == '__main__':\n"
            "    unittest.main()\n"
        )
    }

    test_cmd = "python3 -m unittest test_calc.py"

    result = agent.run_coding_task(
        project_dir=project_dir,
        task_description=task,
        file_edits=file_edits,
        test_command=test_cmd
    )

    # Verify branch was created
    assert result["branch"].startswith("gdr/")
    assert "multiply" in result["branch"]

    # Verify tests passed
    assert result["tests_passed"] is True
    assert "test_calc.py" in result["modified_files"]

    # Verify diff is generated showing the new function
    assert "def multiply" in result["diff"]
    assert "test_multiply" in result["diff"]

    # Verify waiting for user approval via Policy Engine
    assert result["status"] == "waiting_for_approval"
    policy_card = result["policy_card"]
    assert policy_card.decision == ActionDecision.ASK
    assert policy_card.can_edit is True

    print("\n--- Acceptance Test 12 Passed Output ---")
    print(f"Created Branch: {result['branch']}")
    print(f"Tests Output:\n{result['test_output']}")
    print(f"Diff Preview:\n{result['diff']}")
    print(f"Policy Decision: {policy_card.decision} - {policy_card.reason}")
