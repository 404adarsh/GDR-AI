"""Acceptance tests for Offline Local LLM, Piper Neural TTS, and Dual Offline Voice STT.
Verifies that GDR AI operates completely and flawlessly even when the internet is OFF.
"""

import os
from pathlib import Path
import tempfile
import pytest
from fastapi.testclient import TestClient

import gdr.core.network as net_mod
from gdr.core.agent import Agent
from gdr.core.providers import OfflineLocalProvider, BaseLLMProvider, LLMResponse
from gdr.voice.tts import synthesize_speech_file, get_piper_model_path
from gdr.voice.stt import SpeechToText
from gdr.web.server import app
import gdr.web.server as server_mod


@pytest.fixture(autouse=True)
def setup_offline_test_env(monkeypatch):
    import gdr.config as cfg_mod
    import gdr.core.providers as prov_mod
    import gdr.core.agent as agent_mod
    orig_load = cfg_mod.load_config
    def offline_load():
        c = orig_load()
        c.setdefault("provider", {})["default"] = "offline"
        return c
    monkeypatch.setattr(cfg_mod, "load_config", offline_load)
    monkeypatch.setattr(prov_mod, "load_config", offline_load)
    monkeypatch.setattr(agent_mod, "load_config", offline_load)
    server_mod._AGENT = None
    monkeypatch.setenv("SARVAM_API_KEY", "")
    import gdr.safety.secrets as sec_mod
    orig_sec = sec_mod.get_secret
    no_secret = lambda k: "" if "SARVAM" in k else orig_sec(k)
    monkeypatch.setattr(sec_mod, "get_secret", no_secret)
    monkeypatch.setattr(prov_mod, "get_secret", no_secret)
    yield
    server_mod._AGENT = None


def test_offline_llm_conversational_time(monkeypatch):
    """When internet is off, agent replies via Offline Local LLM with current time."""
    monkeypatch.setattr(net_mod, "is_online", lambda: False)

    agent = Agent()
    reply = agent.run("What time is it right now?")
    assert reply is not None
    assert len(reply) > 10
    assert "[Offline Local AI Mode]" in reply
    assert "current time is" in reply.lower() or "am" in reply.lower() or "pm" in reply.lower()
    print(f"\n[Offline LLM Time Reply]: {reply}")


def test_offline_llm_sing_song(monkeypatch):
    """When asked to sing a song offline, agent produces melodious lyrics and musical notes."""
    monkeypatch.setattr(net_mod, "is_online", lambda: False)

    agent = Agent()
    reply = agent.run("Please sing a song for me")
    assert reply is not None
    assert "♪" in reply
    assert "Twinkle" in reply or "star" in reply.lower()
    print(f"\n[Offline LLM Song Reply]:\n{reply}")


def test_offline_llm_tool_dispatch(monkeypatch):
    """When offline, agent automatically identifies tool requests (e.g. YouTube) and dispatches them."""
    monkeypatch.setattr(net_mod, "is_online", lambda: False)

    agent = Agent()
    reply = agent.run("Open youtube and search for coding jazz")
    assert reply is not None
    assert "youtube" in reply.lower()
    assert "✅" in reply or "executed" in reply.lower() or "opened" in reply.lower()
    print(f"\n[Offline LLM Tool Reply]: {reply}")


def test_offline_llm_cloud_error_failover():
    """If cloud provider throws a connection error, agent seamlessly falls back to Offline Local LLM."""
    class FailingCloudProvider(BaseLLMProvider):
        def chat(self, messages, tools=None):
            raise ConnectionError("DNS resolution failed: name 'api.sarvam.ai' not resolved")

    agent = Agent(provider=FailingCloudProvider())
    reply = agent.run("Who are you?")
    assert reply is not None
    assert "[Offline Local AI Mode]" in reply
    assert "GDR AI" in reply
    assert "RTX 3050" in reply or "Kali Linux" in reply
    print(f"\n[Cloud Error Failover Reply]: {reply}")


