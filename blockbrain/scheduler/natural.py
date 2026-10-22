"""Natural language scheduling parser for blockbrain AI.
Converts expressions like 'remind me at 7am' or 'every weekday 9am summarize my email' into structured jobs.
"""

from datetime import datetime, timedelta
import re
from typing import Dict, Any, Optional, Tuple
from croniter import croniter


def parse_natural_schedule(text: str) -> Optional[Dict[str, Any]]:
    """Parse text into a structured scheduled job."""
    raw = text.strip()
    low = raw.lower()

    now = datetime.now()

    # 1. "every weekday [at] 9am ..." -> cron "0 9 * * 1-5"
    m_weekday = re.search(r"every\s+weekday\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", low)
    if m_weekday:
        hour = int(m_weekday.group(1))
        minute = int(m_weekday.group(2) or 0)
        ampm = m_weekday.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        cron_expr = f"{minute} {hour} * * 1-5"
        itr = croniter(cron_expr, now)
        next_run = itr.get_next(datetime)

        # Extract task description
        task = re.sub(r"^.*?every\s+weekday\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*(?:to\s+)?", "", raw, flags=re.I).strip()
        task = task or "Scheduled routine"
        return {
            "description": task,
            "prompt": task,
            "schedule_type": "cron",
            "schedule_expr": cron_expr,
            "next_run_at": next_run,
            "is_reminder_only": False if any(w in task.lower() for w in ["check", "summarize", "run", "backup", "download"]) else True
        }

    # 2. "every day at 8am ..." -> cron "0 8 * * *"
    m_daily = re.search(r"every\s+(?:day|morning|evening)\s+(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", low)
    if m_daily:
        hour = int(m_daily.group(1))
        minute = int(m_daily.group(2) or 0)
        ampm = m_daily.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        cron_expr = f"{minute} {hour} * * *"
        itr = croniter(cron_expr, now)
        next_run = itr.get_next(datetime)

        task = re.sub(r"^.*?every\s+(?:day|morning|evening)\s+(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*(?:to\s+)?", "", raw, flags=re.I).strip()
        task = task or "Daily routine"
        return {
            "description": task,
            "prompt": task,
            "schedule_type": "cron",
            "schedule_expr": cron_expr,
            "next_run_at": next_run,
            "is_reminder_only": False if any(w in task.lower() for w in ["check", "summarize", "run", "backup", "download"]) else True
        }

    # 3. Relative timers: "in 10 minutes", "in 1 hour", "in 30 seconds"
    m_in = re.search(r"in\s+(\d+)\s*(minutes|minute|min|m|hours|hour|hr|h|seconds|second|sec|s)", low)
    if m_in:
        val = int(m_in.group(1))
        unit = m_in.group(2)
        if "h" in unit:
            delta = timedelta(hours=val)
        elif "s" in unit:
            delta = timedelta(seconds=val)
        else:
            delta = timedelta(minutes=val)

        target_time = now + delta
        task = re.sub(r"^.*?in\s+\d+\s*(?:minutes|minute|min|m|hours|hour|hr|h|seconds|second|sec|s)\s*(?:to\s+)?", "", raw, flags=re.I).strip()
        task = task or f"Timer ({val} {unit})"
        return {
            "description": task,
            "prompt": task,
            "schedule_type": "in",
            "schedule_expr": str(int(delta.total_seconds())),
            "next_run_at": target_time,
            "is_reminder_only": True
        }

    # 4. Specific time: "at 7am", "at 18:30", "at 7:30 pm"
    m_at = re.search(r"(?:at\s+)(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", low)
    if m_at:
        hour = int(m_at.group(1))
        minute = int(m_at.group(2) or 0)
        ampm = m_at.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0

        target_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target_time <= now:
            # Schedule for tomorrow if time already passed today
            target_time += timedelta(days=1)

        task = re.sub(r"^.*?(?:remind\s+me\s+)?at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?\s*(?:to\s+)?", "", raw, flags=re.I).strip()
        task = task or f"Reminder at {target_time.strftime('%I:%M %p')}"
        return {
            "description": task,
            "prompt": task,
            "schedule_type": "at",
            "schedule_expr": target_time.isoformat(),
            "next_run_at": target_time,
            "is_reminder_only": True
        }

    return None
