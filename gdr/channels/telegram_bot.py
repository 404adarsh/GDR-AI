"""Telegram Bot channel for GDR AI & Aarushi Companion.
Provides full remote mobile assistant capabilities:
- Text messages & natural conversations with Aarushi
- Voice notes transcribed via local faster-whisper / Sarvam STT
- Photo inspection & OCR
- Inline Approve / Deny buttons for sensitive actions
- Outbound alerts, reminders, and briefing notifications
- Remote voice call/alarm escalation (/callme)
- Commands: /status, /tasks, /screenshot, /remind, /callme, /stop (panic kill switch)
- User ID whitelisting to guarantee private security.
"""

import asyncio
import io
import json
import logging
import os
import tempfile
import threading
from typing import Optional, Dict, Any, List

from gdr.config import load_config, save_config
from gdr.safety.secrets import get_secret
from gdr.core.agent import Agent
from gdr.voice.stt import SpeechToText
from gdr.safety.panic import trigger_panic
from gdr.tools.system import system_health
from gdr.tools.screen import take_screenshot
from gdr.scheduler.store import get_job_store
from gdr.night_shift.queue import list_pending_approvals, resolve_approval
from gdr.channels.format_utils import format_clean_bot_message

logger = logging.getLogger("gdr.channels.telegram_bot")

_TELEGRAM_THREAD: Optional[threading.Thread] = None
_TELEGRAM_RUNNING: bool = False
_TELEGRAM_APP = None
_TELEGRAM_LOOP = None


def is_telegram_bot_running() -> bool:
    """Return whether the Telegram bot polling service is active."""
    global _TELEGRAM_RUNNING, _TELEGRAM_THREAD
    return bool(_TELEGRAM_RUNNING and _TELEGRAM_THREAD and _TELEGRAM_THREAD.is_alive())


def validate_telegram_token(token: Optional[str] = None) -> Dict[str, Any]:
    """Validate a Telegram bot token against api.telegram.org/bot<token>/getMe."""
    tok = token or get_secret("TELEGRAM_BOT_TOKEN")
    if not tok:
        return {"valid": False, "error": "Token is empty"}
    try:
        import urllib.request
        import json
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{tok}/getMe",
            headers={"User-Agent": "gdr-ai/2.0"}
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("ok"):
                result = data.get("result", {})
                return {
                    "valid": True,
                    "bot": {
                        "id": result.get("id"),
                        "username": result.get("username", ""),
                        "first_name": result.get("first_name", ""),
                        "can_join_groups": result.get("can_join_groups", False),
                        "can_read_all_group_messages": result.get("can_read_all_group_messages", False)
                    }
                }
            return {"valid": False, "error": data.get("description", "API rejected token")}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def send_telegram_test_message(text: str = "", chat_id: Optional[str] = None, message: Optional[str] = None) -> Dict[str, Any]:
    """Send a fast test message to Telegram with precise latency measurement and detailed feedback."""
    import time
    t0 = time.time()
    text = format_clean_bot_message(text or message or "")

    token = get_secret("TELEGRAM_BOT_TOKEN") or load_config().get("channels", {}).get("telegram_bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return {"success": False, "message": "TELEGRAM_BOT_TOKEN is not configured in secrets.", "elapsed_ms": 0}

    cfg = load_config()
    target_chat_id = chat_id or get_secret("TELEGRAM_CHAT_ID") or cfg.get("channels", {}).get("allowed_telegram_user_id") or cfg.get("channels", {}).get("telegram_chat_id")
    if not target_chat_id or str(target_chat_id) in ("0", ""):
        return {
            "success": False,
            "message": "No destination Chat ID configured. Either enter your numeric Telegram user ID or send any message to the bot first to auto-bind.",
            "elapsed_ms": 0
        }

    try:
        import urllib.request
        import json
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "gdr-ai/2.0"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=7) as resp:
                elapsed_ms = int((time.time() - t0) * 1000)
                resp_data = json.loads(resp.read().decode("utf-8"))
                success = bool(resp_data.get("ok"))
        except urllib.error.HTTPError as err:
            # Fallback to plain text if Markdown parsing failed
            payload.pop("parse_mode", None)
            data_bytes = json.dumps(payload).encode("utf-8")
            req2 = urllib.request.Request(
                url,
                data=data_bytes,
                headers={"Content-Type": "application/json", "User-Agent": "gdr-ai/2.0"},
                method="POST"
            )
            with urllib.request.urlopen(req2, timeout=6) as resp2:
                elapsed_ms = int((time.time() - t0) * 1000)
                resp_data = json.loads(resp2.read().decode("utf-8"))
                success = bool(resp_data.get("ok"))

        try:
            from gdr.safety.request_db import log_inbound_request
            log_inbound_request(
                ip_address=f"telegram:{target_chat_id}",
                method="TG_TEST",
                path="/telegram/test",
                body_payload={"text": text, "chat_id": str(target_chat_id), "latency_ms": elapsed_ms},
                user_details={"chat_id": str(target_chat_id), "type": "test_message", "elapsed_ms": elapsed_ms},
                status_code=200 if success else 400,
                source="telegram"
            )
        except Exception:
            pass

        if success:
            return {
                "success": True,
                "delivered": True,
                "message": f"Test message delivered successfully in {elapsed_ms}ms!",
                "elapsed_ms": elapsed_ms,
                "chat_id": str(target_chat_id),
                "recipient": str(target_chat_id)
            }
        return {
            "success": False,
            "message": "Telegram API rejected message. Verify destination chat ID.",
            "elapsed_ms": int((time.time() - t0) * 1000)
        }
    except Exception as e:
        elapsed_ms = int((time.time() - t0) * 1000)
        logger.warning(f"Failed to send Telegram test message: {e}")
        return {
            "success": False,
            "message": f"Delivery failed ({e}). Check bot token & ensure chat ID is correct.",
            "elapsed_ms": elapsed_ms
        }


