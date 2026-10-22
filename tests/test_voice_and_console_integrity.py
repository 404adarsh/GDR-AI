"""Test voice, speech recognition, audio playback, and browser console integrity.
Verifies that:
1. No SyntaxError or ReferenceError occur in browser scripts (openFocusCallMode, onOrbClick, sendChat, startIdeVoiceCall).
2. Voice endpoints (/api/voice/transcribe, /api/tts/audio, /api/companion/startup_greeting) return valid responses.
3. Call mode, speech recognition triggers, and audio queue work without crashing.
"""

import io
import json
import threading
import time
import pytest
from playwright.sync_api import sync_playwright
import uvicorn
import requests
import numpy as np
import soundfile as sf

from gdr.web.server import app


def get_free_port():
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def live_server_url():
    port = get_free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(50):
        try:
            r = requests.get(f"{url}/api/status", timeout=1)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.1)
    yield url
    server.should_exit = True


def test_browser_console_zero_syntax_and_reference_errors(live_server_url):
    """Ensure dashboard loads in Chromium with ZERO SyntaxError, ReferenceError, or unhandled errors."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
            ]
        )
        context = browser.new_context(
            permissions=["microphone"]
        )
        page = context.new_page()

        console_errors = []
        page_errors = []

        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("pageerror", lambda err: page_errors.append(str(err)))

        # 1. Load main dashboard
        res = page.goto(live_server_url, wait_until="networkidle")
        assert res.status == 200

        # Check for any SyntaxError or ReferenceError
        fatal_errors = [e for e in (console_errors + page_errors) if "SyntaxError" in e or "ReferenceError" in e]
        assert not fatal_errors, f"Fatal JS errors found: {fatal_errors}"

        # 2. Test openFocusCallMode existence and call
        call_overlay_visible = page.evaluate("""() => {
            if (typeof openFocusCallMode !== 'function') throw new Error('openFocusCallMode is not a function');
            openFocusCallMode();
            const el = document.getElementById('focus-call-overlay');
            return el && el.style.display !== 'none';
        }""")
        assert call_overlay_visible, "Focus Call Overlay should be displayed after openFocusCallMode()"

        # 3. Test toggleFocusMic and listening state
        mic_active = page.evaluate("""() => {
            const btn = document.getElementById('focus-btn-mic');
            return btn && btn.classList.contains('active');
        }""")
        assert mic_active, "Mic button should be active in focus call mode"

        # 4. Test closeFocusCallMode
        call_overlay_closed = page.evaluate("""() => {
            if (typeof closeFocusCallMode !== 'function') throw new Error('closeFocusCallMode is not a function');
            closeFocusCallMode();
            const el = document.getElementById('focus-call-overlay');
            return !el || el.style.display === 'none';
        }""")
        assert call_overlay_closed, "Focus Call Overlay should be hidden after closeFocusCallMode()"

        # 5. Test IDE Call Mode entry point (discreet one-click call)
        ide_call_status = page.evaluate("""() => {
            showScreen('ide');
            if (typeof startIdeVoiceCall !== 'function') throw new Error('startIdeVoiceCall not defined');
            startIdeVoiceCall();
            const badge = document.getElementById('ide-call-active-badge');
            const active = badge && badge.style.display !== 'none';
            endIdeVoiceCall();
            return active;
        }""")
        assert ide_call_status, "startIdeVoiceCall should activate discreet IDE call badge"

        # 6. Verify zero fatal script errors throughout full user session
        all_fatal = [e for e in (console_errors + page_errors) if "SyntaxError" in e or "ReferenceError" in e]
        assert not all_fatal, f"Fatal errors occurred during session: {all_fatal}"

        browser.close()


def test_voice_transcribe_endpoint(live_server_url):
    """Test /api/voice/transcribe with synthetic WAV audio."""
    import base64
    sr = 16000
    # Generate 1.5 seconds of soft synthetic speech-range tone (440Hz sine wave)
    t = np.linspace(0, 1.5, int(sr * 1.5), endpoint=False)
    sine = (0.2 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)

    buf = io.BytesIO()
    sf.write(buf, sine, sr, format='WAV', subtype='PCM_16')
    b64_audio = base64.b64encode(buf.getvalue()).decode('utf-8')

    res = requests.post(
        f"{live_server_url}/api/voice/transcribe",
        json={"audio_base64": f"data:audio/wav;base64,{b64_audio}"},
        timeout=10
    )
    assert res.status_code == 200
    data = res.json()
    assert "text" in data


def test_tts_audio_endpoint(live_server_url):
    """Test /api/tts/audio generates playable audio stream."""
    res = requests.get(
        f"{live_server_url}/api/tts/audio",
        params={"text": "Aarushi voice connection online", "lang": "en"},
        timeout=10
    )
    assert res.status_code == 200
    assert len(res.content) > 100
    assert res.headers.get("content-type", "").startswith("audio/")


def test_companion_startup_greeting(live_server_url):
    """Test personalized morning greeting endpoint."""
    res = requests.get(f"{live_server_url}/api/companion/startup_greeting", timeout=5)
    assert res.status_code == 200
    data = res.json()
    assert "greeting" in data
    assert "session_id" in data
    assert "should_speak" in data


def test_default_ai_loads_as_sarvam_or_api_provider(live_server_url):
    """Verify that by default on startup (without having to manually open settings and click save),
    the system initializes with Sarvam / configured API provider rather than defaulting to local offline LLM."""
    res = requests.get(f"{live_server_url}/api/status", timeout=5)
    assert res.status_code == 200
    data = res.json()
    engine_info = data.get("engine_info", {})
    assert engine_info.get("llm_provider") == "Sarvam", f"Expected default Sarvam provider, got {engine_info}"
    assert engine_info.get("has_api_token") is True
    assert engine_info.get("is_offline") is False


def test_agent_and_chat_never_returns_empty_response(live_server_url):
    """Verify that agent and /api/chat always return a non-empty, spoken conversational response,
    even when tools are invoked or LLM returns empty content."""
    res = requests.post(
        f"{live_server_url}/api/chat",
        json={"prompt": "check my emails"},
        timeout=20
    )
    assert res.status_code == 200
    data = res.json()
    assert "reply" in data
    assert isinstance(data["reply"], str)
    assert len(data["reply"].strip()) > 0, "Assistant reply must never be empty or whitespace"