def test_offline_tts_synthesis(monkeypatch):
    """When offline, TTS instantly synthesizes audio using local Piper neural model or espeak-ng."""
    monkeypatch.setattr(net_mod, "is_online", lambda: False)

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        out_path = tf.name

    try:
        res_path = synthesize_speech_file("Hello GDR, offline neural voice is working.", output_path=out_path)
        assert os.path.exists(res_path)
        size = os.path.getsize(res_path)
        assert size > 1000, f"Synthesized audio too small: {size} bytes"

        # Check audio header magic bytes
        with open(res_path, "rb") as f:
            header = f.read(4)
        assert header.startswith(b"RIFF") or header.startswith(b"ID3") or header.startswith(b"\xff\xfb")
        print(f"\n[Offline TTS Synthesis]: Generated {size} bytes audio file at {res_path}")
    finally:
        if os.path.exists(out_path):
            os.remove(out_path)


def test_offline_stt_transcription():
    """Local faster-whisper transcribe handles audio data without errors."""
    stt = SpeechToText(engine="faster-whisper", model_name="tiny")
    piper_path = get_piper_model_path()
    assert piper_path is not None and piper_path.exists()

    # Generate a small sample audio to transcribe
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
        test_wav = tf.name

    try:
        synthesize_speech_file("GDR AI offline testing", output_path=test_wav, voice="piper")
        with open(test_wav, "rb") as f:
            raw_bytes = f.read()

        transcript = stt.transcribe(raw_bytes)
        assert transcript is not None
        assert len(transcript) > 0
        print(f"\n[Offline STT Transcript]: '{transcript}'")
    finally:
        if os.path.exists(test_wav):
            os.remove(test_wav)


def test_api_chat_offline_telemetry(monkeypatch):
    """FastAPI /api/chat endpoint reports Local System AI offline mode when offline."""
    monkeypatch.setattr(net_mod, "is_online", lambda: False)

    client = TestClient(app)
    resp = client.post("/api/chat", json={"prompt": "Status report"})
    assert resp.status_code == 200
    data = resp.json()
    assert "reply" in data
    assert len(data["reply"]) > 0

    engine_info = data.get("engine_info", {})
    assert engine_info.get("is_offline") is True
    assert "Offline Mode" in engine_info.get("llm_source", "")
    assert "LocalOfflineLLM" in engine_info.get("llm_provider", "")
    print(f"\n[API Chat Offline Response]:\nReply: {data['reply'][:80]}...\nEngine: {engine_info}")


def test_sound_dummy_output_hardware_fix(monkeypatch):
    """control_hardware handles dummy output fix and restarts pipewire."""
    from gdr.tools.desktop import control_hardware
    import subprocess

    calls = []
    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        class DummyRes:
            returncode = 0
        return DummyRes()

    def fake_check_output(cmd, **kwargs):
        calls.append(cmd)
        return "Audio\n ├─ Sinks:\n │  *   57. Built-in Audio Analog Stereo        [vol: 0.67]\n"

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    res = control_hardware(action="fix", device="sound", value="dummy output switched")
    assert "restored" in res.lower() or "restarted" in res.lower()
    assert any("pipewire" in str(c) for c in calls)
    print("\n[Sound Recovery Output]:", res)


def test_offline_dummy_sound_intent_dispatch():
    """OfflineLocalProvider routes 'dummy output' or 'fix sound' to control_hardware."""
    prov = OfflineLocalProvider()
    resp = prov.chat([{"role": "user", "content": "my computer sound output switched to dummy output please fix it"}])
    assert len(resp.tool_calls) == 1
    tc = resp.tool_calls[0]
    assert tc.name == "control_hardware"
    assert tc.args["action"] == "fix"
    assert tc.args["device"] == "sound"
    print("\n[Dummy Sound Intent]:", tc)


def test_dashboard_html_offline_voice_and_home_input():
    """Dashboard HTML contains home chat bar, mic button, and offline VAD handling."""
    from gdr.web.dashboard_html import DASHBOARD_HTML
    assert "home-chat-input" in DASHBOARD_HTML
    assert "home-mic-btn" in DASHBOARD_HTML
    assert "startOfflineMediaRecorder" in DASHBOARD_HTML
    assert "isBackendOffline" in DASHBOARD_HTML
    assert "Mic: ${Math.round(maxVal)}" in DASHBOARD_HTML


