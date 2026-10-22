"""Briefing and alarm subsystem for blockbrain AI."""

from blockbrain.briefing.generator import generate_morning_briefing
from blockbrain.briefing.alarm import StagedAlarm
from blockbrain.briefing.wake import schedule_rtcwake, HARDWARE_LIMITS_DOC

__all__ = [
    "generate_morning_briefing",
    "StagedAlarm",
    "schedule_rtcwake",
    "HARDWARE_LIMITS_DOC",
]

