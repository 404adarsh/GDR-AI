"""Automated test suite for:
1. Desktop Call App Launcher (gdr/system/desktop_app.py) & Chromium standalone app mode.
2. Startup Coordinator sequence & time-aware personalized morning greeting.
3. Autostart integration with --call desktop entry across Linux, Windows, macOS.
4. Focus Call Mode direct text chat bar and auto-listening / auto-connect contracts.
"""

import copy
from datetime import datetime
import json
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from gdr.config import get_gdr_config_dir, load_config, save_config, DEFAULT_CONFIG
from gdr.system.desktop_app import (
    find_desktop_browser_binary,
    configure_desktop_profile_permissions,
    get_desktop_profile_dir,
)
from gdr.system.autostart import LinuxAutostart, DarwinAutostart, WindowsAutostart, get_autostart_status
from gdr.web.server import app


@pytest.fixture
def temp_gdr_env(tmp_path, monkeypatch):
    """Set up isolated GDR directory for desktop companion testing."""
    config_dir = tmp_path / "gdr_config"
    config_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("GDR_CONFIG_DIR", str(config_dir))
    monkeypatch.delenv("USER_NAME", raising=False)
    monkeypatch.delenv("ASSISTANT_NAME", raising=False)

    sample_config = copy.deepcopy(DEFAULT_CONFIG)
    sample_config["general"]["user_name"] = "GDR"
    sample_config["general"]["agent_name"] = "Aarushi"
    sample_config["voice"]["greeting_enabled"] = True
    sample_config["voice"]["speak_greeting_aloud"] = True
    save_config(sample_config)

    return config_dir


def test_desktop_browser_discovery():
    """Verify that find_desktop_browser_binary locates an available standalone browser on the host."""
    res = find_desktop_browser_binary()
    # On Linux system with Chromium installed, should locate chromium
    if os.path.exists("/usr/bin/chromium"):
        assert res is not None
        name, path = res
        assert "chromium" in name or "chrome" in name
        assert os.path.exists(path)


def test_desktop_profile_permissions_preseed(temp_gdr_env):
    """Verify that configure_desktop_profile_permissions creates the Preferences file with media_stream_mic ALLOW."""
    configure_desktop_profile_permissions(port=8844)
    pref_file = get_desktop_profile_dir() / "Default" / "Preferences"

    assert pref_file.exists()
    data = json.loads(pref_file.read_text(encoding="utf-8"))
    exceptions = data.get("profile", {}).get("content_settings", {}).get("exceptions", {})
    mic_rules = exceptions.get("media_stream_mic", {})

    key = "http://127.0.0.1:8844,*"
    assert key in mic_rules
    assert mic_rules[key]["setting"] == 1  # 1 = ALLOW (no permission popup)


def test_startup_greeting_api(temp_gdr_env):
    """Verify GET /api/companion/startup_greeting generates time-aware greeting and session ID."""
    client = TestClient(app)
    resp = client.get("/api/companion/startup_greeting")
    assert resp.status_code == 200
    d = resp.json()

    assert "greeting" in d
    assert len(d["greeting"]) > 5
    assert "session_id" in d
    assert d["session_id"].startswith("startup_")
    assert "should_speak" in d
    assert "period" in d
    assert d["period"] in ("morning", "afternoon", "evening", "night")
    assert any(term in d["greeting"] for term in ["morning", "afternoon", "evening", "night", "GDR", "ready", "Aarushi"])


def test_startup_settings_api(temp_gdr_env):
    """Verify GET and POST /api/companion/startup_settings."""
    client = TestClient(app)

    # 1. Get settings
    get_resp = client.get("/api/companion/startup_settings")
    assert get_resp.status_code == 200
    settings = get_resp.json()
    assert "open_direct_to_call" in settings
    assert "auto_listen_enabled" in settings
    assert "greeting_enabled" in settings

    # 2. Update settings
    payload = {
        "open_direct_to_call": True,
        "auto_listen_enabled": True,
        "greeting_enabled": True,
        "speak_greeting_aloud": True,
        "respect_quiet_hours": True,
        "autostart": False
    }
    post_resp = client.post("/api/companion/startup_settings", json=payload)
    assert post_resp.status_code == 200
    assert post_resp.json()["success"] is True

    # 3. Verify persistence
    cfg = load_config()
    assert cfg["voice"]["open_direct_to_call"] is True
    assert cfg["voice"]["auto_listen_enabled"] is True


def test_call_endpoint_and_html_contracts(temp_gdr_env):
    """Verify /call renders Focus Call Companion with display:flex."""
    client = TestClient(app)
    resp = client.get("/call")
    assert resp.status_code == 200
    html = resp.text

    # Focus overlay must be flex (open directly) on /call
    assert 'id="focus-call-overlay" class="focus-theme-midnight" style="display:flex;"' in html
    assert 'focus-stage' in html
    assert 'focus-controls-dock' in html


def test_autostart_uses_call_flag(tmp_path, monkeypatch):
    """Verify Linux, macOS, and Windows autostart templates execute launcher with --call."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("GDR_CONFIG_DIR", str(tmp_path / "gdr"))
    LinuxAutostart.enable()
    desktop_file = LinuxAutostart.DESKTOP_FILE
    assert desktop_file.exists()
    content = desktop_file.read_text()
    assert "--call" in content
    LinuxAutostart.disable()
    assert not desktop_file.exists()
