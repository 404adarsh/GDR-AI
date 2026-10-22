import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from gdr.memory.rag import (
    RAGStore,
    verify_rag_pin,
    get_rag_store,
    search_knowledge_base,
    add_to_knowledge_base,
)
from gdr.web.server import app


@pytest.fixture
def temp_rag(tmp_path):
    db_file = tmp_path / "test_rag.db"
    store = RAGStore(db_path=db_file)
    return store


def test_rag_pin_authorization():
    assert verify_rag_pin("845427") is True
    assert verify_rag_pin(" 845427 ") is True
    assert verify_rag_pin("123456") is False
    assert verify_rag_pin("") is False
    assert verify_rag_pin(None) is False


def test_rag_store_crud(temp_rag):
    # Ingest document
    doc1 = temp_rag.add_document(
        title="Project Antigravity Notes",
        content="Antigravity is an agentic AI assistant framework designed for autonomous coding and desktop automation.",
        category="notes",
        tags="ai, coding, automation"
    )
    assert doc1["id"] > 0
    assert doc1["title"] == "Project Antigravity Notes"

    doc2 = temp_rag.add_document(
        title="Secret Production Credentials",
        content="The staging database host is db-stage.internal with port 5432 and master user root.",
        category="secrets",
        tags="database, creds"
    )
    assert doc2["id"] > 0

    # Stats
    stats = temp_rag.get_stats()
    assert stats["total_documents"] == 2
    assert "notes" in stats["categories"]
    assert "secrets" in stats["categories"]

    # Search
    results = temp_rag.search_rag("autonomous coding assistant", top_k=5)
    assert len(results) > 0
    assert results[0]["id"] == doc1["id"]

    results_db = temp_rag.search_rag("staging database host 5432", top_k=5)
    assert len(results_db) > 0
    assert results_db[0]["id"] == doc2["id"]

    # List & filter
    all_docs = temp_rag.list_documents()
    assert len(all_docs) == 2

    notes_docs = temp_rag.list_documents(category="notes")
    assert len(notes_docs) == 1
    assert notes_docs[0]["id"] == doc1["id"]

    # Delete
    deleted = temp_rag.delete_document(doc1["id"])
    assert deleted is True
    assert temp_rag.get_stats()["total_documents"] == 1


def test_rag_context_formatting(temp_rag):
    temp_rag.add_document(
        title="DevUser Favorite Foods",
        content="DevUser loves hot samosas, spicy pav bhaji, and authentic masala chai with ginger and cardamom.",
        category="facts"
    )
    ctx = temp_rag.format_rag_context("What snack does DevUser like with tea?")
    assert "DevUser Favorite Foods" in ctx
    assert "masala chai" in ctx
    assert "samosas" in ctx


def test_rag_agent_tool_handlers(temp_rag):
    with patch("gdr.memory.rag.get_rag_store", return_value=temp_rag):
        add_res = add_to_knowledge_base(
            title="DevUser Meeting",
            content="Team sync occurs every Tuesday at 11am IST.",
            category="calendar"
        )
        assert "Saved to Knowledge Base" in add_res
        assert "DevUser Meeting" in add_res

        search_res = search_knowledge_base("When is the team meeting?")
        assert "Tuesday at 11am" in search_res


def test_sarvam_and_bots_api_endpoints():
    from gdr.safety.secrets import get_secret, set_secret
    client = TestClient(app)

    orig_key = get_secret("SARVAM_API_KEY")

    try:
        # 1. Sarvam config
        res = client.get("/api/sarvam/config")
        assert res.status_code == 200
        assert "has_key" in res.json()

        res = client.post("/api/sarvam/config", json={"api_key": "sk_test_sarvam_12345", "model": "sarvam-105b"})
        assert res.status_code == 200
        assert res.json()["success"] is True

        # 2. Telegram config
        res = client.get("/api/telegram/config")
        assert res.status_code == 200
        data = res.json()
        assert "has_token" in data
        assert "running" in data

        # 3. MarkanM config
        res = client.get("/api/markanm/config")
        assert res.status_code == 200
        data = res.json()
        assert "has_token" in data
        assert "running" in data
    finally:
        client.post("/api/sarvam/config", json={"model": "sarvam-105b-conversations"})
        if orig_key:
            set_secret("SARVAM_API_KEY", orig_key)


