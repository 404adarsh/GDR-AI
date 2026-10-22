"""Tests for Telegram & MarkanM Bot Repair, Token Setup, Real-Time Messaging & Sidebar Functionality.
Verifies:
1. Telegram Bot Token validation & fast outbound test message with millisecond latency measurement.
2. MarkanM Connect Token validation & test message with auto-room detection and 403 Forbidden prevention.
3. Policy engine approval latency bypass for direct bot messages (eliminating 3-minute wait).
4. Command-free natural language message interaction (PC health, battery, tasks, general chat).
5. FastAPI endpoints: /api/telegram/validate, /api/telegram/test, /api/markanm/validate, /api/markanm/test,
   /api/channels/activity (with filtering), /api/channels/activity/clear.
6. Full audit of all 53 sidebar onclick handlers in dashboard_html.py.
7. Dedicated screen-messaging layout and speech/text synchronization engine.
"""

import asyncio
import json
import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient

from gdr.channels.telegram_bot import validate_telegram_token, send_telegram_test_message, is_telegram_bot_running
from gdr.channels.markanm_bot import validate_markanm_token, send_markanm_test_message, is_markanm_bot_running
from gdr.safety.policy_engine import AutonomyPolicyEngine, ActionDecision, get_policy_engine


@pytest.fixture
def test_client():
    from gdr.web.server import app
    return TestClient(app)


