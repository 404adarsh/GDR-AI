"""Personal Care & Digital Wellbeing Subsystem for Aarushi AI.
Monitors continuous screen activity, evaluates gentle break reminders (default 50-60 min),
respects quiet hours and daily reminder limits, supports snoozing, and tracks daily breaks.
Framed strictly as practical ergonomics and wellness estimates, never clinical diagnosis.
"""

from datetime import datetime, date, time as dtime
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from gdr.tools.registry import tool

logger = logging.getLogger("gdr.system.wellbeing")

CONFIG_DIR = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr"))
WELLBEING_CONFIG_FILE = CONFIG_DIR / "wellbeing_settings.json"
WELLBEING_STATE_FILE = CONFIG_DIR / "wellbeing_state.json"


class WellbeingManager:
    """Manages continuous activity estimation, quiet hours, and break reminders."""

    DEFAULT_SETTINGS = {
        "enabled": True,
        "continuous_limit_minutes": 55,
        "break_duration_minutes": 5,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "08:00",
        "max_daily_reminders": 6,
        "spoken_reminders": False,
        "idle_threshold_seconds": 300,  # 5 min idle resets continuous session
    }

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or CONFIG_DIR
        self.settings_file = self.config_dir / "wellbeing_settings.json"
        self.state_file = self.config_dir / "wellbeing_state.json"

        self.settings = dict(self.DEFAULT_SETTINGS)
        self._load_settings()

        self.continuous_active_seconds = 0.0
        self.last_activity_time = datetime.now().timestamp()
        self.last_reminder_time = 0.0
        self.snooze_until = 0.0
        self.reminders_sent_today = 0
        self.breaks_taken_today = 0
        self.current_date = date.today().isoformat()
        self._load_state()

    def _load_settings(self):
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    data = json.load(f)
                    self.settings.update(data)
            except Exception:
                pass

    def save_settings(self, new_settings: Dict[str, Any]):
        self.settings.update(new_settings)
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.settings_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save wellbeing settings: {e}")

    def _load_state(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    if data.get("date") == date.today().isoformat():
                        self.continuous_active_seconds = data.get("continuous_active_seconds", 0.0)
                        self.reminders_sent_today = data.get("reminders_sent_today", 0)
                        self.breaks_taken_today = data.get("breaks_taken_today", 0)
                        self.snooze_until = data.get("snooze_until", 0.0)
            except Exception:
                pass

    def _persist_state(self):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "date": date.today().isoformat(),
                "continuous_active_seconds": self.continuous_active_seconds,
                "reminders_sent_today": self.reminders_sent_today,
                "breaks_taken_today": self.breaks_taken_today,
                "snooze_until": self.snooze_until,
                "last_activity_time": self.last_activity_time,
            }
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _check_day_rollover(self):
        today = date.today().isoformat()
        if today != self.current_date:
            self.current_date = today
            self.reminders_sent_today = 0
            self.breaks_taken_today = 0
            self.continuous_active_seconds = 0.0

    def is_in_quiet_hours(self) -> bool:
        """Check whether current local time is within configured quiet hours."""
        try:
            now_time = datetime.now().time()
            start_parts = [int(p) for p in self.settings.get("quiet_hours_start", "22:00").split(":")]
            end_parts = [int(p) for p in self.settings.get("quiet_hours_end", "08:00").split(":")]
            t_start = dtime(start_parts[0], start_parts[1])
            t_end = dtime(end_parts[0], end_parts[1])

            if t_start > t_end:
                # Spans across midnight, e.g. 22:00 to 08:00
                return now_time >= t_start or now_time <= t_end
            else:
                return t_start <= now_time <= t_end
        except Exception:
            return False

    def record_active_tick(self, interval_seconds: float = 30.0):
        """Called when user interaction or activity is detected."""
        self._check_day_rollover()
        now = datetime.now().timestamp()
        idle_threshold = self.settings.get("idle_threshold_seconds", 300)

        # If user was idle longer than threshold, reset continuous active session
        if (now - self.last_activity_time) > idle_threshold:
            self.continuous_active_seconds = interval_seconds
        else:
            self.continuous_active_seconds += interval_seconds

        self.last_activity_time = now
        self._persist_state()

    def record_idle_tick(self, interval_seconds: float = 30.0):
        """Called when system has been idle with no active input."""
        self._check_day_rollover()
        now = datetime.now().timestamp()
        idle_threshold = self.settings.get("idle_threshold_seconds", 300)

        if (now - self.last_activity_time) > idle_threshold:
            self.continuous_active_seconds = max(0.0, self.continuous_active_seconds - interval_seconds)
        self._persist_state()

    def check_break_due(self) -> Optional[str]:
        """Evaluate if continuous session exceeds limit and break reminder should fire."""
        if not self.settings.get("enabled", True):
            return None

        self._check_day_rollover()
        now = datetime.now().timestamp()

        # Respect quiet hours
        if self.is_in_quiet_hours():
            return None

        # Respect snooze
        if now < self.snooze_until:
            return None

        # Respect daily reminder limit
        max_rem = self.settings.get("max_daily_reminders", 6)
        if self.reminders_sent_today >= max_rem:
            return None

        limit_sec = self.settings.get("continuous_limit_minutes", 55) * 60
        if self.continuous_active_seconds >= limit_sec:
            # Trigger reminder
            active_min = int(self.continuous_active_seconds // 60)
            self.reminders_sent_today += 1
            self.last_reminder_time = now
            # Default auto-snooze for 15 minutes to prevent spamming
            self.snooze_until = now + (15 * 60)
            self._persist_state()

            break_min = self.settings.get("break_duration_minutes", 5)
            return (
                f"You've been active for approximately {active_min} minutes. "
                f"How about taking a gentle {break_min}-minute break to rest your eyes and stretch?"
            )

        return None

    def snooze(self, minutes: int = 10) -> str:
        """Snooze break reminders for a specified duration."""
        now = datetime.now().timestamp()
        self.snooze_until = now + (minutes * 60)
        self._persist_state()
        return f"Break reminder snoozed for {minutes} minutes."

    def record_break_taken(self, duration_minutes: int = 5) -> str:
        """User completed a break. Resets continuous active counter."""
        self._check_day_rollover()
        self.breaks_taken_today += 1
        self.continuous_active_seconds = 0.0
        self.snooze_until = 0.0
        self._persist_state()

        try:
            from gdr.system.timeline import get_timeline_tracker
            get_timeline_tracker().record_break_taken(duration_minutes)
        except Exception:
            pass

        return f"Nice work taking a break! Continuous session timer reset."

    def get_status(self) -> Dict[str, Any]:
        """Return current wellbeing status for UI and assistants."""
        self._check_day_rollover()
        active_min = int(self.continuous_active_seconds // 60)
        limit_min = self.settings.get("continuous_limit_minutes", 55)
        now = datetime.now().timestamp()
        is_snoozed = now < self.snooze_until
        snooze_remaining = int(max(0, self.snooze_until - now) // 60) if is_snoozed else 0

        return {
            "enabled": self.settings.get("enabled", True),
            "continuous_active_minutes": active_min,
            "continuous_limit_minutes": limit_min,
            "reminders_sent_today": self.reminders_sent_today,
            "max_daily_reminders": self.settings.get("max_daily_reminders", 6),
            "breaks_taken_today": self.breaks_taken_today,
            "is_in_quiet_hours": self.is_in_quiet_hours(),
            "is_snoozed": is_snoozed,
            "snooze_remaining_minutes": snooze_remaining,
            "settings": self.settings,
            "disclaimer": "Ergonomic wellbeing signals are practical estimates, not medical advice."
        }


_GLOBAL_WELLBEING_MANAGER: Optional[WellbeingManager] = None


def get_wellbeing_manager() -> WellbeingManager:
    global _GLOBAL_WELLBEING_MANAGER
    if _GLOBAL_WELLBEING_MANAGER is None:
        _GLOBAL_WELLBEING_MANAGER = WellbeingManager()
    return _GLOBAL_WELLBEING_MANAGER


# ==============================================================================
# LLM Accessible Tools
# ==============================================================================

@tool(name="get_wellbeing_status", category="wellbeing", tier="AUTO")
def get_wellbeing_status_tool() -> str:
    """Check current screen time, active session duration, breaks taken, and wellbeing settings."""
    wb = get_wellbeing_manager()
    status = wb.get_status()
    return json.dumps(status, indent=2)


@tool(name="snooze_break_reminder", category="wellbeing", tier="AUTO")
def snooze_break_reminder_tool(minutes: int = 10) -> str:
    """Snooze break reminders for a specified number of minutes (e.g. 10 or 15)."""
    wb = get_wellbeing_manager()
    return wb.snooze(minutes)


@tool(name="record_break_taken", category="wellbeing", tier="AUTO")
def record_break_taken_tool(duration_minutes: int = 5) -> str:
    """Record that the user took a restful break and reset continuous active timer."""
    wb = get_wellbeing_manager()
    return wb.record_break_taken(duration_minutes)

