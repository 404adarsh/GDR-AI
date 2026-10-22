"""MarkanM Connect & Chat Bot Channel for GDR AI & Aarushi Companion.
Integrates with MarkanM Chat platform via the official 'markanm' Python SDK:
- Supports slash commands (/start, /help, /ask, /status, /screenshot, /remind, /tasks, /ping, /stop)
- Listens to plain text chat messages and responds using Aarushi's full persona & tools
- Sends outbound notifications, reminders, and proactive chat messages to MarkanM rooms
- Background polling runner with service management.
"""

import asyncio
import logging
import os
import threading
from typing import Optional, Dict, Any, List

from gdr.config import load_config, save_config
from gdr.safety.secrets import get_secret
from gdr.core.agent import Agent
from gdr.safety.panic import trigger_panic
from gdr.tools.system import system_health
from gdr.tools.screen import take_screenshot
from gdr.scheduler.store import get_job_store
from gdr.channels.format_utils import format_clean_bot_message

logger = logging.getLogger("gdr.channels.markanm_bot")

_MARKANM_THREAD: Optional[threading.Thread] = None
_MARKANM_RUNNING: bool = False
_MARKANM_BOT = None
_LAST_ROOM_ID: Optional[str] = None
_MARKANM_STATUS: str = "stopped"
MASTER_BOT_PASSWORD = os.environ.get("BOT_MASTER_PASSWORD", "")


def record_active_room(room_id: Any):
    """Dynamically record the most recent active room so users don't have to manually configure room IDs."""
    global _LAST_ROOM_ID
    if room_id is not None and str(room_id).strip():
        _LAST_ROOM_ID = str(room_id).strip()


def is_markanm_bot_running() -> bool:
    """Check if the MarkanM bot polling daemon is currently active."""
    global _MARKANM_RUNNING, _MARKANM_THREAD
    return bool(_MARKANM_RUNNING and _MARKANM_THREAD and _MARKANM_THREAD.is_alive())


def validate_markanm_token(token: Optional[str] = None) -> Dict[str, Any]:
    """Validate a MarkanM bot token against chat.markanm.com/api/bot/v1/me."""
    tok = token or get_secret("MARKANM_BOT_TOKEN")
    if not tok:
        return {"valid": False, "error": "Token is empty"}
    if not tok.startswith("mkbot_"):
        return {"valid": False, "error": "Invalid MarkanM token format. Token must start with 'mkbot_...'"}

    try:
        from markanm import Bot
        from markanm.exceptions import MarkanMAuthError, MarkanMPermissionError, MarkanMError
        bot = Bot(tok)

        async def _check():
            return await bot.client.get("/me")

        loop = asyncio.new_event_loop()
        try:
            profile = loop.run_until_complete(_check())
            user_data = profile.get("bot") or profile.get("user") or profile
            return {
                "valid": True,
                "bot": {
                    "id": user_data.get("id"),
                    "username": user_data.get("username", ""),
                    "display_name": user_data.get("display_name") or user_data.get("name", "MarkanM Bot"),
                    "role": user_data.get("role", "bot")
                }
            }
        finally:
            loop.close()
    except Exception as e:
        err_str = str(e)
        if "401" in err_str or "unauthorized" in err_str.lower():
            return {"valid": False, "error": "Unauthorized: Invalid MarkanM token. Generate a new token at chat.markanm.com/developers"}
        if "403" in err_str or "forbidden" in err_str.lower():
            return {"valid": False, "error": "Forbidden: Token lacks bot permissions. Verify developer account at chat.markanm.com"}
        return {"valid": False, "error": f"MarkanM API error: {err_str}"}