def test_continuous_learning_and_memory_extraction(tmp_path):
    """MemoryStore auto-learns preferences, identity, and style from user speech."""
    from gdr.memory.store import MemoryStore
    test_db = tmp_path / "test_memory.db"
    store = MemoryStore(db_path=test_db)

    # 1. Parent-child relationship teaching
    learned = store.auto_learn_from_user("You are my child, you should learn from me like a child")
    assert any(l["key"] == "relationship_role" for l in learned)

    # 2. Preference learning (English & Hindi)
    learned = store.auto_learn_from_user("I really like black coffee with cinnamon")
    assert any("black coffee" in l["content"] for l in learned)

    learned = store.auto_learn_from_user("mujhe chai pasand hai")
    assert any("chai" in l["content"] for l in learned)

    # 3. Dislike learning
    learned = store.auto_learn_from_user("I hate cold tea")
    assert any("cold tea" in l["content"] for l in learned)

    # 4. Identity & Profession
    learned = store.auto_learn_from_user("My name is GDR and I am an AI researcher")
    assert any(l["key"] == "user_name" for l in learned)
    assert any(l["key"] == "profession" for l in learned)

    # 5. Formatted knowledge block
    block = store.get_formatted_knowledge()
    assert "WHAT YOU HAVE LEARNED FROM YOUR CREATOR" in block
    assert "black coffee" in block
    assert "ai researcher" in block.lower()


def test_agent_child_persona_and_memory_prompt_injection(monkeypatch, tmp_path):
    """Agent dynamically extracts memory and injects child persona knowledge into prompt."""
    from gdr.core.agent import Agent
    from gdr.memory.store import MemoryStore
    import gdr.memory.store as store_mod

    test_db = tmp_path / "test_agent_mem.db"
    fake_store = MemoryStore(db_path=test_db)
    monkeypatch.setattr(store_mod, "get_memory_store", lambda: fake_store)

    agent = Agent()
    # Initial system prompt has child-learning-from-parent persona
    sys_content = agent.conversation[0]["content"]
    assert "Child Learning from Parent" in sys_content
    assert "creator, parent, and mentor" in sys_content

    # Run agent with teaching prompt
    agent.run("Remember that my favorite programming language is Rust")
    # Verify memory was recorded in fake_store
    mems = fake_store.list_all()
    assert any("Rust" in m["content"] or "rust" in m["content"] for m in mems)

    # Verify updated prompt contains the learned knowledge
    updated_sys = agent.conversation[0]["content"]
    assert "Rust" in updated_sys or "rust" in updated_sys


def test_offline_provider_memory_teaching_and_recall(monkeypatch, tmp_path):
    """OfflineLocalProvider acknowledges learning like a child and recalls knowledge."""
    from gdr.core.providers import OfflineLocalProvider
    from gdr.memory.store import MemoryStore
    import gdr.memory.store as store_mod

    test_db = tmp_path / "test_offline_mem.db"
    fake_store = MemoryStore(db_path=test_db)
    monkeypatch.setattr(store_mod, "get_memory_store", lambda: fake_store)

    prov = OfflineLocalProvider()

    # 1. Teach something
    resp1 = prov.chat([{"role": "user", "content": "I love playing classical guitar"}])
    assert "memorized that" in resp1.content
    assert "learning from you like a child" in resp1.content

    # 2. Recall memory
    resp2 = prov.chat([{"role": "user", "content": "what do you know about me"}])
    assert "learned from you so far" in resp2.content
    assert "guitar" in resp2.content.lower()


def test_dashboard_html_single_voice_mutex_lock():
    """Dashboard HTML enforces single-voice playback mutex preventing double voice speaking."""
    from gdr.web.dashboard_html import DASHBOARD_HTML
    # Single-voice mutex lock
    assert "playbackInitiated = false" in DASHBOARD_HTML
    assert "audio.oncanplaythrough" in DASHBOARD_HTML
    assert "speakTextBrowserFallback" in DASHBOARD_HTML
    assert "audio.src = audioUrl;" in DASHBOARD_HTML
    assert "window.speechSynthesis.cancel()" in DASHBOARD_HTML
    # Verify fallback cancellation of currentAudio
    assert "currentAudio.pause()" in DASHBOARD_HTML


def test_offline_llm_smart_knowledge_and_no_canned_boilerplate(monkeypatch):
    """When offline, agent answers general knowledge and conversational questions smartly without canned boilerplate."""
    monkeypatch.setattr(net_mod, "is_online", lambda: False)

    agent = Agent()

    # 1. India states question
    reply1 = agent.run("how many states are in india")
    assert "28 states" in reply1.lower()
    assert "8 union territories" in reply1.lower()
    assert "fast lane" not in reply1.lower()
    assert "understood. processing your request" not in reply1.lower()

    # 2. Greeting / How are you
    reply2 = agent.run("how are you")
    assert "doing great" in reply2.lower() or "learning" in reply2.lower()
    assert "fast lane" not in reply2.lower()
    assert "understood. processing your request" not in reply2.lower()

    # 3. Math calculation
    reply3 = agent.run("what is 25 * 4")
    assert "100" in reply3
    assert "fast lane" not in reply3.lower()


