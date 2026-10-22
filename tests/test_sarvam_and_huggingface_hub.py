import pytest
import os
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from gdr.web.server import app, get_agent
from gdr.core.agent import Agent
from gdr.core.providers import SarvamProvider, OfflineLocalProvider, get_provider
from gdr.models.downloader import (
    HF_PRESETS,
    CLOUD_MODELS,
    get_download_state,
    list_local_models
)
from gdr.web.dashboard_html import DASHBOARD_HTML


@pytest.fixture
def client():
    return TestClient(app)


def test_sarvam_key_dynamic_detection_in_agent():
    """Verify that when a user adds SARVAM_API_KEY, Agent immediately detects and uses it."""
    # 1. Without key: Agent runs in offline mode
    with patch.dict(os.environ, {"SARVAM_API_KEY": ""}, clear=True), \
         patch("gdr.core.providers.get_secret", return_value=""), \
         patch("gdr.safety.secrets.get_secret", return_value=""):
        agent = Agent()
        # If provider lacks key, has_cloud_key is False
        assert not getattr(agent.provider, "api_key", False)

    # 2. When key is supplied in secrets: Agent dynamically switches to SarvamProvider
    with patch.dict(os.environ, {"SARVAM_API_KEY": "sk_test_sarvam_secret_key_12345"}), \
         patch("gdr.core.providers.get_secret", return_value="sk_test_sarvam_secret_key_12345"), \
         patch("gdr.safety.secrets.get_secret", return_value="sk_test_sarvam_secret_key_12345"):
        # Mock SarvamAI client
        with patch("sarvamai.SarvamAI"):
            prov = SarvamProvider()
            assert prov.api_key == "sk_test_sarvam_secret_key_12345"

            agent = Agent()
            # Run with mock provider
            with patch.object(agent.provider, "chat") as mock_chat:
                mock_chat.return_value = MagicMock(content="Hello from Sarvam AI!", tool_calls=[])
                with patch("gdr.core.network.is_online", return_value=True):
                    reply = agent.run("hi")
                    assert "Sarvam" in reply or len(reply) > 0
                    assert agent.is_offline_mode is False


def test_model_hub_endpoints(client):
    """Test /api/models list, /api/models/active switch, and download status."""
    # 1. GET /api/models
    res = client.get("/api/models")
    assert res.status_code == 200
    data = res.json()
    assert "active_provider" in data
    assert "cloud_models" in data
    assert "hf_presets" in data
    assert len(data["hf_presets"]) >= 4

    # Check preset contents
    qwen_preset = next((p for p in data["hf_presets"] if "qwen" in p["id"]), None)
    assert qwen_preset is not None
    assert "url" in qwen_preset
    assert qwen_preset["filename"].endswith(".gguf")

    # 2. POST /api/models/active
    switch_res = client.post("/api/models/active", json={
        "provider": "sarvam",
        "model": "sarvam-2b"
    })
    assert switch_res.status_code == 200
    switch_data = switch_res.json()
    assert switch_data["success"] is True
    assert switch_data["model"] == "sarvam-2b"

    # 3. GET /api/models/pull/status
    status_res = client.get("/api/models/pull/status")
    assert status_res.status_code == 200
    st = status_res.json()
    assert "status" in st
    assert "percent" in st


def test_home_screen_audio_frequency_and_live_hearing_elements():
    """Verify Home screen contains the live microphone frequency canvas and transcript box."""
    assert 'id="home-live-audio-box"' in DASHBOARD_HTML
    assert 'id="home-audio-wave"' in DASHBOARD_HTML
    assert 'id="home-live-transcript-text"' in DASHBOARD_HTML
    assert 'id="home-mic-freq-label"' in DASHBOARD_HTML
    assert 'id="model-manager-modal"' in DASHBOARD_HTML
    assert 'openModelHubModal' in DASHBOARD_HTML