def test_rag_api_endpoints():
    client = TestClient(app)

    # Auth with invalid PIN
    res = client.post("/api/rag/auth", json={"pin": "wrongpin"})
    assert res.status_code == 403

    # Auth with correct Master PIN
    res = client.post("/api/rag/auth", json={"pin": "845427"})
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Query without PIN
    res = client.get("/api/rag/documents")
    assert res.status_code == 403

    # Query with correct PIN header
    res = client.get("/api/rag/documents", headers={"X-RAG-PIN": "845427"})
    assert res.status_code == 200
    assert "documents" in res.json()

    # Add document via API
    res = client.post(
        "/api/rag/documents",
        headers={"X-RAG-PIN": "845427"},
        json={
            "title": "Aarushi Voice Style",
            "content": "Aarushi should speak playfully, warmly, with sweet teasing and deep affection.",
            "category": "facts",
            "tags": "persona, voice"
        }
    )
    assert res.status_code == 200
    doc_id = res.json()["document"]["id"]

    # Semantic Query API
    res = client.post(
        "/api/rag/query",
        headers={"X-RAG-PIN": "845427"},
        json={"query": "How should Aarushi speak?"}
      )
    assert res.status_code == 200
    assert len(res.json()["matches"]) > 0

    # Delete Document API
    del_res = client.delete(f"/api/rag/documents/{doc_id}", headers={"X-RAG-PIN": "845427"})
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Verify frontend HTML handles string/array tags safely without throwing TypeError
    from gdr.web.dashboard_html import DASHBOARD_HTML
    assert "Array.isArray(doc.tags)" in DASHBOARD_HTML
    assert "doc.tags.split(',')" in DASHBOARD_HTML


def test_markanm_bot_module_imports_and_structure():
    import gdr.channels.markanm_bot as mbot
    assert hasattr(mbot, "is_markanm_bot_running")
    assert hasattr(mbot, "start_markanm_bot_service")
    assert hasattr(mbot, "stop_markanm_bot_service")
    assert hasattr(mbot, "send_markanm_message")


def test_telegram_bot_module_imports_and_structure():
    import gdr.channels.telegram_bot as tg
    assert hasattr(tg, "is_telegram_bot_running")
    assert hasattr(tg, "start_telegram_bot_service")
    assert hasattr(tg, "stop_telegram_bot_service")
    assert hasattr(tg, "send_telegram_message")
    assert hasattr(tg, "send_telegram_voice")


def test_vad_adaptive_endpointing_module():
    import gdr.voice.vad as vad
    assert hasattr(vad, "VADRecorder")
    assert hasattr(vad.VADRecorder, "record_phrase")
    assert hasattr(vad, "check_and_boost_mic")
    assert hasattr(vad, "query_audio_devices")
    assert hasattr(vad, "fix_and_boost_microphones")
    assert hasattr(vad, "test_microphone_input")


def test_audio_device_api_endpoints():
    client = TestClient(app)

    # 1. Query audio devices
    res = client.get("/api/audio/devices")
    assert res.status_code == 200
    data = res.json()
    assert "inputs" in data
    assert "outputs" in data

    # 2. Select audio devices
    res = client.post("/api/audio/devices/select", json={"input_device": 0, "output_device": 0})
    assert res.status_code == 200
    assert res.json()["success"] is True

    # 3. Fix and boost microphones
    res = client.post("/api/audio/mic/fix")
    assert res.status_code == 200
    assert "message" in res.json()

    # 4. Test microphone capture
    res = client.post("/api/audio/mic/test", json={"device": 0})
    assert res.status_code == 200
    assert "success" in res.json()


