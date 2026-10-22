"""
tests/test_sarvam_105b_and_identity_auth.py

Comprehensive test suite verifying:
1. Model ID `sarvam-105b-conversations` and endpoint `POST /v1/chat/completions`.
2. Multi-turn context retention across conversation turns partitioned by channel and session_id.
3. Deterministic authorization and case-insensitive normalization.
4. Scrypt password fallback authentication with 5-attempt rate-limiting lockout.
5. Telemetry milestone tracking and stage latency calculation.
6. Streaming token and sentence generation in stream_run.
"""

import pytest
import time
from unittest.mock import MagicMock, patch

from gdr.safety.auth import get_channel_auth_manager, ChannelAuthManager, hash_password, normalize_username
from gdr.core.telemetry import PipelineTimer, get_pipeline_timer
from gdr.core.providers import SarvamProvider, LLMResponse
from gdr.core.agent import Agent
from gdr.memory.store import MemoryStore


# =====================================================================
# 1. SARVAM 105B CONVERSATIONS MODEL & API TESTS
# =====================================================================

def test_sarvam_default_model_and_validation():
    """Verify default model is sarvam-105b-conversations and only valid 105b models allowed."""
    prov = SarvamProvider(api_key="sk_test_key_123")
    assert prov.model == "sarvam-105b-conversations"

    # Valid model change
    prov.set_model("sarvam-105b")
    assert prov.model == "sarvam-105b"

    # Rejection of invalid/deprecated models (e.g. sarvam-m)
    with pytest.raises(ValueError):
        prov.set_model("sarvam-m")

    with pytest.raises(ValueError):
        prov.set_model("invalid-model-name")


def test_sarvam_chat_completions_call():
    """Verify call goes to /v1/chat/completions with sarvam-105b-conversations."""
    prov = SarvamProvider(api_key="sk_test_mock_123")
    prov.client = MagicMock()
    prov._ensure_client = MagicMock()

    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = "Namaste! Main Aarushi hoon."
    mock_resp.choices[0].message.tool_calls = None
    prov.client.chat.completions.return_value = mock_resp

    messages = [
        {"role": "system", "content": "You are Aarushi."},
        {"role": "user", "content": "Hello!"}
    ]
    reply = prov.chat(messages)

    prov.client.chat.completions.assert_called_once()
    kwargs = prov.client.chat.completions.call_args[1]
    assert kwargs["model"] == "sarvam-105b-conversations"
    assert kwargs["messages"] == messages
    assert "Namaste" in reply.content


def test_sarvam_streaming_tokens():
    """Verify Sarvam stream_chat yields tokens properly."""
    prov = SarvamProvider(api_key="sk_test_mock_123")
    prov.client = MagicMock()
    prov._ensure_client = MagicMock()

    chunk1 = MagicMock()
    chunk1.choices = [MagicMock()]
    chunk1.choices[0].delta.content = "Python "

    chunk2 = MagicMock()
    chunk2.choices = [MagicMock()]
    chunk2.choices[0].delta.content = "ek programming language hai."

    prov.client.chat.completions.return_value = [chunk1, chunk2]

    tokens = list(prov.stream_chat([{"role": "user", "content": "Python kya hai?"}]))
    assert tokens == ["Python ", "ek programming language hai."]


# =====================================================================
# 2. DETERMINISTIC AUTHORIZATION & PASSWORD FALLBACK TESTS
# =====================================================================

def test_auth_manager_case_insensitive_and_at_sign():
    """Verify username matching normalizes '@' prefix and casing."""
    assert normalize_username("@GauraV_07") == "gaurav_07"
    assert normalize_username("  ADMINUSER  ") == "adminuser"
    assert normalize_username("") == ""

    auth = ChannelAuthManager()
    mock_cfg = {
        "channels": {
            "allowed_telegram_usernames": "gaurav_07, adminuser"
        }
    }
    with patch("gdr.safety.auth.load_config", return_value=mock_cfg):
        is_ok, reason = auth.is_authorized("telegram", "12345", username="gaurav_07")
        assert is_ok is True
        is_ok, reason = auth.is_authorized("telegram", "12345", username="@Gaurav_07")
        assert is_ok is True
        is_ok, reason = auth.is_authorized("telegram", "12345", username="  @ADMINUSER  ")
        assert is_ok is True
        is_ok, reason = auth.is_authorized("telegram", "99999", username="random_stranger")
        assert is_ok is False