def send_telegram_message(text: str, chat_id: Optional[str] = None) -> bool:
    """Send an outbound text message to the user via Telegram."""
    res = send_telegram_test_message(text, chat_id=chat_id)
    return bool(res.get("success", False))


def send_telegram_voice(audio_path: str, caption: str = "", chat_id: Optional[str] = None) -> bool:
    """Send an outbound voice message / voice note to user's Telegram."""
    token = get_secret("TELEGRAM_BOT_TOKEN")
    if not token or not os.path.exists(audio_path):
        return False

    cfg = load_config()
    target_chat_id = chat_id or get_secret("TELEGRAM_CHAT_ID") or cfg.get("channels", {}).get("allowed_telegram_user_id") or cfg.get("channels", {}).get("telegram_chat_id")
    if not target_chat_id or str(target_chat_id) in ("0", ""):
        return False

    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/sendVoice"
        with open(audio_path, "rb") as f:
            files = {"voice": f}
            data = {"chat_id": target_chat_id, "caption": caption}
            resp = requests.post(url, data=data, files=files, timeout=20)
            success = (resp.status_code == 200)

        try:
            from gdr.safety.request_db import log_inbound_request
            log_inbound_request(
                ip_address=f"telegram:{target_chat_id}",
                method="TG_VOICE_OUTBOUND",
                path="/telegram/send_voice",
                body_payload={"audio_path": audio_path, "caption": caption, "chat_id": str(target_chat_id)},
                user_details={"chat_id": str(target_chat_id), "type": "outbound_voice", "caption": caption},
                status_code=200 if success else 500,
                source="telegram"
            )
        except Exception:
            pass

        return success
    except Exception as e:
        logger.warning(f"Failed to send Telegram voice: {e}")
        return False