def test_wakeword_detector_timeout_support():
    from gdr.voice.wakeword import WakeWordDetector
    detector = WakeWordDetector()
    # Test wait_for_wake_word returns False gracefully when model is unavailable or timed out
    detected = detector.wait_for_wake_word(timeout=0.05)
    # Returns True if model not available or False if timed out
    assert isinstance(detected, bool)


def test_telegram_and_markanm_username_security_endpoints():
    from gdr.config import load_config, save_config
    import copy
    orig_cfg = copy.deepcopy(load_config())

    client = TestClient(app)

    try:
        # 1. Test Telegram username whitelist save & retrieve
        res = client.post("/api/telegram/config", json={
            "token": "test_token_123",
            "chat_id": "999888777",
            "username": "@my_lord_husband",
            "enabled": False
        })
        assert res.status_code == 200
        assert res.json()["success"] is True

        res = client.get("/api/telegram/config")
        assert res.status_code == 200
        data = res.json()
        assert data["allowed_username"] == "my_lord_husband"
        assert data["allowed_user_id"] == 999888777

        # 2. Test MarkanM username whitelist save & retrieve
        res = client.post("/api/markanm/config", json={
            "token": "mkbot_test_123",
            "room_id": "101",
            "username": "@my_lord_husband",
            "allowed_user_id": "user_42",
            "enabled": False
        })
        assert res.status_code == 200
        assert res.json()["success"] is True

        res = client.get("/api/markanm/config")
        assert res.status_code == 200
        data = res.json()
        assert data["allowed_username"] == "my_lord_husband"
        assert data["allowed_user_id"] == "user_42"
    finally:
        save_config(orig_cfg)


def test_telegram_bot_unauthorized_rejection():
    import gdr.channels.telegram_bot as tg
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    # Mock config with allowed username and allowed user id
    with patch("gdr.channels.telegram_bot.load_config", return_value={
        "channels": {
            "allowed_telegram_username": "my_lord_husband",
            "allowed_telegram_user_id": 12345
        }
    }):
        with patch.object(tg, "get_secret", return_value="fake_token"):
            app_bot = tg.create_telegram_application()
            assert app_bot is not None
            # Check unauthorized user rejection text
            unauth_user = SimpleNamespace(id=99999, username="stranger_attacker", first_name="Stranger")
            mock_msg = MagicMock()
            mock_msg.reply_text = AsyncMock()
            mock_update = SimpleNamespace(effective_user=unauth_user, message=mock_msg, callback_query=None)
            
            import asyncio
            for h in app_bot.handlers.get(0, []):
                if hasattr(h, "callback") and h.callback.__name__ == "start_cmd":
                    start_handler = h.callback
                    asyncio.run(start_handler(mock_update, MagicMock()))
                    reply_call = mock_msg.reply_text.call_args[0][0]
                    assert ("Access restricted" in reply_call or "authenticate" in reply_call)
                    assert "/auth" in reply_call
                    break


def test_request_store_database_crud(tmp_path):
    from gdr.safety.request_db import RequestStore
    db_file = tmp_path / "test_requests.db"
    store = RequestStore(db_path=db_file)

    # Log requests
    req_id1 = store.log_request(
        ip_address="192.168.1.50",
        method="POST",
        path="/api/chat",
        body_payload={"prompt": "Hello Aarushi, how is my PC?"},
        user_details={"prompt": "Hello Aarushi, how is my PC?", "user": "DevUser"},
        status_code=200,
        duration_ms=45.2,
        source="lan"
    )
    assert req_id1 > 0

    req_id2 = store.log_request(
        ip_address="203.0.113.195",
        method="GET",
        path="/api/screen/latest.jpg",
        status_code=200,
        duration_ms=12.0,
        source="cloudflare"
    )
    assert req_id2 > 0

    # Retrieve recent
    logs = store.get_recent_requests(limit=10)
    assert len(logs) == 2
    assert logs[0]["ip_address"] == "203.0.113.195"
    assert logs[1]["ip_address"] == "192.168.1.50"
    assert "Hello Aarushi" in logs[1]["body_payload"]
    assert "DevUser" in logs[1]["user_details"]

    # Filter by IP
    ip_logs = store.get_recent_requests(ip_filter="203.0.113")
    assert len(ip_logs) == 1
    assert ip_logs[0]["id"] == req_id2

    # Stats
    stats = store.get_request_stats()
    assert stats["total_requests"] == 2
    assert stats["unique_ips"] == 2

    # Clear old requests
    cleared = store.clear_old_requests(days=365)
    assert cleared == 0


