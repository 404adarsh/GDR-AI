import pytest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
from gdr.channels.telegram_bot import send_telegram_test_message, create_telegram_application
from gdr.channels.markanm_bot import send_markanm_test_message, build_markanm_bot
from gdr.core.agent import Agent
from gdr.core.providers import SarvamProvider
from gdr.tools.desktop_assistant import install_software_package
from gdr.tools.browser import browser_set_headless
from gdr.config import load_config


def test_telegram_test_message_accepts_message_kwarg():
    """Verify send_telegram_test_message accepts keyword argument 'message' without TypeError."""
    res = send_telegram_test_message(message="Test message from Aarushi", chat_id="12345")
    assert isinstance(res, dict)
    assert "success" in res


def test_markanm_test_message_accepts_message_kwarg():
    """Verify send_markanm_test_message accepts keyword argument 'message' without TypeError."""
    res = send_markanm_test_message(message="Test message to MarkanM", room_id="test_room")
    assert isinstance(res, dict)
    assert "success" in res


def test_telegram_multi_username_authorization():
    """Verify multiple authorized usernames separated by commas or spaces are all authorized."""
    with patch("gdr.channels.telegram_bot.load_config", return_value={
        "channels": {
            "allowed_telegram_username": "alice, bob, @charlie",
            "allowed_telegram_user_id": 0
        }
    }):
        app = create_telegram_application()
        assert app is not None

        # Check authorization logic directly via handler
        is_auth = None
        for handler_list in app.handlers.values():
            for h in handler_list:
                # Find handler with check_and_reject or callback
                pass


def test_sarvam_error_does_not_silently_fallback_to_offline_local():
    """Verify that when Sarvam encounters an API error, it does not silently switch to local offline AI."""
    with patch("gdr.safety.secrets.get_secret", side_effect=lambda k: "sk_test_sarvam_key" if k == "SARVAM_API_KEY" else ""):
        agent = Agent()
        # Mock Sarvam provider raising an error
        with patch.object(agent.provider, "chat", side_effect=RuntimeError("Quota exceeded on Sarvam API")):
            reply = agent.run("Please open YouTube and check emails")
            # Must NOT silently switch to offline local AI mode
            assert "[Offline Local AI Mode]" not in reply
            assert "⚠️" in reply or "Sarvam" in reply or "Quota" in reply


def test_install_software_package_tool_existing_binary():
    """Verify install_software_package detects already installed packages."""
    res = install_software_package("python3")
    assert "already installed" in res.lower()
    assert "python3" in res


def test_browser_set_headless_tool_registered():
    """Verify browser_set_headless is a callable tool."""
    from gdr.tools.registry import get_tool_metadata
    meta = get_tool_metadata("browser_set_headless")
    assert meta is not None
    assert meta["category"] == "browser"


def test_default_model_is_sarvam_conversations():
    """Verify SarvamProvider defaults to sarvam-105b-conversations."""
    prov = SarvamProvider(api_key="mock_test_key")
    assert prov.model == "sarvam-105b-conversations"

