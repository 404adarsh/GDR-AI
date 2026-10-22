"""Secrets loader for blockbrain AI.
Loads secrets strictly from environment variables or the system keyring.
Never from config files or source code.
"""

import os
import re
from typing import Optional, Dict

try:
    import keyring
except ImportError:
    keyring = None

_KNOWN_SECRET_NAMES = [
    "SARVAM_API_KEY",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "EMAIL_ADDRESS",
    "EMAIL_APP_PASSWORD",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "USER_PHONE_NUMBER",
    "WEATHER_API_KEY",
    "BRAVE_API_KEY",
]


def get_secret(name: str, default: Optional[str] = None, service: str = "blockbrain") -> Optional[str]:
    """Retrieve secret from environment variable, falling back to system keyring."""
    # 1. Environment variable (preferred in headless/scripts)
    val = os.environ.get(name)
    if val and val.strip():
        return val.strip()

    # 2. System keyring
    if keyring is not None:
        try:
            stored = keyring.get_password(service, name)
            if stored and stored.strip():
                return stored.strip()
        except Exception:
            pass

    return default


def set_keyring_secret(name: str, value: str, service: str = "blockbrain") -> bool:
    """Store secret into system keyring."""
    if keyring is None:
        return False
    try:
        keyring.set_password(service, name, value)
        return True
    except Exception:
        return False


def set_secret(name: str, value: str, service: str = "blockbrain") -> bool:
    """Convenience alias for set_keyring_secret."""
    return set_keyring_secret(name, value, service=service)


def mask_secret(value: Optional[str]) -> str:
    """Return masked string for display (e.g. 'sk-...4a2b')."""
    if not value:
        return "<unset>"
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}...{value[-3:]}"


def sanitize_text(text: str) -> str:
    """Sanitize any occurrence of known secrets from text before logging or model prompt."""
    if not text:
        return text
    clean = text
    for name in _KNOWN_SECRET_NAMES:
        val = get_secret(name)
        if val and len(val) >= 4 and val in clean:
            clean = clean.replace(val, f"[REDACTED_{name}]")
    return clean