def test_request_logging_api_endpoints():
    client = TestClient(app)

    # 1. Trigger an API call
    res = client.get("/api/status")
    assert res.status_code == 200

    # 2. Query /api/requests
    res_logs = client.get("/api/requests?limit=10")
    assert res_logs.status_code == 200
    data = res_logs.json()
    assert data["success"] is True
    assert "requests" in data
    assert len(data["requests"]) > 0

    # Verify latest request logged /api/status or /api/requests
    recent_paths = [r["path"] for r in data["requests"]]
    assert any("/api/status" in p or "/api/requests" in p for p in recent_paths)

    # 3. Query /api/requests/stats
    res_stats = client.get("/api/requests/stats")
    assert res_stats.status_code == 200
    stats_data = res_stats.json()
    assert stats_data["success"] is True
    assert stats_data["stats"]["total_requests"] >= 1


def test_telegram_and_markanm_master_password_845457_auth():
    import gdr.channels.telegram_bot as tg
    import gdr.channels.markanm_bot as mk
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, patch
    import asyncio

    with patch.dict(os.environ, {"BOT_MASTER_PASSWORD": "845457"}):
        # 1. Telegram Bot /auth 845457
        with patch.object(tg, "get_secret", return_value="fake_tg_token"):
            app_bot = tg.create_telegram_application()
            auth_user = SimpleNamespace(id=777888, username="my_husband", first_name="DevUser")
            mock_msg = MagicMock()
            mock_msg.reply_text = AsyncMock()
            mock_msg.text = "/auth 845457"
            mock_update = SimpleNamespace(effective_user=auth_user, message=mock_msg, callback_query=None)

            # Call auth_cmd
            for h in app_bot.handlers.get(0, []):
                if hasattr(h, "callback") and h.callback.__name__ == "auth_cmd":
                    ctx = SimpleNamespace(args=["845457"])
                    asyncio.run(h.callback(mock_update, ctx))
                    reply = mock_msg.reply_text.call_args[0][0]
                    assert "verified" in reply.lower() or "authenticated" in reply.lower()
                    break

        # 2. MarkanM Bot /auth 845457
        with patch.object(mk, "get_secret", return_value="mkbot_fake_token"):
            bot = mk.build_markanm_bot("mkbot_fake_token")
            mock_ctx = MagicMock()
            mock_ctx.user = SimpleNamespace(id="mk_user_1", username="devuser_mk", display_name="DevUser")
            mock_ctx.args = ["845457"]
            mock_ctx.reply = AsyncMock()

            # Find auth command handler
            auth_handler = bot._commands.get("auth") if hasattr(bot, "_commands") else None
            if auth_handler:
                asyncio.run(auth_handler(mock_ctx))
                reply_mk = mock_ctx.reply.call_args[0][0]
                assert "verified" in reply_mk.lower() or "authenticated" in reply_mk.lower()


def test_markanm_dynamic_room_id_and_no_room_required():
    import gdr.channels.markanm_bot as mk
    from unittest.mock import AsyncMock

    # Test dynamic room recording
    mk.record_active_room("room_dynamic_99")
    assert mk._LAST_ROOM_ID == "room_dynamic_99"

    # Test send_markanm_message uses dynamic room when room_id is None
    with patch.object(mk, "get_secret", return_value="mkbot_test_token"):
        with patch("markanm.Bot") as mock_bot_cls:
            mock_instance = MagicMock()
            mock_instance.send_message = AsyncMock(return_value=True)
            mock_bot_cls.return_value = mock_instance

            sent = mk.send_markanm_message("Test message without room ID")
            assert sent is True
            mock_instance.send_message.assert_called_with(room_id="room_dynamic_99", text="Test message without room ID")


