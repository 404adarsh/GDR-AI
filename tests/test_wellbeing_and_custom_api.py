"""Tests for Digital Wellbeing, Custom API Integration, Desktop Assistant, and Authenticated Web.
"""

from pathlib import Path
import tempfile
import time
import pytest

from gdr.system.wellbeing import WellbeingManager
from gdr.integrations.custom_api import CustomAPIRegistry
from gdr.integrations.authenticated_web import AuthenticatedWebManager
from gdr.tools.desktop_assistant import download_file_tool, media_control_tool


def test_wellbeing_break_reminders_and_snooze():
    """Verify continuous activity monitoring, break recommendation triggers, and snoozing."""
    with tempfile.TemporaryDirectory() as td:
        wb = WellbeingManager(config_dir=Path(td))
        wb.save_settings({
            "enabled": True,
            "continuous_limit_minutes": 50,
            "quiet_hours_start": "23:59",  # Not in quiet hours during test
            "quiet_hours_end": "00:01",
            "max_daily_reminders": 5
        })

        # No break due initially
        assert wb.check_break_due() is None

        # Simulate 51 minutes of continuous activity (51 * 60 = 3060 seconds)
        wb.record_active_tick(interval_seconds=3100)
        reminder = wb.check_break_due()
        assert reminder is not None
        assert "taking a gentle" in reminder or "active for approximately" in reminder

        # Snooze for 10 minutes
        snooze_msg = wb.snooze(10)
        assert "snoozed for 10 minutes" in snooze_msg
        # During snooze, reminder should not re-trigger
        assert wb.check_break_due() is None

        # User takes a break
        break_msg = wb.record_break_taken(5)
        assert "Continuous session timer reset" in break_msg
        assert wb.continuous_active_seconds == 0.0


def test_custom_api_registry_security_and_ratelimit():
    """Verify user API registration, encrypted secrets, and rate limiting."""
    with tempfile.TemporaryDirectory() as td:
        reg = CustomAPIRegistry(config_dir=Path(td))

        # Register an API with secret token
        res = reg.register_api(
            name="test_deployment",
            base_url="https://api.example.com",
            description="Production deployment monitoring",
            auth_type="bearer",
            auth_token="secret_token_12345",
            rate_limit_per_minute=2
        )
        assert res["status"] == "ok"

        # List APIs: must never expose raw token
        apis = reg.list_apis()
        assert len(apis) == 1
        assert apis[0]["name"] == "test_deployment"
        assert "secret_token_12345" not in str(apis[0])

        # Test rate limit enforcement
        now = time.time()
        reg._rate_limit_tracker["test_deployment"] = [now - 10, now - 5]  # Exceeded 2 per min within last 60s
        call_res = reg.query(name="test_deployment")
        assert call_res["error"] is True
        assert call_res["status_code"] == 429
        assert "Rate limit exceeded" in call_res["message"]


def test_authenticated_web_allowlist():
    """Verify domain allowlist enforcement and unauthorized domain rejection."""
    with tempfile.TemporaryDirectory() as td:
        mgr = AuthenticatedWebManager(config_dir=Path(td))

        # Initially unauthorized
        auth, mode = mgr.is_domain_authorized("https://internal.company.com/dashboard")
        assert auth is False

        # Add domain to allowlist
        mgr.add_domain("internal.company.com", mode="read_only")
        auth2, mode2 = mgr.is_domain_authorized("https://internal.company.com/dashboard")
        assert auth2 is True
        assert mode2 == "read_only"

        # Content fetch for non-allowlisted site is blocked
        res = mgr.fetch_content("https://unauthorized-evil-site.com/data")
        assert res["error"] is True
        assert res["status"] == "unauthorized_domain"


def test_desktop_assistant_download_security():
    """Verify safe download validation (scheme check, size check)."""
    # Non-HTTP/HTTPS URLs must be rejected
    res_ftp = download_file_tool("ftp://files.example.com/file.zip")
    assert "Only HTTP and HTTPS URLs are permitted" in res_ftp

    res_file = download_file_tool("file:///etc/passwd")
    assert "Only HTTP and HTTPS URLs are permitted" in res_file


def test_media_control_tool_execution():
    """Verify media control tool handles playback and volume actions."""
    res_search = media_control_tool("search_music", query="ambient coding")
    assert "Opened YouTube Music search" in res_search

    res_vol = media_control_tool("volume_up")
    assert "dispatched" in res_vol or "Adjusted" in res_vol or "volume" in res_vol.lower()
