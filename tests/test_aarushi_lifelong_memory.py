"""Tests for Aarushi Lifelong Memory Engine (Personal Profile, Project Context, Procedural Workflows,
Contradiction Resolution, Credential Filtering, and Backup Export).
"""

import json
from pathlib import Path
import tempfile
import pytest

from gdr.memory.store import MemoryStore, contains_sensitive_credentials
from gdr.memory.lifelong import LifelongMemoryEngine


@pytest.fixture
def temp_memory_store():
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "test_memory.db"
        store = MemoryStore(db_path=db_path)
        yield store


def test_credential_leak_prevention(temp_memory_store):
    """Verify that private keys, API secrets, and passwords are never stored in ordinary memory."""
    store = temp_memory_store

    # Test API Key leak attempt
    res1 = store.remember(
        key="my_openai_key",
        content="Here is my token: sk-proj-abcdef12345678901234567890abcdef123456",
        category="fact"
    )
    assert "Security violation" in res1
    assert store.recall("openai") == []

    # Test Bearer token leak attempt
    res2 = store.remember(
        key="api_bearer",
        content="Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abcdef1234567890",
        category="fact"
    )
    assert "Security violation" in res2
    assert store.recall("Bearer") == []

    # Test Telegram bot token
    res3 = store.remember(
        key="tg_token",
        content="Use bot token 1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ1234567890",
        category="fact"
    )
    assert "Security violation" in res3


def test_personal_profile_persistence(temp_memory_store):
    """Verify long-term personal profile facts survive and retrieve accurately."""
    engine = LifelongMemoryEngine(store=temp_memory_store)

    engine.set_profile_fact("preferred_name", "GDR")
    engine.set_profile_fact("communication_style", "concise and playful")
    engine.set_profile_fact("primary_stack", "Python, TypeScript, FastAPI")

    profile = engine.get_profile()
    assert profile["preferred_name"] == "GDR"
    assert profile["communication_style"] == "concise and playful"
    assert profile["primary_stack"] == "Python, TypeScript, FastAPI"


def test_project_memory_lifecycle(temp_memory_store):
    """Verify structured project memory tracking (purpose, tech_stack, state, blockers, next steps)."""
    engine = LifelongMemoryEngine(store=temp_memory_store)

    # Initial project save
    engine.update_project(
        project_name="GDR-Agent",
        purpose="Jarvis-style personal AI companion",
        tech_stack="Python, FastAPI, SQLite",
        state="Active Development",
        completed_features=["Voice Engine", "Device Mesh"],
        blockers=["Hardware audio loopback"],
        next_steps=["Implement Lifelong Memory"]
    )

    proj = engine.get_project("GDR-Agent")
    assert proj is not None
    assert proj["name"] == "GDR-Agent"
    assert proj["purpose"] == "Jarvis-style personal AI companion"
    assert "Voice Engine" in proj["completed_features"]
    assert "Hardware audio loopback" in proj["known_bugs"] or "Hardware audio loopback" in proj["blockers"]
    assert "Implement Lifelong Memory" in proj["next_steps"]

    # Update project state
    engine.update_project(
        project_name="GDR-Agent",
        state="Phase 6 Complete",
        completed_features=["Voice Engine", "Device Mesh", "Lifelong Memory"],
        next_steps=["Deploy Production Service"]
    )
    updated = engine.get_project("GDR-Agent")
    assert updated["state"] == "Phase 6 Complete"
    assert "Lifelong Memory" in updated["completed_features"]


def test_procedural_workflows_memory(temp_memory_store):
    """Verify procedural instructions and commands are remembered and retrieved."""
    engine = LifelongMemoryEngine(store=temp_memory_store)

    engine.save_workflow(
        workflow_name="run_full_test_suite",
        steps=["Activate virtualenv", "Run pytest with coverage", "Check exit code"],
        commands=[".venv/bin/pytest", "echo $?"]
    )

    wf = engine.get_workflow("run_full_test_suite")
    assert wf is not None
    assert wf["workflow"] == "run_full_test_suite"
    assert len(wf["steps"]) == 3
    assert ".venv/bin/pytest" in wf["commands"]


def test_contradiction_resolution(temp_memory_store):
    """Verify that updating a fact resolves contradictions and maintains accurate knowledge."""
    engine = LifelongMemoryEngine(store=temp_memory_store)

    engine.store.remember("favorite_beverage", "Black Coffee", category="user_preferences")
    res1 = engine.store.recall("coffee")
    assert len(res1) == 1
    assert "Black Coffee" in res1[0]["content"]

    # User expresses new preference
    engine.update_contradiction(
        key="favorite_beverage",
        new_content="Green Tea with Lemon",
        reason="Switched to green tea this month"
    )

    res2 = engine.store.recall("beverage")
    assert len(res2) == 1
    assert "Green Tea" in res2[0]["content"]


def test_memory_export_and_json(temp_memory_store):
    """Verify that all stored lifelong memories can be exported to valid JSON."""
    engine = LifelongMemoryEngine(store=temp_memory_store)

    engine.set_profile_fact("editor", "GDR-IDE")
    engine.update_project("Website", state="In Progress")

    export_json = engine.export_data("json")
    parsed = json.loads(export_json)
    assert isinstance(parsed, list)
    assert len(parsed) >= 2
    keys = [item["key"] for item in parsed]
    assert "profile_editor" in keys
    assert "proj_website" in keys