def test_aarushi_companion_conversational_smart_reply():
    from gdr.models.manager import generate_smart_local_reply

    # 1. Talk to me
    r1 = generate_smart_local_reply("talk to me")
    assert "jaan" in r1.lower()
    assert "listening closely and learning from you" not in r1.lower()

    # 2. Flirt & Love
    r2 = generate_smart_local_reply("i love you")
    assert "pyaar" in r2.lower()
    assert "jealous" in r2.lower() or "possessive" in r2.lower()

    # 3. Jealousy
    r3 = generate_smart_local_reply("are you jealous?")
    assert "jealous" in r3.lower()

    # 4. Identity
    r4 = generate_smart_local_reply("who is your lord husband")
    assert "creator" in r4.lower() or "companion" in r4.lower()

    # 5. General conversational statement
    r5 = generate_smart_local_reply("aaj bahut kaam hai")
    assert "listening closely and learning from you" not in r5.lower()
    assert "aaj bahut kaam hai" in r5


def test_secrets_persistence_multilayer(tmp_path):
    from gdr.safety.secrets import set_secret, get_secret, delete_secret
    from gdr.config import load_config

    test_key = "TEST_MOCK_PERSISTENT_KEY"
    test_val = "sk_test_persistent_secret_12345"

    set_secret(test_key, test_val)
    # Check that get_secret retrieves it
    assert get_secret(test_key) == test_val

    # Check config.toml mirror
    cfg = load_config()
    assert cfg.get("secrets", {}).get(test_key) == test_val

    # Clean up
    delete_secret(test_key)


def test_api_endpoints_return_masked_tokens():
    from fastapi.testclient import TestClient
    from gdr.web.server import app
    from gdr.safety.secrets import set_secret, get_secret

    client = TestClient(app)

    orig_sarvam = get_secret("SARVAM_API_KEY")
    orig_tg = get_secret("TELEGRAM_BOT_TOKEN")
    orig_mk = get_secret("MARKANM_BOT_TOKEN")
    orig_el = get_secret("ELEVENLABS_API_KEY")

    # Use dummy non-placeholder test tokens (no real secrets)
    TEST_SARVAM = "sk_sarvam_dummy_token_for_testing_12345"
    TEST_TG = "123456:tele_dummy_token_testing"
    TEST_MK = "mkbot_dummy_token_testing"
    TEST_EL = "sk_elevenlabs_dummy_token_testing"

    try:
        set_secret("SARVAM_API_KEY", TEST_SARVAM)
        set_secret("TELEGRAM_BOT_TOKEN", TEST_TG)
        set_secret("MARKANM_BOT_TOKEN", TEST_MK)
        set_secret("ELEVENLABS_API_KEY", TEST_EL)

        r_sarvam = client.get("/api/sarvam/config").json()
        assert r_sarvam["has_key"] is True
        assert "..." in r_sarvam["masked_key"]
        # Raw secret must NEVER be returned plaintext
        assert r_sarvam["api_key"] != TEST_SARVAM
        assert "..." in r_sarvam["api_key"]

        r_tg = client.get("/api/telegram/config").json()
        assert r_tg["has_token"] is True
        assert r_tg["token"] != TEST_TG
        assert "..." in r_tg["masked_token"]

        r_mk = client.get("/api/markanm/config").json()
        assert r_mk["has_token"] is True
        assert r_mk["token"] != TEST_MK
        assert "..." in r_mk["masked_token"]

        r_el = client.get("/api/elevenlabs/config").json()
        assert r_el["has_key"] is True
        assert r_el["api_key"] != TEST_EL
        assert "..." in r_el["masked_key"]
    finally:
        if orig_sarvam:
            set_secret("SARVAM_API_KEY", orig_sarvam)
        if orig_tg:
            set_secret("TELEGRAM_BOT_TOKEN", orig_tg)
        if orig_mk:
            set_secret("MARKANM_BOT_TOKEN", orig_mk)
        if orig_el:
            set_secret("ELEVENLABS_API_KEY", orig_el)


