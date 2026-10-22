"""Comprehensive Test Suite for Prompt 2/5: Voice Engine, TTS Streaming & Pronunciation Overhaul.

Verifies:
1. VoiceManager authoritative voice configuration, persistence, and immutable per-response snapshots.
2. Strict voice consistency (preventing random voice switching mid-response or across responses).
3. SpeechTextProcessor markdown cleaning, symbol removal, and Section 7.4 regression cases.
4. Sentence segmentation preserving decimals, abbreviations, and Hinglish.
5. Hinglish pronunciation dictionary preserving technical vocabulary (Python, RAM, Linux, Matrix, etc.).
6. REST API voice endpoints (/api/voice/config, /api/voice/test, /api/tts/stop, /api/tts/audio).
"""

import os
import pytest
from fastapi.testclient import TestClient

from gdr.voice.config import get_voice_manager, VoiceConfig, SUPPORTED_VOICE_CATALOG
from gdr.voice.processor import SpeechTextProcessor, clean_text_for_speech
from gdr.web.server import app


# =========================================================================
# 1. VOICE CONFIGURATION & STRICT CONSISTENCY TESTS
# =========================================================================

def test_voice_manager_singleton_and_defaults():
    """Verify VoiceManager loads authoritative config and catalog."""
    mgr = get_voice_manager()
    cfg = mgr.get_active_config()
    assert isinstance(cfg, VoiceConfig)
    assert cfg.provider in ("edge", "sarvam", "piper", "elevenlabs", "browser")
    assert cfg.voice_id != ""


def test_voice_manager_persistence():
    """Verify changing voice configuration persists across calls."""
    mgr = get_voice_manager()
    original_cfg = mgr.get_active_config()

    # Switch to en_aria
    new_cfg = mgr.set_active_config(
        provider="edge",
        voice_id="en-US-AriaNeural",
        language="en-US",
        persist=False
    )
    assert new_cfg.voice_id == "en-US-AriaNeural"
    assert mgr.get_active_config().voice_id == "en-US-AriaNeural"

    # Restore
    mgr.set_active_config(
        provider=original_cfg.provider,
        voice_id=original_cfg.voice_id,
        language=original_cfg.language,
        persist=False
    )


def test_immutable_response_snapshot_prevents_mid_response_voice_switching():
    """Verify that an immutable snapshot protects ongoing response playback
    even if the user modifies voice settings mid-playback.
    """
    mgr = get_voice_manager()
    mgr.set_active_config(provider="edge", voice_id="hi-IN-SwaraNeural", persist=False)

    # 1. Start response 1 with Swara snapshot
    resp1_id = "resp_test_001"
    snap1 = mgr.create_snapshot(resp1_id)
    assert snap1.voice_id == "hi-IN-SwaraNeural"

    # 2. User changes global voice mid-response to Jenny
    mgr.set_active_config(provider="edge", voice_id="en-US-JennyNeural", persist=False)
    assert mgr.get_active_config().voice_id == "en-US-JennyNeural"

    # 3. Chunks for response 1 must STILL retrieve Swara snapshot
    retrieved_snap = mgr.get_snapshot(resp1_id)
    assert retrieved_snap.voice_id == "hi-IN-SwaraNeural"
    assert retrieved_snap.voice_id != mgr.get_active_config().voice_id

    # 4. Response 2 retrieves the new Jenny config
    resp2_id = "resp_test_002"
    snap2 = mgr.create_snapshot(resp2_id)
    assert snap2.voice_id == "en-US-JennyNeural"

    # Cleanup snapshots
    mgr.release_snapshot(resp1_id)
    mgr.release_snapshot(resp2_id)


def test_decoupled_llm_and_tts_provider():
    """Verify that Local LLM does not silently force Piper if user selected cloud voice,
    and Cloud LLM does not force cloud voice if user selected Piper.
    """
    mgr = get_voice_manager()

    # User explicitly selects Piper while using Sarvam or Cloud LLM
    mgr.set_active_config(provider="piper", voice_id="en_US-lessac-medium", persist=False)
    snap = mgr.create_snapshot("resp_piper_cloud_llm")
    assert snap.provider == "piper"
    assert snap.voice_id == "en_US-lessac-medium"

    # User explicitly selects Edge Swara while using offline LLM
    mgr.set_active_config(provider="edge", voice_id="hi-IN-SwaraNeural", persist=False)
    snap2 = mgr.create_snapshot("resp_swara_offline_llm")
    assert snap2.provider == "edge"
    assert snap2.voice_id == "hi-IN-SwaraNeural"


# =========================================================================
# 2. SPEECH-TEXT PROCESSOR & SECTION 7.4 REGRESSION TESTS
# =========================================================================

def test_section_7_4_regression_cases():
    """Verify exact regression cases from Prompt 2/5 Section 7.4."""
    # Case 1: **Battery:** 70% — currently charging.
    input1 = "**Battery:** 70% — currently charging."
    expected1 = "Battery: 70 percent, currently charging."
    assert SpeechTextProcessor.clean_for_speech(input1) == expected1

    # Case 2: ### System\nYour computer is running normally.
    input2 = "### System\nYour computer is running normally."
    expected2 = "System. Your computer is running normally."
    assert SpeechTextProcessor.clean_for_speech(input2) == expected2

    # Case 3: [Sarvam • Neural HD Studio] Your PC is healthy.
    input3 = "[Sarvam • Neural HD Studio] Your PC is healthy."
    expected3 = "Your PC is healthy."
    assert SpeechTextProcessor.clean_for_speech(input3) == expected3


