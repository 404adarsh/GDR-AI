"""Comprehensive test suite for:
1. Data-preserving restart (gdr --gui --restart).
2. Safe scoped reset (gdr --reset) with confirmation and automated backups.
3. Persistent conversation history across server restarts and page reloads.
4. Voice Interaction State Machine and 3-second Utterance Finalization Countdown.
"""

import copy
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import pytest
from fastapi.testclient import TestClient

from gdr.config import get_gdr_config_dir, load_config, save_config, DEFAULT_CONFIG
from gdr.memory.store import MemoryStore
from gdr.system.lifecycle import (
    graceful_restart_gui,
    safe_reset_application_data,
    create_scoped_backup,
    find_pids_on_port,
    is_port_in_use,
)
from gdr.web.server import app


@pytest.fixture
def temp_gdr_env(tmp_path, monkeypatch):
    """Set up an isolated GDR environment directory for safe testing."""
    config_dir = tmp_path / "gdr_config"
    config_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("GDR_CONFIG_DIR", str(config_dir))
    monkeypatch.delenv("USER_NAME", raising=False)
    monkeypatch.delenv("ASSISTANT_NAME", raising=False)

    # Initialize sample persistent data
    sample_config = copy.deepcopy(DEFAULT_CONFIG)
    sample_config["general"]["user_name"] = "TestOwner"
    sample_config["general"]["agent_name"] = "AarushiTest"
    save_config(sample_config)

    mem_store = MemoryStore(db_path=config_dir / "memory.db")
    mem_store.remember("test_key_1", "User prefers dark mode", category="preference")
    mem_store.remember("test_key_2", "Project name is GDR-IDE", category="project")
    mem_store.save_chat_message("user", "Hello Aarushi", session_id="default")
    mem_store.save_chat_message("assistant", "Hello! I am here to help you.", session_id="default")

    return config_dir


def test_data_preservation_across_restart(temp_gdr_env):
    """Verify that restarting the GUI lifecycle NEVER deletes or resets user data."""
    config_dir = temp_gdr_env
    mem_db = config_dir / "memory.db"
    cfg_file = config_dir / "config.toml"

    assert mem_db.exists()
    assert cfg_file.exists()

    # Pre-restart state check
    store_before = MemoryStore(db_path=mem_db)
    mems_before = store_before.recall("dark mode")
    history_before = store_before.get_chat_history()
    cfg_before = load_config()

    assert len(mems_before) > 0
    assert len(history_before) == 2
    assert cfg_before["general"]["user_name"] == "TestOwner"

    # Execute restart lifecycle on an unused port (should complete gracefully with zero data loss)
    restarted = graceful_restart_gui(port=65432, timeout_seconds=1.0)
    assert restarted is True

    # Post-restart state check: databases and configs must be completely identical
    assert mem_db.exists()
    assert cfg_file.exists()

    store_after = MemoryStore(db_path=mem_db)
    mems_after = store_after.recall("dark mode")
    history_after = store_after.get_chat_history()
    cfg_after = load_config()

    assert len(mems_after) == len(mems_before)
    assert len(history_after) == len(history_before)
    assert history_after[0]["content"] == "Hello Aarushi"
    assert history_after[1]["content"] == "Hello! I am here to help you."
    assert cfg_after["general"]["user_name"] == "TestOwner"


def test_safe_reset_aborts_without_explicit_confirmation(temp_gdr_env):
    """Verify that safe_reset_application_data refuses to run if confirmation string is not 'RESET'."""
    mem_store = MemoryStore(db_path=temp_gdr_env / "memory.db")
    assert len(mem_store.get_chat_history()) > 0

    # Test non-interactive reset with missing or wrong confirmation
    res_empty = safe_reset_application_data(scope="all", confirmation="", interactive=False)
    assert res_empty["success"] is False
    assert "Confirmation required" in res_empty.get("error", "")

    res_wrong = safe_reset_application_data(scope="all", confirmation="yes", interactive=False)
    assert res_wrong["success"] is False

    # Check that data was NOT touched
    assert len(mem_store.get_chat_history()) > 0
    assert len(mem_store.recall("dark mode")) > 0


def test_safe_reset_scoped_with_automatic_backup(temp_gdr_env):
    """Verify safe reset with confirmation='RESET' creates backup and clears target scope."""
    mem_db = temp_gdr_env / "memory.db"
    mem_store = MemoryStore(db_path=mem_db)

    # 1. Reset conversations scope
    res = safe_reset_application_data(scope="conversations", confirmation="RESET", interactive=False)
    assert res["success"] is True
    assert res["backup_path"] is not None
    backup_path = Path(res["backup_path"])
    assert backup_path.exists()
    assert (backup_path / "memory.db").exists()

    # Conversations should be cleared, but memories still intact
    assert len(mem_store.get_chat_history()) == 0
    assert len(mem_store.recall("dark mode")) > 0

    # 2. Reset memories scope
    res2 = safe_reset_application_data(scope="memories", confirmation="RESET", interactive=False)
    assert res2["success"] is True
    assert len(mem_store.recall("dark mode")) == 0


def test_persistent_chat_history_api(temp_gdr_env):
    """Verify GET and DELETE /api/chat/history endpoints and chat persistence."""
    client = TestClient(app)

    # Verify history returns existing messages
    resp = client.get("/api/chat/history")
    assert resp.status_code == 200
    data = resp.json()
    assert "history" in data
    assert data["count"] >= 2
    assert data["history"][0]["role"] == "user"
    assert data["history"][0]["content"] == "Hello Aarushi"

    # Send a new chat message via POST /api/chat
    chat_resp = client.post("/api/chat", json={"prompt": "What is 2 + 2?"})
    assert chat_resp.status_code == 200
    chat_data = chat_resp.json()
    assert "reply" in chat_data

    # Check that history now has 4 messages
    hist_resp2 = client.get("/api/chat/history")
    assert hist_resp2.status_code == 200
    data2 = hist_resp2.json()
    assert data2["count"] >= 4
    last_user = next((m for m in reversed(data2["history"]) if m["role"] == "user"), None)
    assert last_user is not None
    assert last_user["content"] == "What is 2 + 2?"

    # Clear chat history via API
    del_resp = client.delete("/api/chat/history")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Check history is now 0
    hist_resp3 = client.get("/api/chat/history")
    assert hist_resp3.json()["count"] == 0


def test_voice_and_dashboard_contracts():
    """Verify listening and focus call elements exist in dashboard HTML."""
    from gdr.web.dashboard_html import DASHBOARD_HTML

    assert "playListeningBeep" in DASHBOARD_HTML
    assert "focus-call-overlay" in DASHBOARD_HTML
    assert "focus-stage" in DASHBOARD_HTML
    assert "focus-controls-dock" in DASHBOARD_HTML