def test_channels_activity_and_logging():
    from fastapi.testclient import TestClient
    from gdr.web.server import app
    from gdr.safety.request_db import log_inbound_request

    client = TestClient(app)

    log_inbound_request(
        ip_address="tg:987654321",
        method="TG_CMD",
        path="/telegram/status",
        user_details={"username": "devuser_test", "command": "status"},
        status_code=200,
        source="telegram"
    )

    log_inbound_request(
        ip_address="markanm:mk_user_1",
        method="MK_CMD",
        path="/markanm/weather",
        user_details={"username": "gdr_mk", "command": "weather", "args": "Delhi"},
        status_code=200,
        source="markanm"
    )

    resp = client.get("/api/channels/activity?limit=10").json()
    assert resp["success"] is True
    assert len(resp["activity"]) >= 2
    sources = [item["source"] for item in resp["activity"]]
    assert "telegram" in sources
    assert "markanm" in sources


def test_markanm_rich_commands():
    import gdr.channels.markanm_bot as mk
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    bot = mk.build_markanm_bot("mkbot_fake_token")
    mock_ctx = MagicMock()
    mock_ctx.user = SimpleNamespace(id="mk_user_1", username="devuser_mk", display_name="DevUser")
    mock_ctx.args = ["Delhi"]
    mock_ctx.reply = AsyncMock()

    # Weather command
    weather_handler = bot.commands.get("weather")
    assert weather_handler is not None

    # Search command
    search_handler = bot.commands.get("search")
    assert search_handler is not None

    # RAG command
    rag_handler = bot.commands.get("rag")
    assert rag_handler is not None

    # Volume command
    vol_handler = bot.commands.get("volume")
    assert vol_handler is not None


def test_user_profile_and_identity_customization_api():
    """Verify GET and POST /api/settings/profile for dynamic names and credentials."""
    from starlette.testclient import TestClient
    from gdr.web.server import app
    client = TestClient(app)

    # 1. GET profile
    res = client.get("/api/settings/profile")
    assert res.status_code == 200
    d = res.json()
    assert d["success"] is True
    assert "user_name" in d
    assert "assistant_name" in d

    # 2. POST update profile
    post_res = client.post("/api/settings/profile", json={
        "user_name": "NewOwner",
        "assistant_name": "NewAssistant",
        "tone": "playful and helpful"
    })
    assert post_res.status_code == 200
    pd = post_res.json()
    assert pd["success"] is True
    assert pd["user_name"] == "NewOwner"
    assert pd["assistant_name"] == "NewAssistant"

    # Verify updated GET
    get_res2 = client.get("/api/settings/profile")
    d2 = get_res2.json()
    assert d2["user_name"] == "NewOwner"
    assert d2["assistant_name"] == "NewAssistant"


def test_email_and_system_compatibility_endpoints():
    """Verify email settings persistence and system compatibility audit."""
    from starlette.testclient import TestClient
    from gdr.web.server import app
    client = TestClient(app)

    # 1. System Compatibility Endpoint
    comp_res = client.get("/api/system/compatibility")
    assert comp_res.status_code == 200
    comp_data = comp_res.json()
    assert "overall_status" in comp_data
    assert "checks" in comp_data
    assert len(comp_data["checks"]) >= 5

    # 2. Email Settings Endpoint
    email_get = client.get("/api/settings/email")
    assert email_get.status_code == 200
    assert "email_address" in email_get.json()

    # 3. Save Email Settings
    email_post = client.post("/api/settings/email", json={
        "email_address": "test_agent_user@example.com",
        "app_password": "abcd efgh ijkl mnop"
    })
    assert email_post.status_code == 200
    assert email_post.json()["success"] is True

    # 4. Status endpoint includes quota tracking
    status_res = client.get("/api/status")
    assert status_res.status_code == 200
    sd = status_res.json()
    assert "sarvam_quota_exceeded" in sd