def send_markanm_test_message(text: str = "", room_id: Optional[str] = None, message: Optional[str] = None) -> Dict[str, Any]:
    """Send a test message to MarkanM chat with precise latency measurement and clear error diagnosis."""
    import time
    t0 = time.time()
    text = format_clean_bot_message(text or message or "")

    token = get_secret("MARKANM_BOT_TOKEN")
    if not token:
        return {"success": False, "message": "MARKANM_BOT_TOKEN is unset in secrets.", "elapsed_ms": 0}

    cfg = load_config()
    target_room = room_id or _LAST_ROOM_ID or cfg.get("channels", {}).get("markanm_room_id")

    try:
        from markanm import Bot
        from markanm.exceptions import MarkanMPermissionError, MarkanMAuthError, MarkanMNotFoundError, MarkanMError
        bot = Bot(token)

        async def _send():
            nonlocal target_room
            # If no room known, attempt to query the bot's available rooms
            if not target_room or target_room == "default":
                try:
                    rooms_resp = await bot.client.get("/rooms")
                    rooms_list = rooms_resp.get("rooms", [])
                    if rooms_list:
                        target_room = rooms_list[0].get("id")
                        record_active_room(target_room)
                except Exception:
                    pass

            if not target_room or target_room == "default":
                raise ValueError("No active room found. Please invite the bot to a room in MarkanM Chat or specify a Room ID.")

            return await bot.send_message(room_id=str(target_room), text=text)

        loop = asyncio.new_event_loop()
        try:
            res = loop.run_until_complete(_send())
            elapsed_ms = int((time.time() - t0) * 1000)
            success = True
            msg_id = (res.get("id") if isinstance(res, dict) else getattr(res, "id", "msg_ok")) or "msg_ok"
        finally:
            loop.close()

        try:
            from gdr.safety.request_db import log_inbound_request
            log_inbound_request(
                ip_address=f"markanm:{target_room}",
                method="MK_TEST",
                path="/markanm/test",
                body_payload={"text": text, "room_id": str(target_room), "latency_ms": elapsed_ms},
                user_details={"room_id": str(target_room), "type": "test_message", "elapsed_ms": elapsed_ms},
                status_code=200,
                source="markanm"
            )
        except Exception:
            pass

        return {
            "success": True,
            "delivered": True,
            "message": f"Delivered to MarkanM room '{target_room}' in {elapsed_ms}ms!",
            "elapsed_ms": elapsed_ms,
            "room_id": str(target_room)
        }
    except Exception as e:
        elapsed_ms = int((time.time() - t0) * 1000)
        err_msg = str(e)
        status_code = 500

        if "403" in err_msg or "permission" in err_msg.lower() or "forbidden" in err_msg.lower():
            status_code = 403
            friendly_err = f"HTTP 403 Forbidden: The bot is not a member of room '{target_room}' or lacks post permissions. Invite the bot to the channel at chat.markanm.com."
        elif "401" in err_msg or "unauthorized" in err_msg.lower():
            status_code = 401
            friendly_err = "HTTP 401 Unauthorized: Invalid or expired MarkanM token. Update token at chat.markanm.com/developers."
        elif "404" in err_msg:
            status_code = 404
            friendly_err = f"Room '{target_room}' not found on MarkanM server."
        else:
            friendly_err = f"MarkanM Error: {err_msg}"

        try:
            from gdr.safety.request_db import log_inbound_request
            log_inbound_request(
                ip_address=f"markanm:{target_room or 'unknown'}",
                method="MK_TEST_ERROR",
                path="/markanm/test",
                body_payload={"text": text, "error": friendly_err},
                user_details={"room_id": str(target_room or ""), "error": friendly_err},
                status_code=status_code,
                source="markanm"
            )
        except Exception:
            pass

        return {
            "success": False,
            "message": friendly_err,
            "elapsed_ms": elapsed_ms,
            "status_code": status_code
        }


def send_markanm_message(text: str, room_id: Optional[str] = None) -> bool:
    """Send an outbound message to a MarkanM chat room without forcing manual room configuration."""
    res = send_markanm_test_message(text, room_id=room_id)
    return bool(res.get("success", False))


