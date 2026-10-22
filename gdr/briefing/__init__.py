"""Briefing and alarm subsystem for GDR AI."""

from gdr.briefing.generator import generate_morning_briefing
from gdr.briefing.alarm import StagedAlarm
from gdr.briefing.wake import schedule_rtcwake, HARDWARE_LIMITS_DOC

__all__ = [
    "generate_morning_briefing",
    "StagedAlarm",
    "schedule_rtcwake",
    "HARDWARE_LIMITS_DOC",
]