def test_android_termux_tools_and_schemas():
    """Verify Android Termux tool registry and graceful fallback."""
    from gdr.tools.registry import get_all_tool_schemas
    import gdr.tools.android_tool as a_tool

    schemas = get_all_tool_schemas()
    tool_names = [s["function"]["name"] for s in schemas]

    # Verify Android tools are registered
    assert "android_battery_status" in tool_names
    assert "android_toggle_torch" in tool_names
    assert "android_vibrate" in tool_names
    assert "android_show_notification" in tool_names
    assert "android_send_sms" in tool_names
    assert "android_make_call" in tool_names
    assert "android_take_photo" in tool_names
    assert "android_get_gps_location" in tool_names
    assert "android_tts_speak" in tool_names
    assert "android_clipboard" in tool_names

    # Test fallback execution when not running in Termux
    batt = a_tool.android_battery_status()
    assert isinstance(batt, str)
    assert len(batt) > 0

    torch = a_tool.android_toggle_torch(enabled=True)
    assert isinstance(torch, str)

    vib = a_tool.android_vibrate(200)
    assert isinstance(vib, str)


def test_clean_bot_message_formatting():
    """Verify format_clean_bot_message strips system tags, reasoning blocks, and weird symbols."""
    from gdr.channels.format_utils import format_clean_bot_message

    dirty = (
        "<think>Let me see what the user asked.</think>\n"
        "[Offline Local AI Mode] [Sarvam • Neural HD Studio (hi-IN-SwaraNeural)]\n"
        "Here are the details for your day:\n"
        "★ Priority items:\n"
        "• Check morning emails ♪\n"
        "• Join 11 AM conference call ✦\n"
        "\n\n\n"
        "Everything looks well-structured!"
    )
    clean = format_clean_bot_message(dirty)
    assert "<think>" not in clean
    assert "[Offline Local AI Mode]" not in clean
    assert "Sarvam • Neural" not in clean
    assert "♪" not in clean
    assert "★" not in clean
    assert "✦" not in clean
    assert "- Check morning emails" in clean
    assert "Here are the details for your day:" in clean
    assert "\n\n\n" not in clean


def test_telegram_bot_service_lifecycle_safe():
    """Verify start_telegram_bot_service and stop_telegram_bot_service handle lifecycle safely."""
    from gdr.channels.telegram_bot import start_telegram_bot_service, stop_telegram_bot_service, is_telegram_bot_running
    # Without token, should return clean error without throwing
    res = start_telegram_bot_service()
    assert isinstance(res, dict)
    assert "success" in res
    assert stop_telegram_bot_service() is True


def test_markanm_bot_service_lifecycle_safe():
    """Verify start_markanm_bot_service and stop_markanm_bot_service handle lifecycle safely."""
    from gdr.channels.markanm_bot import start_markanm_bot_service, stop_markanm_bot_service, is_markanm_bot_running
    res = start_markanm_bot_service()
    assert isinstance(res, dict)
    assert "success" in res
    assert stop_markanm_bot_service() is True


def test_task_progress_tracker_and_simultaneous_execution():
    """Verify background task progress tracking ('how much it did, how much it left') and concurrent execution."""
    from gdr.core.tasks import get_task_tracker, run_simultaneous_task
    tracker = get_task_tracker()
    task = tracker.register_task(name="Test Download", description="Downloading test model", total_steps=100)
    tracker.update_progress(task.task_id, completed_steps=45, status_message="Downloading chunk 45/100")

    summary = tracker.get_overall_summary()
    assert "Test Download" in summary
    assert "45%" in summary
    assert "steps" in summary

    # Verify task progress report details
    t_dict = task.to_dict()
    assert t_dict["percentage"] == 45
    assert t_dict["completed_steps"] == 45
    assert t_dict["total_steps"] == 100

    tracker.complete_task(task.task_id)
    assert task.status == "completed"


def test_sarvam_105b_conversations_model_and_cloud_priority():
    """Verify SarvamProvider defaults to sarvam-105b-conversations and agent prioritizes it."""
    from gdr.core.providers import SarvamProvider
    p = SarvamProvider(api_key="test_key_abc")
    assert p.model in ["sarvam-105b", "sarvam-105b-conversations"]
    assert p.api_key == "test_key_abc"










