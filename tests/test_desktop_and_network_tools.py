"""Tests for Desktop Integration, YouTube Launcher, Weather, Bookmarks, Ping, and Hardware Control.
"""

import json
from pathlib import Path
import unittest.mock as mock
import pytest

from gdr.tools.desktop import (
    desktop_open,
    open_youtube,
    search_youtube,
    get_weather,
    ping_host,
    test_website as run_website_test,
    bookmark_website,
    get_website,
    list_bookmarks,
    delete_bookmark,
    control_hardware,
    set_brightness,
    get_brightness,
    run_sudo,
)


def test_youtube_and_desktop_open():
    """Verify YouTube open and search commands construct correct desktop URLs."""
    with mock.patch("subprocess.Popen") as mock_popen:
        res1 = open_youtube()
        assert "Opened YouTube" in res1
        mock_popen.assert_called()

        res2 = search_youtube("lofi hip hop")
        assert "Searching YouTube for 'lofi hip hop'" in res2
        assert "results?search_query=lofi+hip+hop" in res2

        res3 = desktop_open("https://github.com")
        assert "Opened 'https://github.com'" in res3


def test_website_bookmarks_crud(tmp_path, monkeypatch):
    """Verify saving, getting, listing, and deleting website bookmarks."""
    bm_file = tmp_path / "bookmarks.json"
    monkeypatch.setattr("gdr.tools.desktop.BOOKMARKS_FILE", bm_file)
    monkeypatch.setattr("gdr.tools.desktop.CONFIG_DIR", tmp_path)

    # 1. Bookmark a website
    res1 = bookmark_website("portfolio", "https://myportfolio.dev", "My personal portfolio site")
    assert "portfolio" in res1
    assert bm_file.exists()

    # 2. List bookmarks
    list_res = list_bookmarks()
    assert "portfolio" in list_res
    assert "https://myportfolio.dev" in list_res

    # 3. Retrieve bookmark by name
    get_res = get_website("portfolio")
    assert "https://myportfolio.dev" in get_res
    assert "My personal portfolio site" in get_res

    # Substring retrieval
    get_sub = get_website("port")
    assert "https://myportfolio.dev" in get_sub

    # 4. Delete bookmark
    del_res = delete_bookmark("portfolio")
    assert "Deleted website bookmark 'portfolio'" in del_res

    # Verify gone
    list_after = list_bookmarks()
    assert "No website bookmarks saved yet" in list_after


def test_ping_host():
    """Verify ping_host on localhost and invalid hostname."""
    # Localhost ping should succeed
    res = ping_host("127.0.0.1", count=1)
    assert "127.0.0.1" in res
    assert "ONLINE" in res or "reachable" in res or "transmitted" in res

    # Invalid host
    res_bad = ping_host("invalid host with spaces!!!")
    assert "Invalid hostname" in res_bad


def test_test_website_diagnostics():
    """Verify website health test against a mocked HTTP response."""
    with mock.patch("requests.get") as mock_get:
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.reason = "OK"
        mock_resp.content = b"<html><title>Test Page</title><body>Hello</body></html>"
        mock_resp.headers = {
            "Server": "nginx/1.24",
            "Strict-Transport-Security": "max-age=31536000",
            "Content-Type": "text/html"
        }
        mock_get.return_value = mock_resp

        res = run_website_test("https://example.com", check_ssl=False)
        assert "HTTP Status: 🟢 200 OK" in res
        assert "Web Server: nginx/1.24" in res
        assert "Security Headers: HSTS" in res
        assert "HEALTHY & RESPONSIVE" in res


def test_get_weather():
    """Verify weather tool parsing from wttr.in JSON format."""
    mock_weather_json = {
        "current_condition": [{
            "temp_C": "26",
            "temp_F": "78",
            "FeelsLikeC": "27",
            "weatherDesc": [{"value": "Partly cloudy"}],
            "humidity": "55",
            "windspeedKmph": "12",
            "winddir16Point": "NW"
        }],
        "nearest_area": [{
            "areaName": [{"value": "New Delhi"}],
            "country": [{"value": "India"}]
        }],
        "weather": [{
            "maxtempC": "32",
            "mintempC": "21"
        }]
    }

    with mock.patch("requests.get") as mock_get:
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_weather_json
        mock_get.return_value = mock_resp

        res = get_weather("Delhi")
        assert "New Delhi, India" in res
        assert "26°C" in res
        assert "Partly cloudy" in res
        assert "Humidity: 55%" in res