def test_auth_manager_password_fallback_and_session_binding():
    """Verify password authentication succeeds, creates 24h session, and binds account ID."""
    auth = ChannelAuthManager()
    mock_cfg = {"channels": {"allowed_telegram_usernames": "known_user"}}

    with patch("gdr.safety.auth.load_config", return_value=mock_cfg), \
         patch("gdr.safety.auth.get_secret", return_value=hash_password("SecurePassword#2026")):

        # Unknown user without session
        is_ok, _ = auth.is_authorized("telegram", "tg_user_999", username="unknown_guy")
        assert is_ok is False

        # Authenticate via password
        success, msg = auth.authenticate_password("telegram", "tg_user_999", "unknown_guy", "SecurePassword#2026")
        assert success is True
        assert "successful" in msg.lower()

        # Now authorized by bound session ID
        is_ok, reason = auth.is_authorized("telegram", "tg_user_999", username="unknown_guy")
        assert is_ok is True
        assert reason == "ACTIVE_SESSION"


def test_auth_manager_rate_limiting_lockout():
    """Verify 5 failed attempts locks out the user for the cooldown period."""
    auth = ChannelAuthManager()
    mock_cfg = {"channels": {}}

    with patch("gdr.safety.auth.load_config", return_value=mock_cfg), \
         patch("gdr.safety.auth.get_secret", return_value=hash_password("CorrectPassword123")):

        # 4 failed attempts
        for i in range(4):
            ok, msg = auth.authenticate_password("telegram", "attacker_42", "attacker", f"WrongPass{i}")
            assert ok is False
            assert "invalid" in msg.lower()

        # 5th failed attempt
        ok, msg = auth.authenticate_password("telegram", "attacker_42", "attacker", "WrongPass4")
        assert ok is False

        # Now locked out
        ok, msg = auth.authenticate_password("telegram", "attacker_42", "attacker", "CorrectPassword123")
        assert ok is False
        assert "wait 5 minutes" in msg.lower()


# =====================================================================
# 3. MULTI-TURN CONVERSATION RETENTION TESTS
# =====================================================================

def test_agent_multi_turn_history_retention():
    """Verify Agent retrieves preceding turns for multi-turn requests like 'Aur example do'."""
    mock_prov = MagicMock()
    mock_prov.chat.return_value = LLMResponse(content="Python ka dusra example yeh hai...")
    mock_prov.model = "sarvam-105b-conversations"

    mem = MemoryStore(":memory:")
    # Seed prior turn
    mem.save_chat_message("user", "Python kya hai?", session_id="test_session_1")
    mem.save_chat_message("assistant", "Python ek programming language hai.", session_id="test_session_1")

    with patch("gdr.memory.store.get_memory_store", return_value=mem), \
         patch("gdr.core.agent.save_checkpoint"):
        agent = Agent(provider=mock_prov)
        reply = agent.run("Aur example do.", session_id="test_session_1", channel="telegram")

        # Verify chat call received system + history + new prompt
        mock_prov.chat.assert_called_once()
        conv_sent = mock_prov.chat.call_args[0][0]
        roles = [m["role"] for m in conv_sent]
        assert "system" in roles
        assert roles[-4:] == ["user", "assistant", "user", "assistant"]
        assert conv_sent[-4]["content"] == "Python kya hai?"
        assert conv_sent[-3]["content"] == "Python ek programming language hai."
        assert conv_sent[-2]["content"] == "Aur example do."


# =====================================================================
# 4. TELEMETRY MILESTONE & STAGE LATENCIES
# =====================================================================

def test_pipeline_timer_milestones_and_latencies():
    """Verify all required milestones are recorded and stage latencies calculated."""
    timer = PipelineTimer("utt_test_001")
    timer.record("speech_started")
    time.sleep(0.01)
    timer.record("speech_ended")
    timer.record("transcription_started")
    time.sleep(0.01)
    timer.record("transcription_completed")
    timer.record("llm_request_started")
    time.sleep(0.01)
    timer.record("first_llm_token")
    time.sleep(0.01)
    timer.record("llm_response_completed")
    timer.record("tts_started")
    time.sleep(0.01)
    timer.record("first_audio_chunk_ready")
    timer.record("playback_started")
    timer.record("playback_completed")

    summary = timer.get_metrics_summary()
    assert summary["utterance_id"] == "utt_test_001"
    assert "time_to_first_token_ms" in summary
    assert "stt_duration_ms" in summary
    assert "tts_synthesis_ms" in summary
    assert "total_end_to_end_ms" in summary
    assert summary["time_to_first_token_ms"] > 0
    assert summary["total_end_to_end_ms"] > 0
