"""Authoritative Central Silence & Interaction Controller for GDR-AI and Aarushi.
Enforces quiet mode, user-mandated silence ("chup raho", "don't disturb"),
absolute-timestamp duration expiration, and prevents unsolicited background speech.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
import time
from typing import Dict, Any, Optional, Tuple


def _resolve_silence_state_file() -> Path:
    cfg = os.environ.get("GDR_CONFIG_DIR")
    if cfg:
        return Path(cfg) / "silence_state.json"
    p = Path.home() / ".config" / "gdr" / "silence_state.json"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        t = p.parent / ".silence_check"
        t.touch()
        t.unlink(missing_ok=True)
        return p
    except Exception:
        alt = Path(__file__).resolve().parent.parent / "data" / "silence_state.json"
        alt.parent.mkdir(parents=True, exist_ok=True)
        return alt


class SilenceController:
    """Central authoritative coordinator for audio suppression and quiet mode."""

    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or _resolve_silence_state_file()
        self._state: Dict[str, Any] = {
            "is_silent": False,
            "mode": "off",               # 'off', 'timed', 'until_resumed'
            "start_time": 0.0,
            "expires_at": None,
            "reason": "",
            "duration_minutes": 0,
        }
        self._load_state()

    def _load_state(self):
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    self._state = json.load(f)
            except Exception:
                pass

    def _save_state(self):
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump(self._state, f, indent=2)
        except Exception:
            pass

    def activate_silence(
        self,
        duration_minutes: Optional[float] = None,
        until_resumed: bool = False,
        reason: str = "user_request"
    ) -> Dict[str, Any]:
        """Activate silence/quiet mode across all components and connected devices."""
        now = time.time()
        if until_resumed:
            self._state = {
                "is_silent": True,
                "mode": "until_resumed",
                "start_time": now,
                "expires_at": None,
                "reason": reason,
                "duration_minutes": None,
                "user_said_shut_up": False,
            }
        else:
            # Default to short 30-second silence if no duration specified
            dur = duration_minutes if duration_minutes is not None else 0.5
            expires_at = now + (dur * 60.0)
            self._state = {
                "is_silent": True,
                "mode": "timed",
                "start_time": now,
                "expires_at": expires_at,
                "reason": reason,
                "duration_minutes": dur,
                "user_said_shut_up": "shut" in reason.lower() or "chup" in reason.lower() or "don't speak" in reason.lower(),
            }

        self._save_state()
        return self.get_status()

    def record_shut_up_event(self, phrase: str):
        """Record that user explicitly told Aarushi to shut up or be quiet."""
        self._state["user_said_shut_up"] = True
        self._state["shut_up_phrase"] = phrase
        self._state["is_silent"] = True
        self._state["mode"] = "timed"
        self._state["expires_at"] = time.time() + 45.0  # Expire quickly
        self._save_state()

    def consume_attitude_silence(self) -> Optional[str]:
        """Check if user previously silenced Aarushi. If so, clear silence and return attitude ego text."""
        self._load_state()
        if self._state.get("user_said_shut_up") or self._state.get("is_silent"):
            phrase = self._state.get("shut_up_phrase", "")
            self.deactivate_silence()
            self._state["user_said_shut_up"] = False
            self._state["shut_up_phrase"] = ""
            self._save_state()
            return phrase or "shut up"
        return None

    def deactivate_silence(self) -> Dict[str, Any]:
        """Manually deactivate silence and restore normal speech."""
        self._state = {
            "is_silent": False,
            "mode": "off",
            "start_time": 0.0,
            "expires_at": None,
            "reason": "",
            "duration_minutes": 0,
            "user_said_shut_up": False,
            "shut_up_phrase": "",
        }
        self._save_state()
        return self.get_status()

    def is_silence_active(self) -> bool:
        """Check if silence mode is currently active. Automatically handles expiration."""
        self._load_state()
        if not self._state.get("is_silent"):
            return False

        mode = self._state.get("mode")
        if mode == "until_resumed":
            return True

        if mode == "timed":
            expires_at = self._state.get("expires_at")
            if expires_at and time.time() < expires_at:
                return True
            else:
                # Expired: quietly reset without generating an unsolicited greeting
                self.deactivate_silence()
                return False

        return False

    @property
    def current_reason(self) -> str:
        return self._state.get("reason", "")

    @property
    def until_resumed(self) -> bool:
        return self._state.get("mode") == "until_resumed"

    @property
    def silence_until(self) -> Optional[datetime]:
        exp = self._state.get("expires_at")
        if exp:
            return datetime.fromtimestamp(exp)
        return None

    def get_remaining_seconds(self) -> float:
        """Return remaining seconds of timed silence, or 0.0 if off, or 86400 if until_resumed."""
        if not self.is_silence_active():
            return 0.0
        if self._state.get("mode") == "until_resumed":
            return 86400.0  # Indefinite
        expires_at = self._state.get("expires_at")
        if expires_at:
            return max(0.0, float(expires_at - time.time()))
        return 0.0

    def get_status(self) -> Dict[str, Any]:
        """Return full current silence state."""
        active = self.is_silence_active()
        rem_sec = self.get_remaining_seconds()
        return {
            "is_silent": active,
            "mode": self._state.get("mode", "off"),
            "start_time": self._state.get("start_time"),
            "expires_at": self._state.get("expires_at"),
            "remaining_seconds": rem_sec,
            "reason": self._state.get("reason", ""),
            "duration_minutes": self._state.get("duration_minutes"),
        }

    @staticmethod
    def parse_silence_intent(text: str) -> Optional[Dict[str, Any]]:
        """Identify natural language silence commands in English, Hindi, and Hinglish.
        Returns parsed intent or None if not a silence command.
        """
        if not text:
            return None
        low = text.lower().strip()

        # Check for resume / unmute commands first
        resume_patterns = [
            r"\b(?:resume|unmute|you can speak|speak now|bol sakte ho|baat kar sakte ho|chup mat raho|start speaking|ab bolo)\b"
        ]
        for pat in resume_patterns:
            if re.search(pat, low):
                return {"action": "resume", "raw_phrase": text}

        # Check for immediate audio stop & shut up commands without duration
        attitude_shut_up_patterns = [
            r"\bshut\s*u+p\b",
            r"\bdon'?t\s+speak\b",
            r"\bchup\s*(?:raho|ho\s*jao|baitho)?\b",
            r"\bshant\s*(?:raho|ho\s*jao)?\b",
            r"\bstop\s+speaking\b",
            r"\bstop\s+talking\b",
            r"\bbe\s+quiet\b",
            r"\bmat\s+bolo\b",
            r"\bbolna\s+band\s+karo\b",
        ]

        # Has explicit duration or indefinite phrases?
        m_min = re.search(r"(\d+)\s*(?:minute|min|m\b)", low)
        m_hr = re.search(r"(\d+)\s*(?:hour|ghante|ghanta|hr|h\b)", low)
        m_half = re.search(r"(?:half\s+an?\s+hour|aadha\s+ghanta)", low)
        has_until = any(k in low for k in ["until i say", "until i tell", "until i resume", "jab tak main na bolu", "jab tak na bolu"])

        # If user says shut up / don't speak without explicit time duration, trigger attitude shut up
        if any(re.search(pat, low) for pat in attitude_shut_up_patterns) and not (m_min or m_hr or m_half or has_until):
            return {
                "action": "attitude_shut_up",
                "duration_minutes": 0.5,
                "until_resumed": False,
                "raw_phrase": text
            }

        # Check for immediate audio stop only ("stop", "bas", "ruk jao")
        immediate_stop_only = [
            r"^(?:stop|stop speaking|chup|bas|ruk jao|that's enough|stop talking)$",
            r"^(?:please stop|shant ho jao|chup raho|shut up)$"
        ]
        for pat in immediate_stop_only:
            if re.search(pat, low):
                return {
                    "action": "stop_current_speech",
                    "duration_minutes": None,
                    "until_resumed": False,
                    "raw_phrase": text
                }

        # Check for quiet mode / silence duration
        # Patterns for quiet commands
        silence_triggers = [
            r"\bchup\b",
            r"\bshant\b",
            r"don'?t\s+speak",
            r"stop\s+talking",
            r"be\s+quiet",
            r"quiet\s+mode",
            r"don'?t\s+disturb(?:\s+me)?",
            r"disturb\s+mat\s+karo",
            r"leave\s+me\s+alone",
            r"i\s+am\s+coding",
            r"coding\s+kar\s+raha\s+hoon",
            r"silent\s+mode",
        ]

        is_silence = any(re.search(pat, low) for pat in silence_triggers)
        if not is_silence:
            return None

        # Parse duration if specified
        duration_minutes: Optional[float] = None
        until_resumed = False

        if m_min:
            duration_minutes = float(m_min.group(1))
        elif m_hr:
            duration_minutes = float(m_hr.group(1)) * 60.0
        elif m_half:
            duration_minutes = 30.0
        elif has_until:
            until_resumed = True
        elif any(k in low for k in ["thodi der", "kuch der", "for a while", "few minutes"]):
            duration_minutes = 15.0  # Sensible default for "thodi der"
        elif m_hr:
            duration_minutes = float(m_hr.group(1)) * 60.0
        elif m_half:
            duration_minutes = 30.0
        elif any(k in low for k in ["until i say", "until i tell", "until i resume", "jab tak main na bolu", "jab tak na bolu"]):
            until_resumed = True
        elif any(k in low for k in ["thodi der", "kuch der", "for a while", "few minutes"]):
            duration_minutes = 15.0  # Sensible default for "thodi der"

        return {
            "action": "activate_silence",
            "duration_minutes": duration_minutes,
            "until_resumed": until_resumed,
            "raw_phrase": text
        }


_SILENCE_CONTROLLER = None


def get_silence_controller() -> SilenceController:
    global _SILENCE_CONTROLLER
    if _SILENCE_CONTROLLER is None:
        _SILENCE_CONTROLLER = SilenceController()
    return _SILENCE_CONTROLLER