def test_hardware_control_and_sudo():
    """Verify brightness, volume, hardware query, and sudo execution."""
    # Brightness get & set
    b_res = set_brightness(75)
    assert "75%" in b_res

    cur_b = get_brightness()
    assert "brightness" in cur_b.lower()

    # Hardware control routing
    vol_res = control_hardware(action="get", device="volume")
    assert "volume" in vol_res.lower() or "speaker" in vol_res.lower()

    bat_res = control_hardware(action="status", device="battery")
    assert "Battery" in bat_res

    # Sudo privileged command test (mocked)
    with mock.patch("subprocess.run") as mock_sub:
        mock_sub.return_value = mock.MagicMock(returncode=0, stdout="Restarting service ok", stderr="")
        sudo_res = run_sudo("systemctl restart networking")
        assert "Privileged command succeeded" in sudo_res
        assert "Restarting service ok" in sudo_res


def test_window_listing_and_typing():
    """Verify window listing, active window detection, and desktop typing."""
    from gdr.tools.screen import list_open_windows, read_active_window, type_in_window

    with mock.patch("subprocess.check_output") as mock_out, mock.patch("subprocess.run") as mock_run:
        # Mock active window title
        mock_out.side_effect = [
            "Terminal - GDR AI\n",  # getwindowname
            "0x04000001\n",         # getactivewindow
            "Selected code sample"   # clipboard
        ]
        active = read_active_window()
        assert "Terminal - GDR AI" in active

        # Mock list_open_windows
        mock_out.side_effect = None
        mock_out.return_value = "0x01 0 host1 Terminal\n0x02 0 host1 Google Chrome\n"
        wins = list_open_windows()
        assert "Terminal" in wins
        assert "Google Chrome" in wins

        # Mock type_in_window
        mock_run.return_value = mock.MagicMock(returncode=0)
        res = type_in_window("echo 'hello jarvis'", window_title="Terminal", press_enter=True)
        assert "Successfully typed into window 'Terminal'" in res
        assert "hello jarvis" in res


def test_whatsapp_message_and_browser_login():
    """Verify WhatsApp message formatting and browser automated login."""
    from gdr.tools.screen import send_whatsapp_message, browser_login

    with mock.patch("subprocess.Popen") as mock_popen, mock.patch("shutil.which", return_value="/usr/bin/xdotool"):
        # Test WhatsApp phone number cleanup (e.g. 10 digit Indian number)
        wa_res = send_whatsapp_message("9876543210", "Meeting in 10 minutes", send_now=True)
        assert "+919876543210" in wa_res
        assert "Meeting%20in%2010%20minutes" in wa_res
        assert "WhatsApp message prepared" in wa_res

        # Test browser login autofill queue
        login_res = browser_login("https://github.com/login", username="testuser", password="secretpassword")
        assert "https://github.com/login" in login_res
        assert "testuser" in login_res
        assert "Navigated to" in login_res