def build_markanm_bot(token: str):
    """Instantiate and register handlers for the MarkanM bot."""
    from markanm import Bot

    bot = Bot(token)
    agent = Agent()

    from gdr.safety.auth import get_channel_auth_manager, normalize_username
    auth_mgr = get_channel_auth_manager()

    UNAUTHORIZED_MSG = (
        "🔒 Access restricted: Your MarkanM account is not recognized. "
        "If you are the owner, please authenticate using `/auth <password>` to verify your session."
    )

    def is_authorized(user_data) -> bool:
        u_name = ""
        uid = ""

        if hasattr(user_data, "username") and user_data.username:
            u_name = str(user_data.username).strip()
        elif isinstance(user_data, dict) and user_data.get("username"):
            u_name = str(user_data.get("username")).strip()

        if not u_name:
            if hasattr(user_data, "display_name") and user_data.display_name:
                u_name = str(user_data.display_name).strip()
            elif isinstance(user_data, dict) and user_data.get("display_name"):
                u_name = str(user_data.get("display_name")).strip()

        if hasattr(user_data, "id") and user_data.id is not None:
            uid = str(user_data.id).strip()
        elif isinstance(user_data, dict) and user_data.get("id"):
            uid = str(user_data.get("id")).strip()

        cfg = load_config()
        authed, _ = auth_mgr.is_authorized("markanm", user_id=uid, username=u_name, config=cfg)
        return authed

    async def check_and_reject(ctx, cmd: str = "") -> bool:
        # Dynamically record room ID from incoming context
        r_id = getattr(ctx, "room_id", None) or getattr(getattr(ctx, "message", None), "room_id", None)
        record_active_room(r_id)

        async def _safe_cmd_reply(msg_text: str):
            try:
                if hasattr(ctx, "reply"):
                    await ctx.reply(msg_text)
                    return
            except Exception as cr_err:
                logger.debug(f"ctx.reply failed: {cr_err}")
            target_room = r_id or _LAST_ROOM_ID or load_config().get("channels", {}).get("markanm_room_id")
            if target_room:
                try:
                    await bot.send_message(str(target_room), msg_text)
                except Exception as b_err:
                    logger.error(f"bot.send_message failed in command {cmd}: {b_err}")

        # Dedup commands
        payload = getattr(ctx, "payload", {}) if isinstance(getattr(ctx, "payload", {}), dict) else {}
        cmd_id = (
            getattr(ctx, "id", None)
            or getattr(getattr(ctx, "event", None), "id", None)
            or payload.get("id")
            or payload.get("event_id")
        )
        if cmd_id:
            from gdr.safety.idempotency import get_event_deduplicator
            if not get_event_deduplicator().claim_event("markanm", f"cmd_{cmd_id}"):
                logger.info(f"Duplicate MarkanM command dropped: cmd_{cmd_id}")
                return False

        u = getattr(ctx, "user", None) or {}
        uname = getattr(u, "username", None) or getattr(u, "display_name", None) or "user"
        uid = getattr(u, "id", None) or "unknown"
        args_str = " ".join(getattr(ctx, "args", []))
        full_text = f"{cmd} {args_str}".strip()

        authed = is_authorized(u)

        # Master Password Fallback
        if not authed and (cmd in ("auth", "login") or full_text.startswith("/auth")):
            cand_pw = args_str.strip() or (full_text.replace("/auth", "").strip())
            if cand_pw:
                success, msg = auth_mgr.authenticate_password("markanm", str(uid), str(uname), cand_pw)
                if success:
                    authed = True
                    await _safe_cmd_reply("✅ Identity verified successfully! Welcome back. Your MarkanM account is now authenticated and linked.")
                else:
                    await _safe_cmd_reply(msg)
                    return False

        try:
            from gdr.safety.request_db import log_inbound_request
            log_inbound_request(
                ip_address=f"markanm:{uid}",
                method="MK_CMD" if cmd else "MK_MSG",
                path=f"/markanm/{cmd}" if cmd else "/markanm/chat",
                user_details={
                    "username": uname,
                    "user_id": uid,
                    "command": cmd,
                    "args": args_str
                },
                status_code=200 if authed else 403,
                source="markanm"
            )
        except Exception:
            pass

        if not authed:
            unauth_msg = (
                f"🔒 Access restricted: Your MarkanM account (@{uname}) is not recognized. "
                "If you are the owner, please authenticate using `/auth <password>` to verify your session."
            )
            await _safe_cmd_reply(unauth_msg)
            return False
        return True

    @bot.command("start")
    async def start_cmd(ctx):
        if not await check_and_reject(ctx, "start"):
            return
        user_name = ctx.user.display_name or ctx.user.username or "there"
        await ctx.reply(
            f"👋 Hello {user_name}! I am Aarushi, your AI companion connected to your laptop!\n\n"
            "✨ Available commands:\n"
            "💬 /ask <question> — Ask me anything\n"
            "🌦️ /weather [city] — Get current live weather\n"
            "🔍 /search <query> — Search the live web\n"
            "🧠 /rag <query> — Search private knowledge vault\n"
            "🗣️ /voice <text> — Speak aloud on laptop speakers\n"
            "🔊 /volume <0-100%> — Adjust laptop speaker volume\n"
            "🔆 /brightness <0-100%> — Adjust laptop screen brightness\n"
            "🖥️ /open <app/url> — Open application or URL on laptop\n"
            "📍 /location — Get laptop geographical location\n"
            "📊 /status — View CPU, VRAM, and laptop health\n"
            "⏰ /remind <time> <task> — Schedule a reminder\n"
            "📸 /screenshot — View laptop screen capture\n"
            "📋 /tasks — View scheduled routines & automations\n"
            "📶 /ping — Check connection latency\n"
            "🔐 /auth <password> — Authenticate with Master Bot Password\n"
            "🚨 /stop — Emergency panic kill-switch\n"
            "✅ /clearpanic — Resume normal operations\n"
            "ℹ️ /help — Show this help message\n\n"
            "💬 Or just send any direct message to chat with me! ❤️"
        )

    @bot.command("help")
    async def help_cmd(ctx):
        await start_cmd(ctx)

    @bot.command("ping")
    async def ping_cmd(ctx):
        if not await check_and_reject(ctx, "ping"):
            return
        await ctx.reply("Pong! 🏓 Aarushi is active and running on your system!")

    @bot.command("status")
    async def status_cmd(ctx):
        if not await check_and_reject(ctx, "status"):
            return
        health = system_health()
        await ctx.reply(f"💻 System Health & Diagnostics:\n\n{health}")

    @bot.command("screenshot")
    async def screenshot_cmd(ctx):
        if not await check_and_reject(ctx, "screenshot"):
            return
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            img_path = tf.name
        take_screenshot(img_path)
        if os.path.exists(img_path) and os.path.getsize(img_path) > 1000:
            await ctx.reply(f"🖥️ Desktop screenshot captured successfully on host at: {img_path}")
        else:
            await ctx.reply("❌ Failed to capture screenshot.")

    @bot.command("tasks")
    async def tasks_cmd(ctx):
        if not await check_and_reject(ctx, "tasks"):
            return
        store = get_job_store()
        jobs = store.list_jobs()
        if not jobs:
            await ctx.reply("📋 No active tasks scheduled.")
            return
        lines = ["📋 Scheduled Tasks on Laptop:"]
        for j in jobs:
            lines.append(f"• #{j['id']} ({j['next_run_at'][:16]}): {j['description']}")
        await ctx.reply("\n".join(lines))

    @bot.command("remind")
    async def remind_cmd(ctx):
        if not await check_and_reject(ctx, "remind"):
            return
        args = ctx.args
        if not args:
            await ctx.reply("Usage: /remind <time e.g. 15m or 18:00> <message>")
            return
        prompt = f"Set a reminder for {args[0]}: {' '.join(args[1:])}"
        reply = agent.run(prompt)
        reply = format_clean_bot_message(reply)
        await ctx.reply(reply)

    @bot.command("stop")
    async def stop_cmd(ctx):
        if not await check_and_reject(ctx, "stop"):
            return
        msg = trigger_panic()
        await ctx.reply(f"🚨 Panic Mode Activated: {msg}")

    @bot.command("ask")
    async def ask_cmd(ctx):
        if not await check_and_reject(ctx, "ask"):
            return
        question = " ".join(ctx.args).strip()
        if not question:
            await ctx.reply("Usage: /ask <your question>")
            return
        r_id = getattr(ctx, "room_id", None) or getattr(getattr(ctx, "message", None), "room_id", None) or "general"
        session_id = f"mk_{r_id}"
        from gdr.memory.store import get_memory_store
        mem_store = get_memory_store()
        mem_store.save_chat_message("user", question, session_id=session_id)
        reply = agent.run(question, session_id=session_id, channel="markanm")
        reply = format_clean_bot_message(reply)
        mem_store.save_chat_message("assistant", reply, session_id=session_id)
        await ctx.reply(reply)

    @bot.command("auth")
    async def auth_cmd(ctx):
        r_id = getattr(ctx, "room_id", None) or getattr(getattr(ctx, "message", None), "room_id", None)
        record_active_room(r_id)
        u = ctx.user
        uname = getattr(u, "username", None) or getattr(u, "display_name", None)
        uid = getattr(u, "id", None)
        candidate_pw = " ".join(getattr(ctx, "args", [])).strip()
        if not candidate_pw:
            await ctx.reply("🔑 Please provide your password:\n`/auth <password>`")
            return
        success, msg = auth_mgr.authenticate_password("markanm", str(uid), str(uname), candidate_pw)
        if success:
            await ctx.reply("✅ Identity verified successfully! Welcome back. Your MarkanM account is now authenticated and linked.")
        else:
            await ctx.reply(msg)

    @bot.command("login")
    async def login_cmd(ctx):
        await auth_cmd(ctx)

    @bot.command("weather")
    async def weather_cmd(ctx):
        if not await check_and_reject(ctx, "weather"):
            return
        loc = " ".join(ctx.args).strip()
        from gdr.tools.weather import get_weather
        res = get_weather(loc)
        await ctx.reply(f"🌦️ {res}")

    @bot.command("search")
    async def search_cmd(ctx):
        if not await check_and_reject(ctx, "search"):
            return
        query = " ".join(ctx.args).strip()
        if not query:
            await ctx.reply("Usage: /search <your query>")
            return
        from gdr.tools.search import web_search
        res = web_search(query)
        await ctx.reply(f"🔍 {res}")

    @bot.command("rag")
    async def rag_cmd(ctx):
        if not await check_and_reject(ctx, "rag"):
            return
        query = " ".join(ctx.args).strip()
        if not query:
            await ctx.reply("Usage: /rag <query to search in knowledge base>")
            return
        from gdr.memory.rag import get_rag_store
        store = get_rag_store()
        matches = store.search_rag(query, top_k=3)
        if not matches:
            await ctx.reply("🧠 No matching documents found in RAG knowledge vault.")
            return
        lines = ["🧠 Retrieved from RAG Knowledge Vault:"]
        for m in matches:
            lines.append(f"• *{m['title']}* [{m['category']}]: {m['content'][:200]}...")
        await ctx.reply("\n\n".join(lines))

    @bot.command("volume")
    async def volume_cmd(ctx):
        if not await check_and_reject(ctx, "volume"):
            return
        val = " ".join(ctx.args).strip() or "75%"
        from gdr.tools.hardware import set_volume
        res = set_volume(val)
        await ctx.reply(f"🔊 {res}")

    @bot.command("brightness")
    async def brightness_cmd(ctx):
        if not await check_and_reject(ctx, "brightness"):
            return
        val = " ".join(ctx.args).strip() or "80%"
        from gdr.tools.hardware import set_brightness
        res = set_brightness(val)
        await ctx.reply(f"🔆 {res}")

    @bot.command("open")
    async def open_cmd(ctx):
        if not await check_and_reject(ctx, "open"):
            return
        target = " ".join(ctx.args).strip()
        if not target:
            await ctx.reply("Usage: /open <app or website e.g. youtube>")
            return
        from gdr.tools.desktop import desktop_open
        res = desktop_open(target)
        await ctx.reply(f"🖥️ {res}")

    @bot.command("location")
    async def location_cmd(ctx):
        if not await check_and_reject(ctx, "location"):
            return
        from gdr.tools.location import get_current_location
        res = get_current_location()
        await ctx.reply(f"📍 Current Laptop Location:\n{res}")

    @bot.command("clearpanic")
    async def clearpanic_cmd(ctx):
        if not await check_and_reject(ctx, "clearpanic"):
            return
        from gdr.safety.panic import clear_panic
        clear_panic()
        await ctx.reply("✅ Panic mode cleared! System operations resumed on your laptop.")

    @bot.command("voice")
    async def voice_cmd(ctx):
        if not await check_and_reject(ctx, "voice"):
            return
        text_to_speak = " ".join(ctx.args).strip()
        if not text_to_speak:
            await ctx.reply("Usage: /voice <message to speak aloud on laptop>")
            return
        from gdr.voice.tts import speak_text
        speak_text(text_to_speak)
        await ctx.reply(f"🗣️ Aarushi spoke aloud on your laptop: \"{text_to_speak}\"")

    @bot.command("sysinfo")
    async def sysinfo_cmd(ctx):
        await status_cmd(ctx)

    @bot.command("health")
    async def health_cmd(ctx):
        await status_cmd(ctx)

    async def _handle_incoming_text_event(evt):
        payload = evt.payload if isinstance(evt.payload, dict) else {}
        msg_obj = payload.get("message") if isinstance(payload.get("message"), dict) else {}
        r_id = (
            getattr(evt, "room_id", None)
            or payload.get("room_id")
            or payload.get("conversation_id")
            or (payload.get("room") or {}).get("id")
            or (msg_obj.get("room") or {}).get("id")
            or msg_obj.get("room_id")
            or _LAST_ROOM_ID
            or load_config().get("channels", {}).get("markanm_room_id")
        )
        record_active_room(r_id)

        user_info = (
            payload.get("user")
            or getattr(evt, "user", None)
            or msg_obj.get("user")
            or msg_obj.get("sender")
            or payload.get("sender")
            or {}
        )
        text = payload.get("text") or msg_obj.get("text") or payload.get("content") or msg_obj.get("content") or getattr(evt, "text", "") or ""
        text = str(text).strip()

        uname = user_info.get("username") if isinstance(user_info, dict) else getattr(user_info, "username", "user")
        uid = user_info.get("id") if isinstance(user_info, dict) else getattr(user_info, "id", "unknown")

        async def _safe_reply(msg_text: str):
            try:
                if hasattr(evt, "reply"):
                    await evt.reply(msg_text)
                    return
            except Exception as e1:
                logger.debug(f"evt.reply failed, trying bot.send_message: {e1}")

            target_room = r_id or _LAST_ROOM_ID or load_config().get("channels", {}).get("markanm_room_id")
            if target_room:
                try:
                    await bot.send_message(str(target_room), msg_text)
                except Exception as e2:
                    logger.error(f"bot.send_message failed to room {target_room}: {e2}")

        if not text:
            return

        # Deduplicate incoming message events
        from gdr.safety.idempotency import get_event_deduplicator
        evt_id = getattr(evt, "id", None) or getattr(evt, "event_id", None) or payload.get("id") or payload.get("event_id")
        dedup_key = f"evt_{evt_id}" if evt_id else f"txt_{uid}_{hash(text)}"
        if not get_event_deduplicator().claim_event("markanm", dedup_key):
            logger.info(f"Duplicate MarkanM message dropped: {dedup_key}")
            return

        authed = is_authorized(user_info)

        # Master Password Fallback
        if not authed and text.startswith("/auth"):
            cand_pw = text.replace("/auth", "").strip()
            if cand_pw:
                success, msg = auth_mgr.authenticate_password("markanm", str(uid), str(uname), cand_pw)
                if success:
                    authed = True
                    await _safe_reply("✅ Identity verified successfully! Welcome back. Your MarkanM account is now authenticated and linked.")
                    return
                else:
                    await _safe_reply(msg)
                    return

        try:
            from gdr.safety.request_db import log_inbound_request
            log_inbound_request(
                ip_address=f"markanm:{uid}",
                method="MK_MSG",
                path="/markanm/chat",
                user_details={"username": uname, "user_id": uid, "text": text},
                status_code=200 if authed else 403,
                source="markanm"
            )
        except Exception:
            pass
        if not authed:
            unauth_msg = (
                f"🔒 Access restricted: Your MarkanM account (@{uname}) is not recognized. "
                "If you are the owner, please authenticate using `/auth <password>` to verify your session."
            )
            await _safe_reply(unauth_msg)
            return

        # Check if text is a command handled by @bot.command
        if text.startswith("/"):
            first_word = text.split()[0].lstrip("/").lower()
            if first_word in bot.commands:
                return  # Handled by @bot.command
            text = text.lstrip("/").strip()

        lower = text.lower().strip()
        if any(k in lower for k in ["pc health", "system health", "cpu", "vram", "ram usage", "battery level", "battery percentage", "computer health", "laptop status"]):
            from gdr.tools.system import system_health
            reply = system_health()
        elif any(k in lower for k in ["pending task", "what tasks", "tasks pending", "scheduled tasks", "reminders"]):
            from gdr.scheduler.store import get_job_store
            jobs = get_job_store().list_all()
            if jobs:
                items = [f"• {j.get('name', 'Job')} (Every {j.get('interval_minutes', 1)}m)" for j in jobs]
                reply = "📋 *Active Scheduled Tasks:*\n" + "\n".join(items)
            else:
                reply = "📋 No pending background scheduled tasks found."
        elif any(k in lower for k in ["what did i work on", "summary of today", "worked on today", "daily summary"]):
            from gdr.memory.daily_learning import get_daily_learning_manager
            reply = get_daily_learning_manager().generate_daily_summary()
        elif any(k in lower for k in ["take screenshot", "desktop screen", "screenshot"]):
            from gdr.tools.screen import take_screenshot
            shot_path = take_screenshot()
            reply = f"📸 Screenshot captured at {shot_path}." if shot_path else "Could not capture screen."
        else:
            try:
                session_id = f"mk_{r_id or 'general'}"
                from gdr.memory.store import get_memory_store
                mem_store = get_memory_store()
                mem_store.save_chat_message("user", text, session_id=session_id)
                reply = await asyncio.to_thread(agent.run, text, session_id=session_id, channel="markanm")
                reply = format_clean_bot_message(reply)
                mem_store.save_chat_message("assistant", reply, session_id=session_id)
            except Exception as ag_err:
                logger.error(f"Error running agent for MarkanM: {ag_err}")
                reply = f"⚠️ I encountered an error while processing: {ag_err}"

        await _safe_reply(reply)
        try:
            from gdr.safety.request_db import log_inbound_request
            log_inbound_request(
                ip_address=f"markanm:{uid}",
                method="MK_REPLY",
                path="/markanm/reply",
                body_payload={"prompt": text, "reply": reply},
                user_details={"username": uname, "user_id": uid, "prompt": text, "reply": reply},
                status_code=200,
                source="markanm"
            )
        except Exception:
            pass

    message_event_types = [
        "message.created",
        "message.received",
        "message_created",
        "message_received",
        "message",
        "new_message",
        "chat.message",
        "chat:message",
        "room.message",
        "message:created",
    ]
    for ev_type in message_event_types:
        @bot.on(ev_type)
        async def on_message_event(evt):
            await _handle_incoming_text_event(evt)

    @bot.on("command.received")
    async def on_command_fallback(evt):
        payload = evt.payload if isinstance(evt.payload, dict) else {}
        cmd_name = str(payload.get("command", "")).lstrip("/").strip().lower()
        if cmd_name not in bot.commands:
            await _handle_incoming_text_event(evt)

    return bot



