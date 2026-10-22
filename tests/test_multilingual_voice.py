"""Multilingual Voice Engine Test Suite for GDR AI.
Validates language detection (Hindi/Hinglish/English), studio-grade neural synthesis,
voice profiles, and REST API audio endpoints.
"""

import os
import pytest
from fastapi.testclient import TestClient

from gdr.voice.tts import (
    detect_language,
    synthesize_speech_file,
    VOICE_PROFILES,
    TextToSpeech
)
from gdr.web.server import app


def test_language_detection_devanagari_hindi():
    """Verify Devanagari Hindi text is accurately detected as hi-IN."""
    text1 = "नमस्ते, आप कैसे हैं?"
    assert detect_language(text1) == "hi-IN"

    text2 = "आज का मौसम कैसा रहेगा?"
    assert detect_language(text2) == "hi-IN"

    text3 = "जीडीआर एआई हमेशा आपकी सेवा में तैयार है।"
    assert detect_language(text3) == "hi-IN"


def test_language_detection_hinglish():
    """Verify Latin-transliterated Hindi (Hinglish) is detected as hi-IN."""
    assert detect_language("kya haal hai bhai") == "hi-IN"
    assert detect_language("namaste jarvis kaise ho") == "hi-IN"
    assert detect_language("aaj ka mausam kaisa hai") == "hi-IN"
    assert detect_language("shukriya dost") == "hi-IN"


def test_language_detection_english():
    """Verify English text is detected as en-US."""
    assert detect_language("Hello Jarvis, what is the status of system?") == "en-US"
    assert detect_language("Open YouTube and search for tech news.") == "en-US"
    assert detect_language("Take a screenshot of the main monitor.") == "en-US"


def test_voice_profiles_schema():
    """Ensure all required voice profiles exist with valid engine and lang attributes."""
    expected_keys = ["hi_male", "hi_female", "en_male", "en_female", "en_indian", "piper_offline"]
    for k in expected_keys:
        assert k in VOICE_PROFILES
        profile = VOICE_PROFILES[k]
        assert "engine" in profile
        assert "voice" in profile
        assert "lang" in profile
        assert "label" in profile
        assert "description" in profile


def test_synthesis_file_generation_hindi(tmp_path):
    """Verify Hindi synthesis produces a valid non-empty audio file."""
    out_file = str(tmp_path / "hindi_speech.mp3")
    res = synthesize_speech_file(
        text="नमस्ते! यह एक परीक्षण संदेश है।",
        output_path=out_file,
        lang="hi"
    )
    assert os.path.exists(res)
    assert os.path.getsize(res) > 500


def test_synthesis_file_generation_english(tmp_path):
    """Verify English synthesis produces a valid non-empty audio file."""
    out_file = str(tmp_path / "english_speech.mp3")
    res = synthesize_speech_file(
        text="Hello, this is a studio quality voice test.",
        output_path=out_file,
        lang="en"
    )
    assert os.path.exists(res)
    assert os.path.getsize(res) > 500


def test_tts_api_voices_endpoint():
    """Test GET /api/tts/voices returns the registered voice profiles."""
    client = TestClient(app)
    res = client.get("/api/tts/voices")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 5
    labels = [p["label"] for p in data]
    assert any("Madhur" in l for l in labels)
    assert any("Guy" in l for l in labels)


def test_tts_api_audio_streaming():
    """Test GET /api/tts/audio streams audio data with correct media type."""
    client = TestClient(app)
    res = client.get("/api/tts/audio?text=नमस्ते+जीडीआर&lang=hi")
    assert res.status_code == 200
    assert res.headers["content-type"] in ("audio/mpeg", "audio/wav")
    assert len(res.content) > 500


def test_tts_api_speak_endpoint():
    """Test POST /api/tts/speak triggers audio synthesis."""
    client = TestClient(app)
    res = client.post("/api/tts/speak", json={"text": "System check OK.", "lang": "en"})
    assert res.status_code == 200
    d = res.json()
    assert d.get("success") is True or "spoken" in d


def test_engine_telemetry_reporting():
    """Verify engine and token transparency data in status and chat endpoints."""
    client = TestClient(app)
    res = client.get("/api/status")
    assert res.status_code == 200
    data = res.json()
    assert "engine_info" in data
    info = data["engine_info"]
    assert "llm_provider" in info
    assert "llm_source" in info
    assert "voice_source" in info


def test_expanded_voice_profiles_and_aliases():
    """Verify newly added studio profiles (Aria, Christopher, Ryan, Sonia, Neerja)."""
    assert "en_aria" in VOICE_PROFILES
    assert "en_christopher" in VOICE_PROFILES
    assert "en_ryan" in VOICE_PROFILES
    assert "en_sonia" in VOICE_PROFILES
    assert "en_neerja" in VOICE_PROFILES
    assert VOICE_PROFILES["en_ryan"]["voice"] == "en-GB-RyanNeural"


def test_song_and_musical_lyrics_cleaning():
    """Verify lyrics with musical notes (♪, ♫) and rhymes are cleaned without data corruption."""
    from gdr.voice.tts import clean_text_for_speech
    sample = "♪ Twinkle, twinkle, little star! ♫ How I wonder what you are!"
    cleaned = clean_text_for_speech(sample)
    assert "Twinkle, twinkle, little star" in cleaned
    assert "♪" not in cleaned
    assert "♫" not in cleaned


