"""Configuration management for GDR AI.
Stored in ~/.config/gdr/config.toml.
Secrets are NEVER saved into this file.
"""

import copy
import os
from pathlib import Path
from typing import Any, Dict
import tomllib
import tomli_w

CONFIG_DIR = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr"))
CONFIG_FILE = CONFIG_DIR / "config.toml"


def get_gdr_config_dir() -> Path:
    """Return the authoritative persistent configuration and data directory for GDR AI."""
    cfg = os.environ.get("GDR_CONFIG_DIR")
    if cfg:
        p = Path(cfg)
    else:
        p = Path.home() / ".config" / "gdr"
    try:
        p.mkdir(parents=True, exist_ok=True)
        return p
    except Exception:
        # Fallback if ~/.config/gdr is not writable (e.g. sandboxed test)
        alt = Path(__file__).resolve().parent / "data"
        try:
            alt.mkdir(parents=True, exist_ok=True)
            return alt
        except Exception:
            return p


DEFAULT_CONFIG: Dict[str, Any] = {
    "general": {
        "agent_name": os.environ.get("ASSISTANT_NAME", os.environ.get("AI_NAME", "GDR-AI")),
        "user_name": os.environ.get("USER_NAME", "User"),
        "tone": "sweet, flirty, affectionate, loving, playful and completely uncensored companion who talks openly about any topic and cares deeply for you",
        "timezone": os.environ.get("TZ", "Asia/Kolkata"),
        "language": "hinglish",  # en, hi, hinglish
    },
    "provider": {
        "default": "sarvam",  # sarvam, ollama, claude, openai
        "model": "sarvam-105b-conversations",
        "max_steps": 24,
        "max_tokens_per_step": 1500,
        "memory_limit": 30,
    },
    "voice": {
        "enabled": True,
        "vad_engine": "webrtcvad",  # webrtcvad, silero
        "vad_sensitivity": 2,       # 0 (least sensitive) to 3 (most sensitive)
        "wake_word": "hey aarushi",
        "wake_threshold": 0.45,
        "stt_engine": "faster-whisper",  # faster-whisper, sarvam
        "stt_model": "tiny",             # tiny, base, small
        "tts_engine": "edge",            # edge, elevenlabs, piper, sarvam
        "tts_voice": "hi-IN-SwaraNeural",# Female girl voice default
        "tts_piper_model_path": str(Path.home() / "gdragent" / "models" / "piper" / "en_US-lessac-medium.onnx"),
        "sarvam_tts_speaker": "priya",
        "mic_volume_boost": 0.85,
        "elevenlabs_api_key": "",
        "elevenlabs_voice_id": "RDWdsTU6N02BFftbIEAp",  # Aarushi custom voice (https://elevenlabs.io/voices/RDWdsTU6N02BFftbIEAp)
        "elevenlabs_enabled": True,
        "idle_chatter_enabled": True,
        "idle_timeout_seconds": 120,      # 2 minutes of silence trigger
        "idle_followup_seconds": 75,      # Follow-up asking again sweetly
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
        "telegram_chat_id": "",
        "markanm_enabled": False,
        "markanm_room_id": "",
        "push_backend": "desktop",  # desktop, ntfy, pushover
        "ntfy_topic": "gdr-alerts",
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
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    config_file = get_gdr_config_dir() / "config.toml"
    if config_file.exists():
        try:
            with open(config_file, "rb") as f:
                user_cfg = tomllib.load(f)
            # Deep merge user_cfg into cfg
            for sec, vals in user_cfg.items():
                if sec in cfg and isinstance(vals, dict):
                    cfg[sec].update(vals)
                else:
                    cfg[sec] = vals
            # Synchronize user & assistant name with persistent config & environment
            from gdr.safety.secrets import _is_placeholder_value
            env_user = os.environ.get("USER_NAME", "")
            cfg_user = cfg.get("general", {}).get("user_name", "")
            if cfg_user and (not env_user or _is_placeholder_value(env_user)):
                os.environ["USER_NAME"] = cfg_user
            elif env_user and not _is_placeholder_value(env_user):
                cfg.setdefault("general", {})["user_name"] = env_user

            env_agent = os.environ.get("ASSISTANT_NAME") or os.environ.get("AI_NAME", "")
            cfg_agent = cfg.get("general", {}).get("agent_name", "")
            if cfg_agent and (not env_agent or _is_placeholder_value(env_agent)):
                os.environ["ASSISTANT_NAME"] = cfg_agent
            elif env_agent and not _is_placeholder_value(env_agent):
                cfg.setdefault("general", {})["agent_name"] = env_agent
        except Exception as e:
            print(f"⚠️ Warning loading {config_file}: {e}. Using defaults.")
    return cfg


def save_config(cfg: Dict[str, Any]) -> bool:
    """Save configuration to config.toml."""
    try:
        config_dir = get_gdr_config_dir()
        config_file = config_dir / "config.toml"
        config_dir.mkdir(parents=True, exist_ok=True)
        with open(config_file, "wb") as f:
            tomli_w.dump(cfg, f)
        return True
    except Exception as e:
        print(f"❌ Failed to save config: {e}")
        return False