def create_telegram_application():
    """Build and configure the python-telegram-bot application."""
    token = get_secret("TELEGRAM_BOT_TOKEN") or load_config().get("channels", {}).get("telegram_bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return None

    cfg = load_config()
    raw_allowed_id = cfg.get("channels", {}).get("allowed_telegram_user_id", 0)
    try:
        allowed_id = int(raw_allowed_id)
    except (ValueError, TypeError):
        allowed_id = 0

    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        ApplicationBuilder,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ContextTypes,
        filters,
    )

    app = ApplicationBuilder().token(token).build()
    agent = Agent()
    stt = SpeechToText()

    from gdr.safety.auth import get_channel_auth_manager, normalize_username
    auth_mgr = get_channel_auth_manager()

    UNAUTHORIZED_MSG = (
        "🔒 Access restricted: Your Telegram account is not recognized. "
        "If you are the owner, please authenticate using `/auth <password>` to verify your session."
    )

    def is_authorized(update: Update) -> bool:
        user = update.effective_user
        if not user:
            return False
        uid = str(user.id)
        u_name = user.username or ""
        cfg = load_config()
        authed, _ = auth_mgr.is_authorized("telegram", user_id=uid, username=u_name, config=cfg)
        return authed

    async def check_and_reject(update: Update) -> bool:
        u_id = getattr(update, "update_id", None)
        if u_id is not None:
            try:
                from gdr.safety.idempotency import get_event_deduplicator
                if not get_event_deduplicator().claim_event("telegram", f"upd_{u_id}"):
                    logger.info(f"Duplicate Telegram update {u_id} skipped.")
                    return False
            except Exception as e:
                logger.debug(f"Dedup check error: {e}")

        u = update.effective_user
        raw_t = getattr(update.message, "text", None) if update.message else None
        u_text = raw_t if isinstance(raw_t, str) else ""
        authed = is_authorized(update)

        # Check for explicit password attempt inside message
        if not authed and u and u_text:
            parts = u_text.strip().split()
            cand_pw = None
            if len(parts) >= 2 and parts[0] in ("/auth", "/login"):
                cand_pw = parts[1]
            elif u_text.strip().startswith("/auth"):
                cand_pw = u_text.replace("/auth", "").strip()

            if cand_pw:
                success, msg = auth_mgr.authenticate_password(
                    "telegram",
                    user_id=str(u.id),
                    username=u.username,
                    candidate_password=cand_pw
                )
                if success:
                    authed = True
                    if update.message:
                        await update.message.reply_text(
                            "✅ Identity verified successfully! Welcome back. Your Telegram account is now authenticated and linked."
                        )
                else:
                    if update.message:
                        await update.message.reply_text(msg)
                    return False

        try:
            from gdr.safety.request_db import log_inbound_request
            log_inbound_request(
                ip_address=f"telegram:{u.id if u else 'unknown'}",
                method="TG_CMD" if u_text.startswith("/") else "TG_MSG",
                path=u_text.split()[0] if u_text.startswith("/") else "/telegram/message",
                user_details={
                    "user_id": u.id if u else None,
                    "username": u.username if u else None,
                    "first_name": u.first_name if u else None,
                    "text": u_text
                },
                status_code=200 if authed else 403,
                source="telegram"
            )
        except Exception:
            pass

        if authed:
            return True
        if update.message:
            await update.message.reply_text(UNAUTHORIZED_MSG, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer(UNAUTHORIZED_MSG, show_alert=True)
        return False

    async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await check_and_reject(update):
            return
        await update.message.reply_text(
            f"🌸 *Hello {update.effective_user.first_name}! I am Aarushi.*\n\n"
            "I'm connected to your laptop! You can chat with me, send voice notes, photos, or control your system.\n\n"
            "📋 *Commands:*\n"
            "• `/status` - Live laptop health, battery & VRAM\n"
            "• `/screenshot` - Real-time desktop screen snapshot\n"
            "• `/remind <time> <text>` - Schedule a reminder or task\n"
            "• `/callme` - Trigger alarm / emergency phone call\n"
            "• `/tasks` - View scheduled background tasks\n"
            "• `/stop` - Emergency panic kill-switch\n"
            "• `/help` - Show all commands\n\n"
            "💬 *Or just send me any text or voice note—I'm right here with you!* ❤️",
            parse_mode="Markdown"
        )

    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await start_cmd(update, context)

    async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await check_and_reject(update):
            return
        health = system_health()
        await update.message.reply_text(f"💻 *System Status:*\n\n```\n{health}\n```", parse_mode="Markdown")

    async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await check_and_reject(update):
            return
        msg = trigger_panic()
        await update.message.reply_text(f"🚨 *PANIC TRIGGERED:*\n{msg}", parse_mode="Markdown")

    async def screenshot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await check_and_reject(update):
            return
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            img_path = tf.name
        take_screenshot(img_path)
        if os.path.exists(img_path) and os.path.getsize(img_path) > 1000:
            with open(img_path, "rb") as f:
                await update.message.reply_photo(photo=f, caption="🖥️ Desktop Screen Snapshot")
            try:
                os.remove(img_path)
            except Exception:
                pass
        else:
            await update.message.reply_text("❌ Failed to capture screen.")

    async def tasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await check_and_reject(update):
            return
        store = get_job_store()
        jobs = store.list_jobs()
        if not jobs:
            await update.message.reply_text("📋 No active tasks scheduled.")
            return
        lines = ["📋 *Scheduled Tasks:*"]
        for j in jobs:
            lines.append(f"• #{j['id']} ({j['next_run_at'][:16]}): {j['description']}")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def remind_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await check_and_reject(update):
            return
        args = context.args
        if not args:
            await update.message.reply_text("Usage: `/remind <time e.g. 10m or 14:30> <message>`", parse_mode="Markdown")
            return
        prompt = f"Set a reminder for {args[0]}: {' '.join(args[1:])}"
        reply = agent.run(prompt)
        await update.message.reply_text(reply)

    async def callme_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await check_and_reject(update):
            return
        await update.message.reply_text("📞 Triggering immediate call / alert escalation to your phone...")
        from gdr.channels.phone import call_phone_with_escalation
        res = call_phone_with_escalation("Urgent escalation requested via Telegram /callme command.")
        await update.message.reply_text(f"📢 Escalation result: {res}")

    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await check_and_reject(update):
            return
        user_text = update.message.text or ""
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # Natural language intent detection without requiring strict slash commands
        lower = user_text.lower().strip()
        if any(k in lower for k in ["pc health", "system health", "cpu", "vram", "ram usage", "battery level", "battery percentage", "computer health", "laptop status"]):
            from gdr.tools.system import system_health
            reply = system_health()
        elif any(k in lower for k in ["pending task", "what tasks", "tasks pending", "scheduled tasks", "active tasks"]):
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
            if shot_path and os.path.exists(shot_path):
                with open(shot_path, "rb") as pf:
                    await update.message.reply_photo(photo=pf, caption="📸 Current desktop screen snapshot.")
                return
            reply = "Could not capture screen."
        else:
            chat_id_str = f"tg_{update.effective_chat.id}"
            from gdr.memory.store import get_memory_store
            mem_store = get_memory_store()
            mem_store.save_chat_message("user", user_text, session_id=chat_id_str)
            reply = await asyncio.to_thread(agent.run, user_text, session_id=chat_id_str, channel="telegram")
            reply = format_clean_bot_message(reply)
            mem_store.save_chat_message("assistant", reply, session_id=chat_id_str)

        await update.message.reply_text(reply)
        try:
            from gdr.safety.request_db import log_inbound_request
            u = update.effective_user
            log_inbound_request(
                ip_address=f"telegram:{u.id if u else 'unknown'}",
                method="TG_REPLY",
                path="/telegram/reply",
                body_payload={"prompt": user_text, "reply": reply},
                user_details={"username": u.username if u else None, "user_id": u.id if u else None, "prompt": user_text, "reply": reply},
                status_code=200,
                source="telegram"
            )
        except Exception:
            pass

    async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await check_and_reject(update):
            return
        voice_file = await update.message.voice.get_file()
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tf:
            ogg_path = tf.name
        await voice_file.download_to_drive(ogg_path)

        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        text = stt.transcribe(ogg_path)
        try:
            os.remove(ogg_path)
        except Exception:
            pass

        if not text:
            await update.message.reply_text("Could not transcribe voice note.")
            return

        await update.message.reply_text(f"🗣️ *Heard:* \"{text}\"", parse_mode="Markdown")
        chat_id_str = f"tg_{update.effective_chat.id}"
        from gdr.memory.store import get_memory_store
        mem_store = get_memory_store()
        mem_store.save_chat_message("user", text, session_id=chat_id_str)
        reply = await asyncio.to_thread(agent.run, text, session_id=chat_id_str, channel="telegram")
        reply = format_clean_bot_message(reply)
        mem_store.save_chat_message("assistant", reply, session_id=chat_id_str)
        await update.message.reply_text(reply)
        try:
            from gdr.safety.request_db import log_inbound_request
            u = update.effective_user
            log_inbound_request(
                ip_address=f"telegram:{u.id if u else 'unknown'}",
                method="TG_REPLY",
                path="/telegram/reply",
                body_payload={"prompt": text, "reply": reply, "input_type": "voice"},
                user_details={"username": u.username if u else None, "user_id": u.id if u else None, "prompt": text, "reply": reply},
                status_code=200,
                source="telegram"
            )
        except Exception:
            pass

    async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await check_and_reject(update):
            return
        photo_file = await update.message.photo[-1].get_file()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
            jpg_path = tf.name
        await photo_file.download_to_drive(jpg_path)

        caption = update.message.caption or "What is in this image?"
        prompt = f"The user sent a photo. Query: '{caption}'. Image saved at '{jpg_path}'."
        reply = await asyncio.to_thread(agent.run, prompt)
        reply = format_clean_bot_message(reply)
        try:
            os.remove(jpg_path)
        except Exception:
            pass
        await update.message.reply_text(reply)
        try:
            from gdr.safety.request_db import log_inbound_request
            u = update.effective_user
            log_inbound_request(
                ip_address=f"telegram:{u.id if u else 'unknown'}",
                method="TG_REPLY",
                path="/telegram/reply",
                body_payload={"prompt": caption, "reply": reply, "input_type": "photo"},
                user_details={"username": u.username if u else None, "user_id": u.id if u else None, "prompt": caption, "reply": reply},
                status_code=200,
                source="telegram"
            )
        except Exception:
            pass

    async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await check_and_reject(update):
            return
        query = update.callback_query
        await query.answer()
        data = query.data
        if data.startswith("appr_"):
            parts = data.split(":")
            item_id = parts[0]
            action = parts[1]
            success = resolve_approval(item_id, approved=(action == "yes"))
            status_text = "Approved ✅" if action == "yes" else "Denied ❌"
            await query.edit_message_text(f"Action #{item_id}: {status_text}")

    async def auth_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        u = update.effective_user
        if not u:
            return
        args_list = getattr(context, "args", []) or []
        candidate_pw = " ".join([str(a) for a in args_list if isinstance(a, str)]).strip()
        if not candidate_pw and update.message:
            raw_t = getattr(update.message, "text", None)
            if isinstance(raw_t, str):
                parts = raw_t.strip().split()
                if len(parts) >= 2:
                    candidate_pw = parts[1]

        if not candidate_pw:
            await update.message.reply_text(
                "🔑 Please provide your password:\n`/auth <password>`",
                parse_mode="Markdown"
            )
            return

        success, msg = auth_mgr.authenticate_password(
            "telegram",
            user_id=str(u.id),
            username=u.username,
            candidate_password=candidate_pw
        )
        if success:
            await update.message.reply_text(
                "✅ Identity verified successfully! Welcome back. Your Telegram account is now authenticated and linked."
            )
        else:
            await update.message.reply_text(msg)

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("auth", auth_cmd))
    app.add_handler(CommandHandler("login", auth_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler("screenshot", screenshot_cmd))
    app.add_handler(CommandHandler("tasks", tasks_cmd))
    app.add_handler(CommandHandler("remind", remind_cmd))
    app.add_handler(CommandHandler("callme", callme_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))

    return app


def start_telegram_bot_service(restart: bool = False) -> Dict[str, Any]:
    """Start Telegram bot long-polling in a background thread with inter-process lock protection."""
    global _TELEGRAM_THREAD, _TELEGRAM_RUNNING, _TELEGRAM_APP, _TELEGRAM_LOOP

    token = get_secret("TELEGRAM_BOT_TOKEN") or load_config().get("channels", {}).get("telegram_bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        return {"success": False, "message": "TELEGRAM_BOT_TOKEN is not configured in secrets or env."}

    # Reject placeholder/test tokens before attempting to poll
    _placeholder_markers = ["test_token", "sample", "mock", "dummy", "placeholder", "your_", "xxx", "***"]
    if any(m in token.lower() for m in _placeholder_markers):
        logger.warning("⛔ Telegram bot not started: token is a placeholder. Set a real token via Settings.")
        return {"success": False, "message": "Telegram token appears to be a placeholder. Set a real token via Settings → Bot Tokens."}

    from gdr.channels.bot_lock import BotProcessLock
    lock = BotProcessLock("telegram")

    if is_telegram_bot_running():
        if restart:
            stop_telegram_bot_service()
            import time
            time.sleep(0.5)
        else:
            return {"success": True, "message": "Telegram bot service is already running in this process."}

    # Inter-process lock: verify no competing Python process is polling
    acquired, lock_info = lock.acquire(owner_description="telegram-polling-worker")
    if not acquired:
        owner_pid = lock_info.get("pid")
        owner_desc = lock_info.get("owner", "another process")
        logger.info(f"Telegram polling already managed by PID {owner_pid} ({owner_desc}). Reusing active worker.")
        return {
            "success": True,
            "message": f"Telegram bot polling is already active in process PID {owner_pid}.",
            "running": True,
            "external_owner": True,
            "owner_pid": owner_pid
        }

    def _runner():
        global _TELEGRAM_RUNNING, _TELEGRAM_APP, _TELEGRAM_LOOP
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _TELEGRAM_LOOP = loop
        try:
            _TELEGRAM_APP = create_telegram_application()
            if not _TELEGRAM_APP:
                _TELEGRAM_RUNNING = False
                lock.release()
                return
            _TELEGRAM_RUNNING = True
            logger.info("🤖 Telegram bot polling started.")
            # stop_signals=None prevents signal handler crash on non-main threads
            _TELEGRAM_APP.run_polling(stop_signals=None, close_loop=False)
        except Exception as e:
            err_str = str(e)
            if "conflict" in err_str.lower() or "terminated by other getupdates request" in err_str.lower():
                logger.warning(f"⚠️ Telegram bot polling conflict: {e}. Polling aborted cleanly to prevent retry loop.")
            elif "invalid token" in err_str.lower() or "unauthorized" in err_str.lower() or "401" in err_str:
                logger.error(f"⛔ Telegram bot auth failed: {e}. Polling stopped. Go to Settings → Bot Tokens to reconfigure.")
            else:
                logger.warning(f"Telegram bot runner stopped: {e}")
        finally:
            _TELEGRAM_RUNNING = False
            _TELEGRAM_LOOP = None
            lock.release()

    _TELEGRAM_THREAD = threading.Thread(target=_runner, daemon=True, name="TelegramBotThread")
    _TELEGRAM_THREAD.start()

    return {"success": True, "message": "Telegram bot service started in background."}


def stop_telegram_bot_service() -> bool:
    """Stop the running Telegram bot service and release process lock."""
    global _TELEGRAM_RUNNING, _TELEGRAM_APP, _TELEGRAM_LOOP, _TELEGRAM_THREAD
    _TELEGRAM_RUNNING = False
    if _TELEGRAM_APP and _TELEGRAM_LOOP and _TELEGRAM_LOOP.is_running():
        try:
            future = asyncio.run_coroutine_threadsafe(_TELEGRAM_APP.stop(), _TELEGRAM_LOOP)
            try:
                future.result(timeout=2.0)
            except Exception:
                pass
        except Exception as e:
            logger.debug(f"Error stopping Telegram application: {e}")

    if _TELEGRAM_THREAD and _TELEGRAM_THREAD.is_alive():
        _TELEGRAM_THREAD.join(timeout=2.0)

    from gdr.channels.bot_lock import BotProcessLock
    BotProcessLock("telegram").release()

    _TELEGRAM_THREAD = None
    _TELEGRAM_APP = None
    _TELEGRAM_LOOP = None
    return True


def start_telegram_bot():
    """CLI entrypoint for running Telegram bot in foreground."""
    app = create_telegram_application()
    if not app:
        print("⚠️ TELEGRAM_BOT_TOKEN not configured.")
        return
    print("🤖 Telegram bot polling started (Press Ctrl+C to stop).")
    app.run_polling()
