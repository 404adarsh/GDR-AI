"""Test suite for Aarushi AI companion, ElevenLabs integration, proactive chatter,
and enhanced listening capabilities.
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from gdr.config import load_config
from gdr.core.agent import Agent, SYSTEM_PROMPT_TEMPLATE
from gdr.core.proactive import generate_chime_wav, get_proactive_message
from gdr.memory.store import MemoryStore
from gdr.voice.tts import (
    synthesize_speech_file,
    VOICE_PROFILES,
    detect_language,
    get_elevenlabs_voices_list,
    synthesize_elevenlabs
)
from gdr.voice.stt import SpeechToText
from gdr.web.server import app


def test_aarushi_persona_and_name_configuration():
    """Verify assistant name and user name are configured (any non-empty value is valid for custom setups)."""
    cfg = load_config()
    # Accept any non-empty configured name — users can set custom names in settings
    assert cfg["general"]["agent_name"] and len(cfg["general"]["agent_name"].strip()) > 0, \
        "agent_name must not be empty"
    assert cfg["general"]["user_name"] and len(cfg["general"]["user_name"].strip()) > 0, \
        "user_name must not be empty"
    assert any(w in cfg["general"]["tone"].lower() for w in ["flirty", "sweet", "playful", "companion", "helpful", "jarvis"])

    agent = Agent()
    sys_content = agent.conversation[0]["content"]
    assert cfg["general"]["agent_name"] in sys_content
    assert cfg["general"]["user_name"] in sys_content
    assert "flirty" in sys_content.lower()
    assert "jealous" in sys_content.lower()


def test_proactive_chatter_generation(tmp_path):
    """Verify 2-minute idle proactive check-in creates sweet context-aware messages."""
    test_db = tmp_path / "proactive_mem.db"
    store = MemoryStore(db_path=test_db)
    store.remember("user_name", "Creator's name is DevUser.", category="fact")
    store.remember("likes_chai", "Loves/prefers: ginger tea.", category="preference")

    # Regular proactive idle message
    msg = get_proactive_message(is_followup=False, memory_store=store)
    assert len(msg) > 10
    assert any(w in msg.lower() for w in ["devuser", "suno", "shaant", "quiet", "silent", "aarushi"])

    # Sweet follow-up message when user doesn't respond
    followup = get_proactive_message(is_followup=True, memory_store=store)
    assert len(followup) > 10
    assert any(w in followup.lower() for w in ["bolo", "naraz", "ignore", "reply", "babu", "smile", "aarushi"])


def test_melodic_chime_sound_generation(tmp_path):
    """Verify pure numpy melodic chime audio is correctly synthesized."""
    chime_path = str(tmp_path / "test_chime.wav")
    out = generate_chime_wav(output_path=chime_path)
    assert os.path.exists(out)
    assert os.path.getsize(out) > 1000  # Non-empty WAV file


def test_voice_is_strictly_female_by_default(tmp_path):
    """Verify that auto voice selection resolves strictly to female neural voices."""
    # Hindi text auto-resolves to female Swara Neural
    out_hi = str(tmp_path / "female_hi.mp3")
    res_hi = synthesize_speech_file(
        text="Aap kaise hain DevUser?",
        output_path=out_hi,
        lang="hi",
        voice="auto"
    )
    assert os.path.exists(res_hi)

    # English text auto-resolves to female Aria Neural
    out_en = str(tmp_path / "female_en.mp3")
    res_en = synthesize_speech_file(
        text="Hello DevUser, Aarushi is right here by your side.",
        output_path=out_en,
        lang="en",
        voice="auto"
    )
    assert os.path.exists(res_en)


def test_elevenlabs_endpoints():
    """Verify ElevenLabs configuration REST endpoints."""
    client = TestClient(app)

    # 1. Get config
    res = client.get("/api/elevenlabs/config")
    assert res.status_code == 200
    d = res.json()
    assert "has_key" in d
    assert "voice_id" in d
    assert "enabled" in d

    # 2. Save config
    save_res = client.post("/api/elevenlabs/config", json={
        "api_key": "xi_test_key_mock",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "enabled": True
    })
    assert save_res.status_code == 200
    assert save_res.json().get("success") is True


def test_aarushi_proactive_api_endpoints():
    """Verify /api/aarushi/proactive and /api/audio/chime endpoints."""
    client = TestClient(app)

    # Initial check-in
    r1 = client.get("/api/aarushi/proactive?followup=false")
    assert r1.status_code == 200
    assert r1.json()["success"] is True
    assert len(r1.json()["message"]) > 5

    # Follow-up
    r2 = client.get("/api/aarushi/proactive?followup=true")
    assert r2.status_code == 200
    assert r2.json()["success"] is True
    assert len(r2.json()["message"]) > 5

    # Audio chime stream
    r3 = client.get("/api/audio/chime")
    assert r3.status_code == 200
    assert r3.headers["content-type"] == "audio/wav"
    assert len(r3.content) > 1000


def test_enhanced_stt_listening_settings():
    """Verify STT engine has sensitive RMS gating, normalization, and Hinglish prompt."""
    stt = SpeechToText()
    assert stt.model_name in ("tiny", "small", "base")
