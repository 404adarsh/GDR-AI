"""Tests for GDR-IDE Focus Talking Mode: Anime Companion Call Experience.
Validates character assets, manifest, REST endpoints, static file delivery,
barge-in voice interruption mechanisms, and HTML/UI integration.
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import pytest
from fastapi.testclient import TestClient

from gdr.web.server import app, STATIC_DIR
from gdr.web.dashboard_html import DASHBOARD_HTML


@pytest.fixture
def client():
    return TestClient(app)


def test_api_characters_manifest(client):
    """Verify /api/characters returns all available anime companion profiles."""
    res = client.get("/api/characters")
    assert res.status_code == 200
    data = res.json()
    assert "characters" in data
    chars = {c["id"]: c for c in data["characters"]}
    
    assert "aarushi" in chars
    assert "aoi" in chars
    assert "kenji" in chars

    aarushi = chars["aarushi"]
    assert aarushi["name"] == "Aarushi"
    assert "Warm" in aarushi["role"]
    assert "neutral" in aarushi["expressions"]
    assert "listening" in aarushi["expressions"]
    assert "speaking" in aarushi["expressions"]
    assert "CC0" in aarushi.get("license", {}).get("name", "")


def test_api_character_by_id(client):
    """Verify /api/characters/{char_id} returns character details and 404 for invalid."""
    res_aarushi = client.get("/api/characters/aarushi")
    assert res_aarushi.status_code == 200
    assert res_aarushi.json()["name"] == "Aarushi"

    res_aoi = client.get("/api/characters/aoi")
    assert res_aoi.status_code == 200
    assert res_aoi.json()["name"] == "Aoi"

    res_kenji = client.get("/api/characters/kenji")
    assert res_kenji.status_code == 200
    assert res_kenji.json()["name"] == "Kenji"

    res_invalid = client.get("/api/characters/nonexistent_companion")
    assert res_invalid.status_code == 404


def test_character_svg_assets_exist_and_are_valid():
    """Verify all character vector SVG files exist and are well-formed XML/SVG."""
    characters_dir = STATIC_DIR / "characters"
    assert characters_dir.exists()

    expected_chars = ["aarushi", "aoi", "kenji"]
    expected_expressions = [
        "neutral", "listening", "speaking", "happy", "thinking",
        "curious", "surprised", "comforting", "teasing", "sleepy"
    ]

    for char_id in expected_chars:
        char_dir = characters_dir / char_id
        assert char_dir.exists(), f"Directory missing for {char_id}"

        for expr in expected_expressions:
            svg_file = char_dir / f"{expr}.svg"
            assert svg_file.exists(), f"Missing SVG: {svg_file}"
            content = svg_file.read_text(encoding="utf-8")
            assert "<svg" in content
            assert "</svg>" in content

            # Verify it parses as valid XML
            root = ET.fromstring(content)
            assert root.tag.endswith("svg")
            assert "viewBox" in root.attrib


def test_static_character_svg_serving(client):
    """Verify FastAPI static route serves character SVGs with correct MIME type."""
    for char in ["aarushi", "aoi", "kenji"]:
        res = client.get(f"/static/characters/{char}/neutral.svg")
        assert res.status_code == 200
        assert "image/svg+xml" in res.headers.get("content-type", "")
        assert len(res.content) > 500


def test_dashboard_html_contains_focus_overlay_and_controls():
    """Verify DASHBOARD_HTML contains complete Focus Call overlay structure and controls."""
    html = DASHBOARD_HTML

    # Overlay & themes
    assert 'id="focus-call-overlay"' in html
    assert "focus-theme-midnight" in html
    assert "focus-theme-lavender" in html
    assert "focus-theme-warm" in html
    assert "focus-theme-dark" in html

    # Character stage & halo
    assert 'id="focus-character-img"' in html
    assert 'id="focus-halo"' in html
    assert 'id="focus-voice-wave"' in html
    assert 'id="focus-expression-pill"' in html
    assert "companion-breathe" in html

    # Call controls
    assert 'id="focus-btn-mic"' in html
    assert 'id="focus-btn-stop"' in html
    assert 'id="focus-btn-speaker"' in html
    assert 'id="focus-btn-end"' in html
    assert "interruptFocusCall()" in html

    # Live transcript
    assert 'id="focus-transcript-user-text"' in html
    assert 'id="focus-transcript-bot-text"' in html
    assert 'id="focus-call-timer"' in html

    # Character Gallery Modal
    assert 'id="character-gallery-modal"' in html
    assert 'id="char-card-aarushi"' in html
    assert 'id="char-card-aoi"' in html
    assert 'id="char-card-kenji"' in html


def test_dashboard_html_contains_navigation_entry_points():
    """Verify entry points into Focus Talking Mode exist in sidebar, home, and chat headers."""
    html = DASHBOARD_HTML

    # Sidebar button
    assert 'id="nav-focus-call-btn"' in html
    assert "19. Focus Anime Call" in html
    assert "openFocusCallMode()" in html

    # Home quick button
    assert 'id="focus-call-home-btn"' in html
    assert "Call Aarushi (Focus Mode)" in html

    # Chat header button
    assert "Focus Call" in html

    # Command palette action
    assert "19. Focus Anime Companion Call" in html


def test_dashboard_html_contains_focus_call_manager_script():
    """Verify Focus Call Manager and barge-in integration logic are present in dashboard scripts."""
    html = DASHBOARD_HTML

    required_js_symbols = [
        "openFocusCallMode",
        "closeFocusCallMode",
        "interruptFocusCall",
        "setFocusCharacter",
        "setFocusTheme",
        "setFocusExpression",
        "updateFocusCallState",
        "updateFocusUserTranscript",
        "updateFocusAssistantTranscript",
        "analyzeAndSetExpression",
        "openCharacterGalleryModal",
        "selectCharacter",
        "loadFocusCharactersManifest"
    ]

    for sym in required_js_symbols:
        assert sym in html, f"Missing JS function: {sym}"
