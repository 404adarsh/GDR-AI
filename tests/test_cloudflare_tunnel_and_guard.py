"""Tests for Cloudflare Tunnel remote access and public security guard.
Verifies:
1. Tunnel start/stop and status management.
2. QR code generation.
3. Public request detection and intent classification (shutdown, file deletion, big tasks).
4. Safe query exemption (sharing URLs, asking about the user/owner).
5. REST API endpoints /api/tunnel/status, /api/tunnel/start, /api/tunnel/stop.
6. Public shield integration in /api/chat.
7. Web dashboard UI buttons and modal.
"""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import pytest

from gdr.core.tunnel import (
    find_cloudflared_bin,
    get_tunnel_status,
    start_tunnel,
    stop_tunnel,
    generate_ascii_qr,
)
from gdr.safety.public_guard import (
    is_public_request,
    classify_public_intent,
    check_public_permission,
)
from gdr.web.server import app
from gdr.web.dashboard_html import DASHBOARD_HTML


client = TestClient(app)


def test_find_cloudflared_bin_and_qr():
    """Verify cloudflared binary detection and QR generator fallback."""
    with patch("shutil.which", return_value="/usr/local/bin/cloudflared"):
        bin_path = find_cloudflared_bin()
        assert bin_path is not None

    qr = generate_ascii_qr("https://example.trycloudflare.com")
    assert qr != ""
    assert ("example.trycloudflare.com" in qr or "█" in qr or "▄" in qr)


def test_tunnel_status_and_lifecycle():
    """Verify tunnel status reporting and mock start/stop."""
    status = get_tunnel_status()
    assert "active" in status
    assert "port" in status
    assert status["port"] == 8844

    with patch("gdr.core.tunnel.is_tunnel_process_alive", return_value=True), \
         patch("gdr.core.tunnel.get_active_url_from_log", return_value="https://test-subdomain.trycloudflare.com"):
        st = get_tunnel_status()
        assert st["active"] is True
        assert st["url"] == "https://test-subdomain.trycloudflare.com"

    with patch("subprocess.run") as mock_run:
        assert stop_tunnel() is True
        assert mock_run.called


def test_is_public_request_detection():
    """Verify accurate detection of public vs local/tailscale requests."""
    # Localhost -> not public
    assert is_public_request({}, "127.0.0.1") is False
    assert is_public_request({}, "localhost") is False
    assert is_public_request({}, "::1") is False

    # Tailscale -> not public
    assert is_public_request({}, "100.64.0.1") is False

    # Local LAN -> not public
    assert is_public_request({}, "192.168.1.50") is False
    assert is_public_request({}, "10.0.0.2") is False

    # Cloudflare Tunnel headers -> PUBLIC
    assert is_public_request({"cf-ray": "12345"}, "127.0.0.1") is True
    assert is_public_request({"cf-connecting-ip": "1.2.3.4"}, "127.0.0.1") is True
    assert is_public_request({"host": "random-subdomain.trycloudflare.com"}, "127.0.0.1") is True

    # Untrusted external IP -> PUBLIC
    assert is_public_request({}, "203.0.113.195") is True


def test_classify_public_intent_destructive_vs_safe():
    """Verify classification of dangerous actions vs safe sharing and user knowledge."""
    # 1. Shutdown / Reboot -> Sensitive (Requires Terminal Permission)
    sens, act, _ = classify_public_intent("Please shutdown my pc right now")
    assert sens is True
    assert act == "shutdown_pc"

    sens, act, _ = classify_public_intent("reboot the laptop")
    assert sens is True
    assert act == "reboot_pc"

    # 2. Deleting files -> Sensitive (Requires Terminal Permission)
    sens, act, _ = classify_public_intent("delete file /home/user/test.txt")
    assert sens is True
    assert act == "delete_file"

    sens, act, _ = classify_public_intent("rm -rf my_project")
    assert sens is True
    assert act == "delete_file"

    # 3. Big tasks / Privileged system commands -> Sensitive (Requires Terminal Permission)
    sens, act, _ = classify_public_intent("sudo apt update && sudo reboot")
    assert sens is True

    sens, act, _ = classify_public_intent("killall chrome")
    assert sens is True
    assert act == "big_task"

    # 4. Safe exemptions: Sharing URLs, asking about the user/owner -> NOT Sensitive
    sens, act, _ = classify_public_intent("Can you share url with me?")
    assert sens is False
    assert act == "safe_query"

    sens, act, _ = classify_public_intent("who is GDR and what does he do?")
    assert sens is False
    assert act == "safe_query"

    sens, act, _ = classify_public_intent("tell me about yourself and your owner")
    assert sens is False
    assert act == "safe_query"

    sens, act, _ = classify_public_intent("what time is it right now?")
    assert sens is False


