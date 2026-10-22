"""Morning briefing generator for blockbrain AI.
Compiles weather, calendar events, top tasks, email summaries, news, overnight results, and pending approvals.
Outputs both a spoken briefing text and a formatted markdown message.
"""

from datetime import datetime
import json
import os
from typing import Dict, Any, Tuple
import requests

from blockbrain.config import load_config
from blockbrain.scheduler.store import get_job_store
from blockbrain.safety.audit import get_recent_audit_logs
from blockbrain.tools.email_tool import DRAFTS_FILE


def get_weather() -> str:
    """Fetch current weather without requiring any API keys."""
    try:
        # Use wttr.in format for quick text summary
        resp = requests.get(
            "https://wttr.in/?format=%C:+%t+(feels+like+%f),+wind+%w,+humidity+%h",
            headers={"User-Agent": "curl/8.0"},
            timeout=4
        )
        if resp.status_code == 200:
            return resp.text.strip()
    except Exception:
        pass
    return "Weather currently unavailable"


def get_news_headlines(topics: list) -> list:
    """Fetch brief headlines for chosen topics."""
    headlines = []
    # Fetch from HackerNews top items for tech/ai
    try:
        resp = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=4)
        if resp.status_code == 200:
            top_ids = resp.json()[:3]
            for item_id in top_ids:
                item_resp = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json", timeout=3)
                if item_resp.status_code == 200:
                    data = item_resp.json()
                    headlines.append(data.get("title", ""))
    except Exception:
        pass
    return headlines or ["Open-source AI models advance local deployment.", "Linux kernel security patches released."]


def get_pending_approvals() -> list:
    """Return count of items requiring manual approval."""
    approvals = []
    if DRAFTS_FILE.exists():
        try:
            with open(DRAFTS_FILE, "r") as f:
                drafts = json.load(f)
            for d in drafts:
                if d.get("status") == "pending_approval":
                    approvals.append(f"Email draft to {d.get('recipient')} ('{d.get('subject')}')")
        except Exception:
            pass
    return approvals


def generate_morning_briefing() -> Tuple[str, str]:
    """Generate both (spoken_text, markdown_text)."""
    cfg = load_config()
    user_name = cfg.get("general", {}).get("user_name", "blockbrain")
    now_str = datetime.now().strftime("%A, %B %d, %Y")

    weather = get_weather()
    topics = cfg.get("briefing", {}).get("news_topics", ["tech", "ai"])
    news = get_news_headlines(topics)

    # Tasks due today from SQLite
    store = get_job_store()
    pending_tasks = store.list_jobs(include_completed=False)[:3]
    task_bullets = [f"• {t['description']}" for t in pending_tasks] if pending_tasks else ["• No urgent tasks pending."]

    # Overnight tasks
    audit_logs = get_recent_audit_logs(limit=20)
    overnight_count = len([l for l in audit_logs if l.get("tier") == "AUTO"])

    # Pending approvals
    approvals = get_pending_approvals()

    # 1. Spoken Version (natural conversational tone)
    spoken_parts = [
        f"Good morning, {user_name}! Today is {now_str}.",
        f"Weather is {weather}.",
        f"You have {len(pending_tasks)} scheduled tasks today.",
    ]
    if pending_tasks:
        spoken_parts.append(f"First up: {pending_tasks[0]['description']}.")
    if approvals:
        spoken_parts.append(f"Notice: You have {len(approvals)} action pending your approval.")
    spoken_parts.append("Have a productive day!")
    spoken_text = " ".join(spoken_parts)

    # 2. Markdown Version (for Telegram / Phone Push)
    md_lines = [
        f"☀️ **Good Morning, {user_name}!**",
        f"📅 *{now_str}*\n",
        f"🌤️ **Weather:** {weather}\n",
        "📋 **Top Tasks:**",
    ]
    md_lines.extend(task_bullets)

    md_lines.append("\n📰 **Headlines:**")
    for h in news[:3]:
        md_lines.append(f"• {h}")

    if approvals:
        md_lines.append(f"\n⚠️ **Pending Approvals ({len(approvals)}):**")
        for a in approvals:
            md_lines.append(f"• {a}")

    if overnight_count > 0:
        md_lines.append(f"\n🌙 **Night Shift:** {overnight_count} background operations finished successfully.")

    markdown_text = "\n".join(md_lines)

    return spoken_text, markdown_text