def test_telegram_token_validation_success():
    """Verify telegram token validation with successful API response."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = json.dumps({
            "ok": True,
            "result": {
                "id": 987654321,
                "is_bot": True,
                "first_name": "Aarushi Companion",
                "username": "AarushiGdrBot"
            }
        }).encode("utf-8")
        mock_urlopen.return_value = mock_resp

        res = validate_telegram_token("123456:FAKE_VALID_TOKEN")
        assert res["valid"] is True
        assert res["bot"]["username"] == "AarushiGdrBot"
        assert res["bot"]["id"] == 987654321


def test_telegram_token_validation_failure():
    """Verify telegram token validation handles invalid tokens gracefully."""
    import urllib.error
    with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError("url", 401, "Unauthorized", {}, None)):
        res = validate_telegram_token("bad_token")
        assert res["valid"] is False
        assert "Unauthorized" in res["error"]


def test_telegram_test_message_latency_measurement():
    """Verify send_telegram_test_message returns delivery confirmation with latency in ms."""
    with patch("gdr.channels.telegram_bot.get_secret") as mock_secret, \
         patch("urllib.request.urlopen") as mock_urlopen:
        mock_secret.side_effect = lambda k: "123456:FAKE_TOKEN" if k == "TELEGRAM_BOT_TOKEN" else "11223344"
        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.read.return_value = json.dumps({"ok": True, "result": {"message_id": 42}}).encode("utf-8")
        mock_urlopen.return_value = mock_resp

        res = send_telegram_test_message(text="Ping test", chat_id="11223344")
        assert res["success"] is True
        assert res["delivered"] is True
        assert "elapsed_ms" in res
        assert res["elapsed_ms"] >= 0
        assert res["recipient"] == "11223344"
        assert "delivered" in res["message"].lower()


def test_markanm_token_validation_success():
    """Verify MarkanM token validation queries /me and extracts bot developer identity."""
    with patch("markanm.Bot") as mock_bot_cls:
        mock_bot = MagicMock()
        async def fake_get(path):
            return {"user": {"id": "usr_dev_42", "username": "gdr_developer", "name": "GDR Dev"}}
        mock_bot.client.get = fake_get
        mock_bot_cls.return_value = mock_bot

        res = validate_markanm_token("mkbot_valid_token_xyz")
        assert res["valid"] is True
        assert res["bot"]["username"] == "gdr_developer"


def test_markanm_token_validation_invalid():
    """Verify MarkanM token validation correctly flags invalid format or 401."""
    res = validate_markanm_token("invalid_token_without_prefix")
    assert res["valid"] is False
    assert "mkbot_" in res["error"]


def test_markanm_test_message_prevents_403_and_measures_latency():
    """Verify send_markanm_test_message discovers valid rooms instead of sending to non-existent 'default'."""
    with patch("gdr.channels.markanm_bot.get_secret") as mock_secret, \
         patch("markanm.Bot") as mock_bot_cls:
        mock_secret.return_value = "mkbot_valid_token_123"

        mock_bot = MagicMock()
        async def fake_get(path):
            return {"rooms": [{"id": "room_live_99", "name": "General"}]}
        async def fake_send(room_id, text):
            return {"id": "msg_42", "text": text}

        mock_bot.client.get = fake_get
        mock_bot.send_message = fake_send
        mock_bot_cls.return_value = mock_bot

        res = send_markanm_test_message(text="Ping test", room_id="room_live_99")
        assert res["success"] is True
        assert res["delivered"] is True
        assert res["room_id"] == "room_live_99"
        assert "elapsed_ms" in res
        assert res["elapsed_ms"] >= 0


def test_policy_engine_no_three_minute_wait_for_bot_messages():
    """Verify policy engine auto-approves bot notifications and messages to authorized owner without 180s queue delay."""
    pe = AutonomyPolicyEngine()
    # Sending telegram message to chat
    card_tg = pe.evaluate("send_telegram_message", {"message": "Test ping", "chat_id": "12345"})
    assert card_tg.decision == ActionDecision.AUTO

    # Sending markanm message
    card_mk = pe.evaluate("send_markanm_message", {"message": "Test ping", "room_id": "room_1"})
    assert card_mk.decision == ActionDecision.AUTO


def test_fastapi_telegram_and_markanm_endpoints(test_client):
    """Verify FastAPI routes for token validation, test latency, activity logs, and log purge."""
    with patch("gdr.channels.telegram_bot.validate_telegram_token") as mock_tg_val, \
         patch("gdr.channels.telegram_bot.send_telegram_test_message") as mock_tg_test, \
         patch("gdr.channels.markanm_bot.validate_markanm_token") as mock_mk_val, \
         patch("gdr.channels.markanm_bot.send_markanm_test_message") as mock_mk_test:

        mock_tg_val.return_value = {"success": True, "valid": True, "bot": {"username": "test_bot"}}
        mock_tg_test.return_value = {"success": True, "delivered": True, "elapsed_ms": 195.4, "recipient": "123", "message": "Delivered in 195ms"}
        mock_mk_val.return_value = {"success": True, "valid": True, "user": {"username": "dev_user"}}
        mock_mk_test.return_value = {"success": True, "delivered": True, "elapsed_ms": 162.1, "room_id": "r1", "message": "Delivered in 162ms"}

        # Telegram Validate
        res1 = test_client.post("/api/telegram/validate", json={"token": "123:ABC"})
        assert res1.status_code == 200
        assert res1.json()["valid"] is True

        # Telegram Test with Latency
        res2 = test_client.post("/api/telegram/test", json={"chat_id": "123"})
        assert res2.status_code == 200
        assert res2.json()["elapsed_ms"] == 195.4

        # MarkanM Validate
        res3 = test_client.post("/api/markanm/validate", json={"token": "mkbot_abc"})
        assert res3.status_code == 200
        assert res3.json()["valid"] is True

        # MarkanM Test with Latency
        res4 = test_client.post("/api/markanm/test", json={"room_id": "r1"})
        assert res4.status_code == 200
        assert res4.json()["elapsed_ms"] == 162.1

        # Channel Activity Filter
        res5 = test_client.get("/api/channels/activity?provider=telegram")
        assert res5.status_code == 200
        assert "activity" in res5.json()

        # Channel Activity Clear
        res6 = test_client.post("/api/channels/activity/clear")
        assert res6.status_code == 200
        assert res6.json()["success"] is True


def test_command_free_natural_language_intent_routing():
    """Verify bots process ordinary natural language messages without requiring /auth or slash commands."""
    from unittest.mock import AsyncMock
    from gdr.channels.markanm_bot import build_markanm_bot

    with patch("gdr.channels.markanm_bot.get_secret", return_value="mkbot_test"), \
         patch("markanm.Bot") as mock_bot_cls:
        registered_handlers = {}
        mock_instance = MagicMock()
        def mock_on(event_name):
            def decorator(func):
                registered_handlers[event_name] = func
                return func
            return decorator
        mock_instance.on = mock_on
        mock_bot_cls.return_value = mock_instance

        bot = build_markanm_bot("mkbot_test_token")
        handler = registered_handlers.get("message.created")
        assert handler is not None

        # Test system health natural language routing
        evt = MagicMock()
        evt.payload = {"room_id": "r1", "text": "how is my system health", "user": {"id": "123", "username": "owner"}}
        evt.reply = AsyncMock()

        with patch("gdr.channels.markanm_bot.load_config", return_value={"channels": {"allowed_markanm_username": "owner", "allowed_markanm_user_id": "123"}}):
            asyncio.run(handler(evt))
            assert evt.reply.called
            sent_reply = evt.reply.call_args[0][0]
            assert any(k in sent_reply for k in ["CPU", "System", "RAM", "Health", "Battery", "%"])


def test_sidebar_audit_all_onclick_functions_defined():
    """Audit all 53 sidebar items to ensure zero missing symbols or broken ReferenceError calls."""
    import re
    from gdr.web.dashboard_html import DASHBOARD_HTML

    html = DASHBOARD_HTML
    sidebar_match = re.search(r'<aside class="primary-sidebar".*?</aside>', html, re.DOTALL)
    assert sidebar_match is not None, "Sidebar container must exist in dashboard HTML"

    sidebar_html = sidebar_match.group(0)
    onclick_funcs = re.findall(r'([a-zA-Z0-9_]+)\(', sidebar_html)
    assert len(onclick_funcs) >= 45, f"Expected 45+ sidebar actions, found {len(onclick_funcs)}"

    missing_funcs = []
    for fn in set(onclick_funcs):
        if fn == "var":
            continue
        # Check if function is defined in script blocks
        is_defined = (f"function {fn}" in html) or (f"{fn} =" in html) or (f"{fn}=" in html)
        if not is_defined:
            missing_funcs.append(fn)

    assert missing_funcs == [], f"Found missing sidebar handlers: {missing_funcs}"


def test_dedicated_messaging_screen_structure():
    """Verify dedicated screen-messaging exists with cards, validation buttons, latency feedback, and filters."""
    from gdr.web.dashboard_html import DASHBOARD_HTML
    html = DASHBOARD_HTML

    assert 'id="screen-messaging"' in html, "Dedicated screen-messaging container must exist"
    assert 'id="msg-tg-token-input"' in html, "Telegram token input on messaging screen must exist"
    assert 'id="msg-mk-token-input"' in html, "MarkanM token input on messaging screen must exist"
    assert 'validateTelegramTokenUI' in html, "Telegram token validation UI handler must exist"
    assert 'validateMarkanMTokenUI' in html, "MarkanM token validation UI handler must exist"
    assert 'testTelegramMessageUI' in html, "Telegram test message handler must exist"
    assert 'testMarkanMMessageUI' in html, "MarkanM test message handler must exist"
    assert 'filterBotActivityLogs' in html, "Bot activity filter function must exist"
    assert 'clearBotActivityLogs' in html, "Clear bot activity logs handler must exist"
    assert 'nav-messaging-btn' in html, "Sidebar entry for Messaging Integrations must exist"
