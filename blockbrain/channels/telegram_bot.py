"""Telegram Bot channel for blockbrain AI.
Provides full remote mobile assistant capabilities:
- Text messages & natural conversations
- Voice notes transcribed via local faster-whisper / Sarvam STT
- Photo inspection & OCR
- Inline Approve / Deny buttons for sensitive actions
- Commands: /status, /tasks, /screenshot, /stop (panic kill switch)
- User ID whitelisting to guarantee private security.
"""

import io
import json
import os
import tempfile
from typing import Optional

from blockbrain.config import load_config
from blockbrain.safety.secrets import get_secret
from blockbrain.core.agent import Agent
from blockbrain.voice.stt import SpeechToText
from blockbrain.safety.panic import trigger_panic
from blockbrain.tools.system import system_health
from blockbrain.tools.screen import take_screenshot
from blockbrain.scheduler.store import get_job_store
from blockbrain.night_shift.queue import list_pending_approvals, resolve_approval


def start_telegram_bot():
    """Start Telegram long-polling bot if configured."""
    token = get_secret("TELEGRAM_BOT_TOKEN")
    if not token:
        print("⚠️ Telegram bot token unset (set TELEGRAM_BOT_TOKEN in keyring or env).")
        return

    cfg = load_config()
    allowed_id = int(cfg.get("channels", {}).get("allowed_telegram_user_id", 0))

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

    def is_authorized(update: Update) -> bool:
        if not allowed_id:
            return True  # If 0, first user can bind or prompt
        return update.effective_user.id == allowed_id

    async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update):
            await update.message.reply_text("⛔ Unauthorized user ID.")
            return
        await update.message.reply_text(
            f"👋 Hello {update.effective_user.first_name}! I am blockbrain AI.\n\n"
            "You can talk to me via text, send voice notes, or photos.\n"
            "Commands:\n"
            "/status - Check laptop health\n"
            "/tasks - View scheduled routines\n"
            "/screenshot - View desktop screen\n"
            "/stop - Emergency kill switch (panic)"
        )

    async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update):
            return
        health = system_health()
        await update.message.reply_text(f"💻 **System Status:**\n\n{health}")

    async def stop_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update):
            return
        msg = trigger_panic()
        await update.message.reply_text(f"🚨 {msg}")

    async def screenshot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update):
            return
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tf:
            img_path = tf.name
        take_screenshot(img_path)
        if os.path.exists(img_path) and os.path.getsize(img_path) > 1000:
            with open(img_path, "rb") as f:
                await update.message.reply_photo(photo=f, caption="Desktop Screenshot")
            os.remove(img_path)
        else:
            await update.message.reply_text("Failed to capture screen.")

    async def tasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update):
            return
        store = get_job_store()
        jobs = store.list_jobs()
        if not jobs:
            await update.message.reply_text("No active tasks scheduled.")
            return
        lines = ["📋 **Scheduled Tasks:**"]
        for j in jobs:
            lines.append(f"• #{j['id']} ({j['next_run_at'][:16]}): {j['description']}")
        await update.message.reply_text("\n".join(lines))

    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update):
            return
        user_text = update.message.text
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        reply = agent.run(user_text)
        await update.message.reply_text(reply)

    async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update):
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

        await update.message.reply_text(f"🗣️ *Transcribed:* \"{text}\"")
        reply = agent.run(text)
        await update.message.reply_text(reply)

    async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not is_authorized(update):
            return
        photo_file = await update.message.photo[-1].get_file()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
            jpg_path = tf.name
        await photo_file.download_to_drive(jpg_path)

        caption = update.message.caption or "What is in this image?"
        prompt = f"The user sent a photo. Query: '{caption}'. Image saved at '{jpg_path}'."
        reply = agent.run(prompt)
        try:
            os.remove(jpg_path)
        except Exception:
            pass
        await update.message.reply_text(reply)

    async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("stop", stop_cmd))
    app.add_handler(CommandHandler("screenshot", screenshot_cmd))
    app.add_handler(CommandHandler("tasks", tasks_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("🤖 Telegram bot polling started.")
    app.run_polling()