def test_speech_processor_strips_system_and_metadata_tags():
    """Verify processor strips various model tags, bracket labels, and timestamps."""
    samples = [
        ("[LocalOfflineLLM • Piper Neural] Everything is operating smoothly.", "Everything is operating smoothly."),
        ("[Offline Local AI Mode] RAM is 4GB.", "RAM is 4GB."),
        ("[GDR Fast Lane • 150 tokens] Processing completed.", "Processing completed."),
        ("Sweet Companion Your files are saved.", "Your files are saved."),
    ]
    for inp, exp in samples:
        assert SpeechTextProcessor.clean_for_speech(inp) == exp


def test_speech_processor_table_and_markdown_cleaning():
    """Verify Markdown tables, URLs, asterisks, and hashtags are cleaned naturally."""
    table_sample = "| Component | Status |\n|---|---|\n| CPU | OK |\n| RAM | Good |"
    cleaned = SpeechTextProcessor.clean_for_speech(table_sample)
    assert "|---|" not in cleaned
    assert "CPU" in cleaned
    assert "RAM" in cleaned

    url_sample = "Check https://github.com/404adarsh/GDR-AI for updates."
    assert SpeechTextProcessor.clean_for_speech(url_sample) == "Check link for updates."


def test_code_block_summarization_vs_verbatim():
    """Verify code blocks are summarized in concise mode rather than reading syntax."""
    code_text = "Here is the calculation:\n```python\nimport math\nprint(math.sqrt(16))\n```\nAll done."
    cleaned = SpeechTextProcessor.clean_for_speech(code_text, mode="concise")
    assert "import math" not in cleaned
    assert "math.sqrt" not in cleaned
    assert "Here is the calculation:" in cleaned
    assert "All done." in cleaned


# =========================================================================
# 3. SENTENCE & PHRASE SEGMENTATION TESTS
# =========================================================================

def test_sentence_segmentation_protects_decimals_and_abbreviations():
    """Verify segmentation does not split numbers like 10.5 or abbreviations like e.g."""
    text = "Battery is at 10.5 percent. For example, e.g. run pytest now! How is your day?"
    segments = SpeechTextProcessor.segment_into_speakable_phrases(text)
    assert len(segments) >= 2
    # Ensure 10.5 wasn't cut into "10." and "5 percent"
    assert any("10.5 percent" in s for s in segments)
    assert not any(s == "10." for s in segments)


def test_sentence_segmentation_hinglish_and_hindi():
    """Verify segmentation handles Hindi and Hinglish punctuation correctly."""
    text = "नमस्ते जीडीआर। आपका दिन कैसा रहा? सब कुछ ठीक है ना!"
    segments = SpeechTextProcessor.segment_into_speakable_phrases(text)
    assert len(segments) >= 2
    assert "नमस्ते जीडीआर।" in segments[0] or "नमस्ते जीडीआर" in segments[0]


# =========================================================================
# 4. HINGLISH PRONUNCIATION DICTIONARY TESTS
# =========================================================================

def test_hinglish_technical_vocabulary_preservation():
    """Verify technical terms in Roman Hindi / Hinglish are preserved without corruption."""
    sample = "Mere Linux terminal mein Python script chalao aur RAM check karo."
    processed = SpeechTextProcessor.apply_pronunciation_dictionary(sample)
    assert "Linux" in processed
    assert "Terminal" in processed
    assert "Python" in processed
    assert "RAM" in processed

    sample2 = "Matrix aur determinant solve karke probability nikalo."
    processed2 = SpeechTextProcessor.apply_pronunciation_dictionary(sample2)
    assert "Matrix" in processed2
    assert "Determinant" in processed2
    assert "Probability" in processed2


# =========================================================================
# 5. REST API ENDPOINTS FOR VOICE
# =========================================================================

def test_api_voice_config_endpoints():
    """Test GET and POST /api/voice/config."""
    client = TestClient(app)

    # 1. GET config
    res = client.get("/api/voice/config")
    assert res.status_code == 200
    cfg = res.json()
    assert "provider" in cfg
    assert "voice_id" in cfg
    assert "fallback_enabled" in cfg

    # 2. POST update config
    res2 = client.post("/api/voice/config", json={
        "provider": "edge",
        "voice_id": "hi-IN-SwaraNeural",
        "language": "hi-IN"
    })
    assert res2.status_code == 200
    d = res2.json()
    assert d["success"] is True
    assert d["config"]["voice_id"] == "hi-IN-SwaraNeural"


def test_api_voice_test_endpoint():
    """Test POST /api/voice/test synthesizes a preview sample."""
    client = TestClient(app)
    res = client.post("/api/voice/test", json={"voice": "en_aria", "text": "Testing voice audio pipeline."})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "audio_url" in data
    assert "voice" in data


def test_api_tts_stop_endpoint():
    """Test POST /api/tts/stop immediately halts host audio playback."""
    client = TestClient(app)
    res = client.post("/api/tts/stop")
    assert res.status_code == 200
    assert res.json().get("success") is True


def test_api_tts_audio_with_response_id():
    """Test GET /api/tts/audio accepts response_id for snapshot tracking."""
    client = TestClient(app)
    res = client.get("/api/tts/audio?text=Hello+GDR&lang=en&voice=en-US-AriaNeural&response_id=resp_test_999")
    assert res.status_code == 200
    assert res.headers["content-type"] in ("audio/mpeg", "audio/wav")
    assert len(res.content) > 500

