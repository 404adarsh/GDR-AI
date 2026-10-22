"""Tests for GDR Stealth Meeting & Interview Copilot (Phases 16+).
Verifies:
1. StealthCopilot singleton and state management.
2. Screen question solver formulating Talking Points, Optimal Approach/Big-O, Code, and Edge Cases.
3. Audio whisper and auto-watch mechanics.
4. Mobile OLED Teleprompter endpoint (GET /stealth).
5. Stealth REST APIs (status, latest, solve, autowatch, whisper, clear).
6. Google Meet screen-share invisibility & camouflage architecture.
"""

from fastapi.testclient import TestClient
import pytest

from gdr.stealth.copilot import get_stealth_copilot, StealthCopilot
from gdr.web.server import app
from gdr.web.dashboard_html import DASHBOARD_HTML


@pytest.fixture
def client():
    return TestClient(app)


def test_stealth_copilot_singleton_and_status():
    copilot1 = get_stealth_copilot()
    copilot2 = get_stealth_copilot()
    assert copilot1 is copilot2

    status = copilot1.get_status()
    assert "autowatch_enabled" in status
    assert "whisper_enabled" in status
    assert "has_solution" in status
    assert "is_solving" in status


def test_stealth_copilot_solve_algorithm_and_structure():
    copilot = get_stealth_copilot()
    
    # Solve Two Sum
    res = copilot.solve_screen(force_prompt="Given an array of integers nums and an integer target, return indices of two numbers that add up to target.")
    assert res is not None
    assert "Two Sum" in res["question"] or "indices" in res["question"].lower()
    
    # 1. Spoken Talking Points to say immediately
    assert res["talking_points"] != ""
    assert any(k in res["talking_points"].lower() for k in ["hash map", "linear", "complement", "two sum"])

    # 2. Optimal Approach & Big-O
    assert res["approach"] != ""
    assert "O(N)" in res["approach"] or "O(" in res["approach"]

    # 3. Clean Code
    assert res["code"] != ""
    assert "def " in res["code"]

    # 4. Critical Edge Cases
    assert res["edge_cases"] != ""
    assert any(k in res["edge_cases"].lower() for k in ["negative", "empty", "null", "duplicate", "element"])


def test_stealth_copilot_solve_system_design():
    copilot = get_stealth_copilot()
    res = copilot.solve_screen(force_prompt="Design a distributed rate limiter for an API Gateway handling 100k RPS.")
    
    assert res is not None
    assert "rate limit" in res["question"].lower() or "design" in res["question"].lower()
    assert any(k in res["talking_points"].lower() for k in ["token bucket", "sliding window", "redis", "rate"])
    assert "redis" in res["approach"].lower() or "bucket" in res["approach"].lower()
    assert len(res["code"]) > 20


def test_stealth_copilot_autowatch_and_whisper_toggles():
    copilot = get_stealth_copilot()

    # Toggle autowatch
    state1 = copilot.toggle_autowatch(True, interval=3.0)
    assert state1 is True
    assert copilot.get_status()["autowatch_enabled"] is True

    state2 = copilot.toggle_autowatch(False)
    assert state2 is False
    assert copilot.get_status()["autowatch_enabled"] is False

    # Toggle whisper
    w1 = copilot.toggle_whisper(True)
    assert w1 is True
    assert copilot.get_status()["whisper_enabled"] is True

    w2 = copilot.toggle_whisper(False)
    assert w2 is False
    assert copilot.get_status()["whisper_enabled"] is False


def test_stealth_mobile_teleprompter_endpoint(client):
    """Verify standalone OLED Mobile Teleprompter page served for phone companion."""
    resp = client.get("/stealth")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    html = resp.text

    # Verify pure black OLED design & key UI elements
    assert "GDR AI | Stealth Copilot" in html
    assert "SOLVE NOW" in html
    assert "Say This First" in html
    assert "Optimal Approach &amp; Big-O" in html or "Optimal Approach & Big-O" in html
    assert "Solution Code" in html
    assert "Edge Cases" in html
    assert "100% Invisible to Google Meet" in html


def test_stealth_rest_apis(client):
    """Verify REST API lifecycle for Stealth Copilot."""
    # 1. Status
    resp = client.get("/api/stealth/status")
    assert resp.status_code == 200
    st = resp.json()
    assert "autowatch_enabled" in st

    # 2. Trigger Solve
    solve_resp = client.post("/api/stealth/solve", json={"prompt": "Valid Parentheses: check if string of brackets is valid"})
    assert solve_resp.status_code == 200
    sol = solve_resp.json()
    assert "Parentheses" in sol["question"] or "brackets" in sol["question"].lower()
    assert "talking_points" in sol
    assert "approach" in sol
    assert "code" in sol

    # 3. Latest
    latest_resp = client.get("/api/stealth/latest")
    assert latest_resp.status_code == 200
    latest = latest_resp.json()
    assert latest["question"] == sol["question"]

    # 4. Auto-watch API toggle
    auto_resp = client.post("/api/stealth/autowatch", json={"enabled": True, "interval": 4.0})
    assert auto_resp.status_code == 200
    assert auto_resp.json()["autowatch_enabled"] is True
    client.post("/api/stealth/autowatch", json={"enabled": False})

    # 5. Whisper API toggle
    whisp_resp = client.post("/api/stealth/whisper", json={"enabled": True})
    assert whisp_resp.status_code == 200
    assert whisp_resp.json()["whisper_enabled"] is True
    client.post("/api/stealth/whisper", json={"enabled": False})

    # 6. Clear
    clear_resp = client.post("/api/stealth/clear")
    assert clear_resp.status_code == 200
    assert clear_resp.json()["success"] is True


def test_dashboard_html_stealth_integration():
    """Verify dashboard includes Stealth Copilot nav tab, screen, and ghost camouflage overlay."""
    assert "🕵️ Stealth Copilot" in DASHBOARD_HTML
    assert 'id="screen-stealth"' in DASHBOARD_HTML
    assert 'id="stealth-ghost-hud"' in DASHBOARD_HTML
    assert "Ghost Prompter" in DASHBOARD_HTML
    assert "Phone Pairing" in DASHBOARD_HTML
    assert "SYSTEM MONITOR" in DASHBOARD_HTML