def test_panic_mode_unstick_and_agent_resume(tmp_path, monkeypatch):
    """Verify agent detects 'clear panic' or 'resume' when panicked and unlocks immediately."""
    from gdr.safety.panic import trigger_panic, is_panicked, clear_panic
    from gdr.core.agent import Agent

    monkeypatch.setenv("GDR_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr("gdr.safety.panic.PANIC_LOCK_FILE", tmp_path / "panic.lock")

    clear_panic()
    assert is_panicked() is False

    # Trigger panic
    trigger_panic()
    assert is_panicked() is True

    agent = Agent()
    # When panicked, normal requests should be rejected
    res_blocked = agent.run("Open youtube")
    assert "EMERGENCY STOP" in res_blocked or "panic" in res_blocked.lower()

    # User explicitly asks to clear panic / resume
    res_cleared = agent.run("Please clear panic and resume")
    assert "cleared" in res_cleared.lower() or "resumed" in res_cleared.lower()
    assert is_panicked() is False


def test_rest_api_panic_toggle_and_location_endpoints(tmp_path, monkeypatch):
    """Verify /api/panic toggle, /api/location and /api/bookmarks."""
    from fastapi.testclient import TestClient
    from gdr.web.server import app
    from gdr.safety.panic import clear_panic

    monkeypatch.setenv("GDR_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr("gdr.safety.panic.PANIC_LOCK_FILE", tmp_path / "panic.lock")
    monkeypatch.setattr("gdr.tools.desktop.CONFIG_DIR", tmp_path)
    monkeypatch.setattr("gdr.tools.desktop.BOOKMARKS_FILE", tmp_path / "bookmarks.json")

    clear_panic()
    client = TestClient(app)

    # 1. Toggle panic ON
    r1 = client.post("/api/panic", json={"action": "toggle"})
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["panicked"] is True

    # 2. Toggle panic OFF
    r2 = client.post("/api/panic", json={"action": "toggle"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["panicked"] is False
    assert "cleared" in d2["message"].lower()

    # 3. Post Location
    r_loc = client.post("/api/location", json={"latitude": 28.6139, "longitude": 77.2090, "accuracy": 15.0})
    assert r_loc.status_code == 200
    assert r_loc.json()["success"] is True

    # Get Location
    r_get_loc = client.get("/api/location")
    assert r_get_loc.status_code == 200
    assert r_get_loc.json()["latitude"] == 28.6139

    # 4. Bookmarks API
    r_bm_add = client.post("/api/bookmarks", json={"name": "news", "url": "https://news.ycombinator.com", "category": "tech"})
    assert r_bm_add.status_code == 200

    r_bm_list = client.get("/api/bookmarks")
    assert r_bm_list.status_code == 200
    assert "news" in r_bm_list.json()


def test_get_current_location_and_weather_resolution(tmp_path, monkeypatch):
    """Verify get_current_location and get_weather with automatic location resolution."""
    from gdr.tools.desktop import get_current_location, resolve_location_data, get_weather

    monkeypatch.setenv("GDR_CONFIG_DIR", str(tmp_path))
    loc_file = tmp_path / "location.json"
    monkeypatch.setattr("gdr.tools.desktop.LOCATION_FILE", loc_file)
    monkeypatch.setattr("gdr.tools.desktop.CONFIG_DIR", tmp_path)

    loc_data = {
        "latitude": 28.4595,
        "longitude": 77.5020,
        "accuracy": 12.0,
        "display_name": "Knowledge Park II, Greater Noida, Gautam Buddha Nagar, Uttar Pradesh, 201310, India",
        "city": "Greater Noida",
        "state": "Uttar Pradesh",
        "postcode": "201310",
        "country": "India"
    }
    loc_file.write_text(json.dumps(loc_data))

    # Test get_current_location
    res = get_current_location()
    assert "Greater Noida" in res
    assert "28.4595" in res
    assert "High Precision GPS" in res

    # Test get_weather with empty location automatically using resolved city
    with mock.patch("requests.get") as mock_get:
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "current_condition": [{
                "temp_C": "26",
                "temp_F": "78",
                "FeelsLikeC": "27",
                "weatherDesc": [{"value": "Sunny"}],
                "humidity": "45",
                "windspeedKmph": "12",
                "winddir16Point": "NW"
            }],
            "nearest_area": [{
                "areaName": [{"value": "Greater Noida"}],
                "country": [{"value": "India"}]
            }],
            "weather": [{
                "maxtempC": "32",
                "mintempC": "20"
            }]
        }
        mock_get.return_value = mock_resp

        weather_res = get_weather("")
        assert "Greater Noida" in weather_res
        assert "26°C" in weather_res
        assert "Sunny" in weather_res


def test_live_screen_stream_and_frame_api(tmp_path, monkeypatch):
    """Verify live screen streaming frame push, status endpoint, and tools."""
    from fastapi.testclient import TestClient
    from gdr.web.server import app
    from gdr.tools.screen import get_live_screen_status, take_screenshot, see_screen
    import base64

    client = TestClient(app)

    # Fake 100-byte png base64
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 2000
    fake_b64 = "data:image/png;base64," + base64.b64encode(fake_png).decode("utf-8")

    # Post frame
    r = client.post("/api/screen/frame", json={"image": fake_b64})
    assert r.status_code == 200
    assert r.json()["success"] is True

    # Check live status API
    r_live = client.get("/api/screen/live")
    assert r_live.status_code == 200
    assert r_live.json()["active"] is True

    # Check tool status
    status_str = get_live_screen_status()
    assert "ACTIVE" in status_str

    # Test take_screenshot uses live frame
    out_img = tmp_path / "test_shot.png"
    shot_res = take_screenshot(str(out_img))
    assert "live screen stream frame" in shot_res
    assert out_img.exists()
    assert out_img.stat().st_size > 1000

    # Test see_screen incorporates live screen indicator
    see_res = see_screen("What is displayed?")
    assert "Live Screen Stream Active" in see_res


def test_stop_speech_barge_in_api():
    """Verify /api/stop halts assistant audio playback immediately."""
    from fastapi.testclient import TestClient
    from gdr.web.server import app

    client = TestClient(app)
    with mock.patch("gdr.voice.tts.stop_speaking") as mock_stop:
        r = client.post("/api/stop")
        assert r.status_code == 200
        assert r.json()["success"] is True
        mock_stop.assert_called_once()


def test_web_search_and_research():
    """Verify web_search and deep_research functions execute cleanly."""
    from gdr.tools.research import web_search, deep_research

    with mock.patch("requests.post") as mock_post:
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html>
            <a class="result__snippet" href="https://example.com/delhi">Delhi weather and live conditions guide.</a>
            <a class="result__url" href="https://example.com/delhi">https://example.com/delhi</a>
        </html>
        """
        mock_post.return_value = mock_resp

        res = web_search("New Delhi weather")
        assert "Delhi weather" in res or "Search Results" in res or "https://example.com" in res

        # Deep research
        deep_res = deep_research("Quantum Computing")
        assert "research report compiled" in deep_res.lower()
        assert "quantum_computing" in deep_res.lower()