def get_markanm_bot_status() -> str:
    """Return current lifecycle status of the MarkanM bot service."""
    return _MARKANM_STATUS


def _is_placeholder_token(token: str) -> bool:
    """Return True if the token looks like a test/placeholder value."""
    if not token:
        return True
    low = token.lower().strip()
    placeholder_markers = ["test", "mock", "sample", "dummy", "placeholder", "mkbot_test", "your_", "xxx", "***"]
    return any(m in low for m in placeholder_markers)


def start_markanm_bot_service(restart: bool = False) -> Dict[str, Any]:
    """Start MarkanM bot polling in a background daemon thread with process lock."""
    global _MARKANM_THREAD, _MARKANM_RUNNING, _MARKANM_BOT, _MARKANM_STATUS

    token = get_secret("MARKANM_BOT_TOKEN") or load_config().get("channels", {}).get("markanm_bot_token") or os.environ.get("MARKANM_BOT_TOKEN")
    if not token:
        _MARKANM_STATUS = "stopped"
        return {"success": False, "message": "MARKANM_BOT_TOKEN is not configured in secrets or env."}

    if _is_placeholder_token(token):
        _MARKANM_STATUS = "auth_failed"
        logger.warning("⛔ MarkanM bot not started: token is a placeholder/test value. Configure a real token.")
        return {"success": False, "message": "MarkanM token appears to be a placeholder. Set a real token via Settings."}

    from gdr.channels.bot_lock import BotProcessLock
    lock = BotProcessLock("markanm")

    if is_markanm_bot_running():
        if restart:
            stop_markanm_bot_service()
            time.sleep(0.5)
        else:
            return {"success": True, "message": "MarkanM bot service is already running in this process.", "status": _MARKANM_STATUS}

    acquired, lock_info = lock.acquire(owner_description="markanm-polling-worker")
    if not acquired:
        owner_pid = lock_info.get("pid") if isinstance(lock_info, dict) else lock_info
        _MARKANM_STATUS = "running"
        logger.info(f"MarkanM bot polling already locked by PID {owner_pid}; skipping duplicate worker.")
        return {
            "success": True,
            "message": f"MarkanM bot polling is already active in process PID {owner_pid}.",
            "running": True,
            "external_owner": True,
            "owner_pid": owner_pid,
            "status": "running"
        }

    _MARKANM_STATUS = "starting"

    def _runner():
        global _MARKANM_RUNNING, _MARKANM_BOT, _MARKANM_STATUS
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            _MARKANM_BOT = build_markanm_bot(token)
            _MARKANM_RUNNING = True
            _MARKANM_STATUS = "running"
            logger.info("🤖 MarkanM bot polling started.")
            # Run custom polling loop that aborts on 401/403 instead of spamming
            loop.run_until_complete(_safe_polling_loop(_MARKANM_BOT))
        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "unauthorized" in err_str.lower() or "invalid" in err_str.lower():
                _MARKANM_STATUS = "auth_failed"
                logger.error(f"⛔ MarkanM bot auth failed (401). Polling stopped. Reconfigure your token. Error: {e}")
            else:
                _MARKANM_STATUS = "error"
                logger.warning(f"MarkanM bot runner stopped: {e}")
        finally:
            _MARKANM_RUNNING = False
            if _MARKANM_STATUS == "running":
                _MARKANM_STATUS = "stopped"
            lock.release()

    async def _safe_polling_loop(bot):
        """Custom polling loop that stops cleanly on 401/403 auth errors."""
        global _MARKANM_RUNNING, _MARKANM_STATUS
        from markanm.exceptions import MarkanMAuthError, MarkanMError
        from markanm import Event
        import time as _time

        # Pre-validate token before entering poll loop
        try:
            await bot.client.get("/me")
        except Exception as pre_err:
            pre_str = str(pre_err)
            if "401" in pre_str or "403" in pre_str or "unauthorized" in pre_str.lower():
                _MARKANM_STATUS = "auth_failed"
                _MARKANM_RUNNING = False
                logger.error(f"⛔ MarkanM token invalid (pre-flight check failed). Stopping. {pre_err}")
                return
            # Network/timeout issues: continue anyway and let poll loop handle

        poll_count = 0
        interval = 2.0
        while _MARKANM_RUNNING:
            try:
                res = await bot.client.post("/polling")
                events_data = res.get("events", [])
                if events_data:
                    for evt_raw in events_data:
                        event = Event(evt_raw)
                        await bot.dispatch_event(event)
                poll_count += 1
                if poll_count % 30 == 0:
                    logger.debug(f"MarkanM polling active ({poll_count * interval:.0f}s elapsed)")
            except MarkanMAuthError as auth_err:
                # 401/403: stop immediately, do NOT loop
                _MARKANM_STATUS = "auth_failed"
                _MARKANM_RUNNING = False
                logger.error(f"⛔ MarkanM auth failed: {auth_err}. Polling stopped. Go to Settings → Bot Tokens to reconfigure.")
                return
            except MarkanMError as mk_err:
                # Other API errors: log once, back off, keep trying
                logger.warning(f"MarkanM API error (will retry): {mk_err}")
                await asyncio.sleep(interval * 3)
            except Exception as exc:
                if not _MARKANM_RUNNING:
                    break
                logger.debug(f"MarkanM polling transient error: {exc}")
                await asyncio.sleep(interval)
            await asyncio.sleep(interval)

    _MARKANM_THREAD = threading.Thread(target=_runner, daemon=True, name="MarkanMBotThread")
    _MARKANM_THREAD.start()

    return {"success": True, "message": "MarkanM bot service started in background.", "status": "starting"}


def stop_markanm_bot_service() -> bool:
    """Stop the running MarkanM bot service and release lock."""
    global _MARKANM_RUNNING, _MARKANM_BOT, _MARKANM_THREAD, _MARKANM_STATUS
    _MARKANM_RUNNING = False
    _MARKANM_STATUS = "stopped"
    if _MARKANM_BOT and hasattr(_MARKANM_BOT, "stop"):
        try:
            _MARKANM_BOT.stop()
        except Exception:
            pass
    if _MARKANM_THREAD and _MARKANM_THREAD.is_alive():
        _MARKANM_THREAD.join(timeout=1.5)
    from gdr.channels.bot_lock import BotProcessLock
    BotProcessLock("markanm").release()
    _MARKANM_THREAD = None
    _MARKANM_BOT = None
    return True