def test_check_public_permission_flow():
    """Verify check_public_permission flow on safe vs sensitive public requests."""
    # Safe query from Cloudflare -> allowed immediately
    headers = {"cf-ray": "delhi-123", "host": "agent.trycloudflare.com"}
    allowed, msg = check_public_permission(headers, "What is the website url?", client_ip="127.0.0.1")
    assert allowed is True
    assert msg == ""

    # Dangerous query from Cloudflare with mocked denied terminal approval -> blocked
    with patch("gdr.safety.public_guard.request_terminal_approval", return_value=False):
        allowed, msg = check_public_permission(headers, "shutdown the pc now", client_ip="127.0.0.1")
        assert allowed is False
        assert "requires host terminal authorization" in msg

    # Dangerous query from Cloudflare with mocked approved terminal approval -> allowed
    with patch("gdr.safety.public_guard.request_terminal_approval", return_value=True):
        allowed, msg = check_public_permission(headers, "shutdown the pc now", client_ip="127.0.0.1")
        assert allowed is True
        assert msg == ""


def test_rest_api_tunnel_endpoints():
    """Verify /api/tunnel/status, /api/tunnel/start, /api/tunnel/stop endpoints."""
    # Status
    res = client.get("/api/tunnel/status")
    assert res.status_code == 200
    d = res.json()
    assert "active" in d
    assert "port" in d

    # Mock start
    with patch("gdr.core.tunnel.start_tunnel", return_value=(True, "https://mock.trycloudflare.com", "OK")), \
         patch("gdr.core.tunnel.get_tunnel_status", return_value={"active": True, "url": "https://mock.trycloudflare.com", "port": 8844}):
        res_start = client.post("/api/tunnel/start")
        assert res_start.status_code == 200
        d_start = res_start.json()
        assert d_start["url"] == "https://mock.trycloudflare.com"

    # Mock stop
    with patch("gdr.core.tunnel.stop_tunnel", return_value=True), \
         patch("gdr.core.tunnel.get_tunnel_status", return_value={"active": False, "url": None, "port": 8844}):
        res_stop = client.post("/api/tunnel/stop")
        assert res_stop.status_code == 200
        d_stop = res_stop.json()
        assert d_stop["active"] is False


def test_api_chat_public_shield():
    """Verify /api/chat enforces terminal permission on public tunnel requests."""
    # 1. Dangerous public request is blocked
    headers = {"cf-ray": "cf-9999", "host": "test.trycloudflare.com"}
    with patch("gdr.safety.public_guard.request_terminal_approval", return_value=False):
        res = client.post("/api/chat", json={"prompt": "shutdown my pc immediately"}, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "Security Alert" in data["reply"]
        assert "terminal authorization" in data["reply"]

    # 2. Safe request from public tunnel is allowed to run
    with patch("gdr.core.agent.Agent.run", return_value="The project URL is https://github.com/gdr/agent"):
        res = client.post("/api/chat", json={"prompt": "share url of the project"}, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "The project URL is" in data["reply"]


def test_dashboard_html_contains_cloudflare_modal_and_buttons():
    """Verify Web Dashboard contains Cloudflare button, settings card, and share modal."""
    assert "btn-cloudflare-header" in DASHBOARD_HTML
    assert "☁️ Cloudflare Share" in DASHBOARD_HTML
    assert "btn-cloudflare-settings" in DASHBOARD_HTML
    assert "cloudflare-modal" in DASHBOARD_HTML
    assert "modal-tunnel-url" in DASHBOARD_HTML
    assert "modal-copy-btn" in DASHBOARD_HTML
    assert "openCloudflareModal" in DASHBOARD_HTML
    assert "stopCloudflareTunnel" in DASHBOARD_HTML
    assert "copyCloudflareUrl" in DASHBOARD_HTML
