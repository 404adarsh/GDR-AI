"""Configuration management for blockbrain AI.
Stored in ~/.config/blockbrain/config.toml.
Secrets are NEVER saved into this file.
"""

import os
from pathlib import Path
from typing import Any, Dict
import tomllib
import tomli_w

CONFIG_DIR = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain"))
CONFIG_FILE = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG: Dict[str, Any] = {
    "general": {
        "agent_name": "blockbrain AI",
        "user_name": "blockbrain",
        "tone": "friendly, direct, concise, Jarvis-style",
        "timezone": "Asia/Kolkata",
        "language": "en",  # en, hi, hinglish
    },
    "provider": {
        "default": "sarvam",  # sarvam, ollama, claude, openai
        "model": "sarvam-105b",
        "max_steps": 24,
        "max_tokens_per_step": 1500,
        "memory_limit": 30,
    },
    "voice": {
        "enabled": True,
        "vad_engine": "webrtcvad",  # webrtcvad, silero
        "vad_sensitivity": 2,       # 0 (least sensitive) to 3 (most sensitive)
        "wake_word": "hey jarvis",
        "wake_threshold": 0.45,
        "stt_engine": "faster-whisper",  # faster-whisper, sarvam
        "stt_model": "tiny",             # tiny, base, small
        "tts_engine": "piper",           # piper, espeak, sarvam
        "tts_voice": "en_US-lessac-medium",
        "tts_piper_model_path": str(Path.home() / "blockbrainagent" / "models" / "piper" / "en_US-lessac-medium.onnx"),
        "sarvam_tts_speaker": "shubh",
        "mic_volume_boost": 0.85,
    },
    "briefing": {
        "alarm_time": "07:30",
        "loud_alarm": True,
        "push_channel": "telegram",  # telegram, ntfy, pushover
        "enable_phone_call": False,  # Twilio escalation
        "snooze_minutes": 10,
        "escalation_delay_seconds": 180,
        "news_topics": ["tech", "ai", "cybersecurity"],
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "07:00",
    },
    "night_shift": {
        "enabled": True,
        "auto_approval_tier": "AUTO",
        "step_budget": 50,
        "max_retries": 3,
        "allowed_folders": ["~/Downloads", "~/Documents", "~/Desktop"],
    },
    "channels": {
        "telegram_enabled": False,
        "allowed_telegram_user_id": 0,
        "push_backend": "desktop",  # desktop, ntfy, pushover
        "ntfy_topic": "blockbrain-alerts",
    },
    "safety": {
        "require_approval_sensitive": True,
        "spending_cap_daily_usd": 5.0,
        "sudo_allowlist": [
            "systemctl restart ",
            "systemctl stop ",
            "systemctl start ",
            "apt update",
        ],
    },
    "web": {
        "host": "127.0.0.1",
        "port": 8844,
        "allow_tailscale": True,
    },
}


def load_config() -> Dict[str, Any]:
    """Load configuration from config.toml, filling in defaults."""
    cfg = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "rb") as f:
                user_cfg = tomllib.load(f)
            # Deep merge user_cfg into cfg
            for sec, vals in user_cfg.items():
                if sec in cfg and isinstance(vals, dict):
                    cfg[sec].update(vals)
                else:
                    cfg[sec] = vals
        except Exception as e:
            print(f"⚠️ Warning loading {CONFIG_FILE}: {e}. Using defaults.")
    return cfg


def save_config(cfg: Dict[str, Any]) -> bool:
    """Save configuration to config.toml without storing sensitive secrets."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # Deep strip any accidential secrets
        clean_cfg = {}
        for sec, vals in cfg.items():
            if isinstance(vals, dict):
                clean_sec = {}
                for k, v in vals.items():
                    if "key" in k.lower() or "secret" in k.lower() or "password" in k.lower() or "token" in k.lower():
                        continue
                    clean_sec[k] = v
                clean_cfg[sec] = clean_sec
            else:
                clean_cfg[sec] = vals

        with open(CONFIG_FILE, "wb") as f:
            tomli_w.dump(clean_cfg, f)
        return True
    except Exception as e:
        print(f"❌ Failed to save config: {e}")
        return False

