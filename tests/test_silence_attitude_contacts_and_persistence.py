"""Tests for Call & Silence ego/attitude recovery, Contacts network with trust levels, and persistence across restart."""

import os
import pytest
from starlette.testclient import TestClient
from gdr.web.server import app
from gdr.core.silence_controller import SilenceController
from gdr.contacts.service import ContactService
from gdr.safety.secrets import get_secret, _save_env_secret
from gdr.config import load_config
from gdr.core.persona import PersonaConfig


@pytest.fixture
def test_client():
    return TestClient(app)


def test_silence_controller_shut_up_attitude_flow():
    """Verify that saying 'shut up' activates short silence with attitude and clears when user speaks next."""
    sc = SilenceController()

    # 1. User says "shut up. don't speak"
    parsed = sc.parse_silence_intent("don't speak. shut uup")
    assert parsed is not None
    assert parsed.get("action") == "attitude_shut_up"

    # Activate silence
    res = sc.activate_silence(duration_minutes=parsed.get("duration_minutes"), reason=parsed.get("raw_phrase"))
    assert res["is_silent"] is True
    # Verify it is timed, not indefinite
    assert res["mode"] == "timed"
    assert res["duration_minutes"] == 0.5  # 30 seconds default
    sc.record_shut_up_event(parsed.get("raw_phrase"))

    # Verify attitude silence event is recorded
    status = sc.get_status()
    assert status["is_silent"] is True

    # 2. User speaks next: "kahan ho aarushi? batayein mujhe"
    attitude_trigger = sc.consume_attitude_silence()
    assert attitude_trigger is not None
    assert "shut" in attitude_trigger.lower() or "speak" in attitude_trigger.lower()

    # Verify silence is now automatically deactivated
    status_after = sc.get_status()
    assert status_after["is_silent"] is False

    # 3. Test Agent level attitude generation
    from unittest.mock import patch
    from gdr.core.agent import Agent
    from gdr.core.providers import LLMResponse

    agent = Agent()
    # Trigger attitude silence state again
    sc.record_shut_up_event("shut up")
    with patch.object(agent.provider, "chat", return_value=LLMResponse(content="Main theek hoon!")):
        reply = agent.run("Suno, kahan ho tum?")
        assert "Arey waah" in reply or "shut up" in reply
        assert "Mere bina nahi raha gaya na" in reply or "stay away" in reply


def test_contacts_service_crud_and_trust_levels(tmp_path):
    """Test that ContactsService stores and retrieves trust_level and category."""
    db_path = tmp_path / "test_contacts.db"
    svc = ContactService(db_path=db_path)

    # 1. Add trusted family member
    c1 = svc.add_contact(
        display_name="Mom",
        relationship_type="Trusted Family",
        email="mom@example.com",
        phone_number="+919876543210",
        trust_level=95,
        category="Family",
        is_trusted_contact=True
    )
    assert c1["id"] is not None
    assert c1["trust_level"] == 95
    assert c1["relationship_type"] == "Trusted Family"

    # 2. Add enemy / untrusted contact
    c2 = svc.add_contact(
        display_name="Rival Hacker",
        relationship_type="Enemy / Rival / Untrusted",
        email="rival@phishing.org",
        phone_number="+919800000000",
        trust_level=10,
        category="Enemy",
        is_trusted_contact=False
    )
    assert c2["trust_level"] == 10

    # 3. Update contact trust level
    updated = svc.update_contact(
        contact_id=c2["id"],
        trust_level=5,
        notes="Confirmed hostile attacker. Never send sensitive data."
    )
    assert updated["trust_level"] == 5
    assert "hostile" in updated["notes"]

    # 4. Check prompt summary contains safety warnings
    summary = svc.get_contact_summary_for_prompt()
    assert "Mom" in summary
    assert "Rival Hacker" in summary
    assert "UNTRUSTED / ENEMY" in summary


def test_contacts_api_endpoints(test_client):
    """Test /api/contacts endpoints with trust_level and category."""
    # 1. Create a contact via API
    payload = {
        "display_name": "Best Friend Rahul",
        "relationship_type": "Best Friend",
        "email": "rahul@test.com",
        "phone_number": "+919988776655",
        "trust_level": 90,
        "is_trusted_contact": True,
        "notes": "College best friend"
    }
    res = test_client.post("/api/contacts", json=payload)
    assert res.status_code == 200
    d = res.json()
    assert d.get("success") is True
    contact_id = d.get("contact", {}).get("id")
    assert contact_id is not None
    assert d.get("contact", {}).get("trust_level") == 90

    # 2. Retrieve contacts
    res = test_client.get("/api/contacts")
    assert res.status_code == 200
    contacts_list = res.json()
    assert any(c["display_name"] == "Best Friend Rahul" for c in contacts_list)

    # 3. Update contact via PUT
    update_payload = {
        "trust_level": 95,
        "notes": "Updated: childhood best friend"
    }
    res = test_client.put(f"/api/contacts/{contact_id}", json=update_payload)
    assert res.status_code == 200
    assert res.json().get("success") is True
    assert res.json().get("contact", {}).get("trust_level") == 95

    # 4. Delete contact
    del_res = test_client.delete(f"/api/contacts/{contact_id}")
    assert del_res.status_code == 200
    assert del_res.json().get("success") is True


def test_profile_and_name_persistence_across_restart(test_client):
    """Test that profile name saves persist into environment and persona."""
    save_payload = {
        "user_name": "Gaurav Master",
        "assistant_name": "Aarushi Companion",
        "system_prompt": "You are Aarushi, personal companion."
    }
    res = test_client.post("/api/settings/profile", json=save_payload)
    assert res.status_code == 200
    d = res.json()
    assert d.get("success") is True

    # Verify environment and secrets loaded
    assert os.environ.get("USER_NAME") == "Gaurav Master"
    assert os.environ.get("ASSISTANT_NAME") == "Aarushi Companion"

    # Verify Persona reflects updated authoritative names
    persona = PersonaConfig.from_config()
    assert persona.user_name == "Gaurav Master"
    assert persona.name == "Aarushi Companion"