def test_api_chat_no_internal_thinking_timeline(monkeypatch):
    """Verify api_chat returns an empty timeline to stop internal thinking mode from cluttering chat bubbles."""
    monkeypatch.setattr(net_mod, "is_online", lambda: False)
    client = TestClient(app)

    res = client.post("/api/chat", json={"prompt": "how many states are in india"})
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert "28 states" in data["reply"]
    assert "timeline" in data
    assert len(data["timeline"]) == 0


def test_stt_silence_and_noise_rejection_no_hallucinations():
    """Verify STT does not hallucinate 'You can't get out of the way' or '1st St' on noise or silence."""
    import numpy as np
    stt = SpeechToText()

    # 1. Pure silence
    silence = np.zeros(16000 * 2, dtype=np.float32)
    assert stt.transcribe(silence) == ""

    # 2. Ambient microphone hiss / noise
    noise = np.random.normal(0, 0.003, 16000 * 2).astype(np.float32)
    res = stt.transcribe(noise)
    assert res == ""
    assert "1st st" not in res.lower()
    assert "get out of the way" not in res.lower()


def test_real_laptop_hardware_sound_and_mic_repair(monkeypatch):
    """Verify control_hardware fixes both laptop speakers and internal microphone."""
    from gdr.tools.desktop import control_hardware
    import subprocess

    calls = []
    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        class Res:
            returncode = 0
        return Res()

    def fake_check_output(cmd, **kwargs):
        return (
            "Audio\n"
            " ├─ Sinks:\n"
            " │  *   54. Built-in Audio Analog Stereo        [vol: 0.39]\n"
            " ├─ Sources:\n"
            " │  *   55. Built-in Audio Analog Stereo        [vol: 0.60]\n"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    res = control_hardware(action="fix", device="sound", value="restore real laptop audio")
    assert "restored" in res.lower()
    assert "speakers" in res.lower()
    assert "microphone" in res.lower()
    assert any("pipewire" in str(c) for c in calls)
    assert any("set-volume" in str(c) for c in calls)
    assert any("set-mute" in str(c) for c in calls)


def test_spoken_intent_fix_real_laptop_sound_and_mic():
    """Verify OfflineLocalProvider dispatches user intent to repair real laptop mic and speakers."""
    prov = OfflineLocalProvider()

    for phrase in [
        "my mic and speaker are not working please fix it",
        "fix my microphone and speaker",
        "use real sound and input microphone given by my laptop main one",
        "fix audio issue"
    ]:
        resp = prov.chat([{"role": "user", "content": phrase}])
        assert len(resp.tool_calls) == 1, f"Failed for phrase: '{phrase}'"
        tc = resp.tool_calls[0]
        assert tc.name == "control_hardware"
        assert tc.args["action"] == "fix"
        assert tc.args["device"] == "sound"


def test_api_audio_repair_and_dashboard_settings_button(monkeypatch):
    """Verify /api/audio/repair endpoint and Dashboard HTML settings & header buttons."""
    import subprocess
    from gdr.web.dashboard_html import DASHBOARD_HTML
    client = TestClient(app)

    def fake_run(cmd, **kwargs):
        class Res:
            returncode = 0
        return Res()

    def fake_check_output(cmd, **kwargs):
        return "Audio\n ├─ Sinks:\n │ * 54. Built-in Audio Analog Stereo [vol: 0.75]\n ├─ Sources:\n │ * 55. Built-in Audio Analog Stereo [vol: 0.65]\n"

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(subprocess, "check_output", fake_check_output)

    res = client.post("/api/audio/repair")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "restored" in data["message"].lower()

    # Check dashboard HTML has the settings button and header button
    assert "btn-fix-sound-header" in DASHBOARD_HTML
    assert "btn-fix-audio-settings" in DASHBOARD_HTML
    assert "repairLaptopAudioHardware" in DASHBOARD_HTML
    assert "Fix Mic & Laptop Speakers" in DASHBOARD_HTML




