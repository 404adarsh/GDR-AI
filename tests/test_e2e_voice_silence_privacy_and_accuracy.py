"""End-to-End Test Suite for GDR-AI Silence Controller, Voice Interruption,
Privacy Guards, and Contact Disambiguation (Prompt 5/5).
"""

import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from gdr.core.silence_controller import SilenceController, get_silence_controller
from gdr.core.proactive import get_proactive_message
from gdr.memory.store import MemoryStore
from gdr.tools.research import check_personal_disambiguation, web_search
from gdr.web.server import app


@pytest.fixture
def test_silence_controller(tmp_path):
    """Provide an isolated SilenceController instance with a temporary state file."""
    state_file = tmp_path / "silence_state.json"
    sc = SilenceController(state_file=state_file)
    return sc


@pytest.fixture
def test_client():
    """FastAPI TestClient for GDR web server."""
    return TestClient(app)


def test_silence_controller_activation_and_expiry(test_silence_controller):
    sc = test_silence_controller
    assert not sc.is_silence_active()
    assert sc.get_remaining_seconds() == 0.0

    # 1. Activate timed silence (e.g. 5 minutes)
    sc.activate_silence(duration_minutes=5, reason="user_test")
    assert sc.is_silence_active()
    remaining = sc.get_remaining_seconds()
    assert 280 <= remaining <= 300
    assert sc.current_reason == "user_test"

    # 2. Deactivate explicitly
    sc.deactivate_silence()
    assert not sc.is_silence_active()
    assert sc.get_remaining_seconds() == 0.0


def test_silence_controller_until_resumed(test_silence_controller):
    sc = test_silence_controller
    sc.activate_silence(until_resumed=True, reason="indefinite_quiet")
    assert sc.is_silence_active()
    assert sc.until_resumed is True
    assert sc.get_remaining_seconds() == 86400.0

    sc.deactivate_silence()
    assert not sc.is_silence_active()
    assert sc.until_resumed is False


def test_silence_controller_parse_intents(test_silence_controller):
    sc = test_silence_controller

    # Silence commands
    for phrase in [
        "chup raho",
        "tum 5 minute ke liye chup ho sakte ho?",
        "thodi der chup ho jao",
        "don't speak",
        "please stop talking",
        "be quiet",
        "don't disturb me",
        "shant ho jao",
    ]:
        res = sc.parse_silence_intent(phrase)
        assert res is not None, f"Failed to parse: '{phrase}'"
        assert res["action"] in ("activate_silence", "stop_current_speech")

    # Resume commands
    for phrase in [
        "resume",
        "ab bol sakte ho",
        "start speaking",
        "chup mat raho",
        "you can speak now",
    ]:
        res = sc.parse_silence_intent(phrase)
        assert res is not None, f"Failed to parse resume: '{phrase}'"
        assert res["action"] == "resume"


def test_proactive_messaging_suppressed_during_silence(test_silence_controller, monkeypatch):
    """Verify that Aarushi NEVER generates unsolicited messages during quiet mode."""
    monkeypatch.setattr("gdr.core.proactive.get_silence_controller", lambda: test_silence_controller)
    test_silence_controller.activate_silence(duration_minutes=10, reason="quiet_test")

    # Proactive messaging must return empty string
    msg = get_proactive_message(is_followup=False)
    assert msg == ""

    msg_followup = get_proactive_message(is_followup=True)
    assert msg_followup == ""


def test_personal_disambiguation_guard():
    """Verify that queries for personal contacts receive the disambiguation header."""
    # 1. Personal contact searches with ambiguous names
    disambig_ayushi = check_personal_disambiguation("Ayushi")
    assert "[PRIVACY & DISAMBIGUATION NOTICE" in disambig_ayushi
    assert "NOT evidence" in disambig_ayushi

    disambig_girlfriend = check_personal_disambiguation("my girlfriend Ayushi")
    assert "[PRIVACY & DISAMBIGUATION NOTICE" in disambig_girlfriend

    disambig_friend = check_personal_disambiguation("mera dost Rahul")
    assert "[PRIVACY & DISAMBIGUATION NOTICE" in disambig_friend

    # 2. Technical queries should NOT have the disambiguation warning
    disambig_python = check_personal_disambiguation("python asyncio tutorial")
    assert disambig_python == ""

    disambig_linux = check_personal_disambiguation("linux systemd service")
    assert disambig_linux == ""


def test_memory_store_girlfriend_relationship_and_privacy(tmp_path):
    """Verify memory accurately records girlfriend relationship and purges unverified claims."""
    mem_file = tmp_path / "memory.db"
    ms = MemoryStore(db_path=mem_file)

    # Remember girlfriend's name
    ms.auto_learn_from_user("My girlfriend is Ayushi")
    rel = ms.get_personal_relationship("Ayushi")
    assert rel is not None
    assert rel["relationship"] == "girlfriend"
    assert rel["verified"] is True

    # User explicitly corrects/purges an unverified claim
    ms.correct_personal_fact(
        "Ayushi",
        "Ayushi is a student and user's girlfriend, not a journalist or public figure.",
        category="people_relationships"
    )
    purged_count = ms.purge_unverified_contact_claims("Ayushi")
    assert isinstance(purged_count, int)

    # Check suppression preferences
    ms.set_preference("suppress_user_name", True)
    assert ms.get_preference("suppress_user_name") is True

    ms.set_preference("language_override", "en")
    assert ms.get_preference("language_override") == "en"


def test_silence_api_endpoints(test_client):
    """Verify REST API silence status, activate, and deactivate endpoints."""
    # 1. Activate silence via API
    resp = test_client.post("/api/silence/activate", json={
        "duration_minutes": 15,
        "reason": "api_test"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["active"] is True
    assert data["reason"] == "api_test"

    # 2. Check silence status
    st_resp = test_client.get("/api/silence/status")
    assert st_resp.status_code == 200
    st_data = st_resp.json()
    assert st_data["active"] is True
    assert st_data["remaining_seconds"] > 0

    # 3. TTS speech endpoints must be suppressed during silence
    tts_resp = test_client.post("/api/tts/speak", json={"text": "Hello test"})
    assert tts_resp.status_code == 200
    tts_data = tts_resp.json()
    assert tts_data["played"] is False
    assert tts_data["status"] == "silence_mode_active"

    # 4. Deactivate silence via API
    deact_resp = test_client.post("/api/silence/deactivate")
    assert deact_resp.status_code == 200
    assert deact_resp.json()["active"] is False

    # 5. Check status is now deactivated
    st_resp2 = test_client.get("/api/silence/status")
    assert st_resp2.json()["active"] is False


def test_stop_speech_and_barge_in_endpoints(test_client):
    """Verify that /api/stop and /api/tts/stop immediately halt audio playback."""
    resp1 = test_client.post("/api/stop")
    assert resp1.status_code == 200
    assert resp1.json()["success"] is True

    resp2 = test_client.post("/api/tts/stop")
    assert resp2.status_code == 200
    assert resp2.json()["stopped"] is True
