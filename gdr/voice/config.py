"""Authoritative Voice Configuration and Management for GDR AI.

Provides centralized VoiceConfig and VoiceManager ensuring strict voice consistency,
per-response immutable configuration snapshots, and reliable persistence.
"""

from dataclasses import dataclass, field, asdict
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
import copy

from gdr.config import load_config, save_config

logger = logging.getLogger("gdr.voice.config")

# Standard supported voice profiles mapped to provider and voice IDs
SUPPORTED_VOICE_CATALOG: Dict[str, Dict[str, Any]] = {
    "hi_swara": {
        "provider": "edge",
        "voice_id": "hi-IN-SwaraNeural",
        "language": "hi-IN",
        "label": "Hindi: Swara (Studio Neural)",
        "gender": "female"
    },
    "hi_female": {
        "provider": "edge",
        "voice_id": "hi-IN-SwaraNeural",
        "language": "hi-IN",
        "label": "Hindi: Swara (Studio Neural)",
        "gender": "female"
    },
    "hi_male": {
        "provider": "edge",
        "voice_id": "hi-IN-MadhurNeural",
        "language": "hi-IN",
        "label": "Hindi: Madhur (Studio Neural)",
        "gender": "male"
    },
    "en_aria": {
        "provider": "edge",
        "voice_id": "en-US-AriaNeural",
        "language": "en-US",
        "label": "English: Aria (Expressive Neural)",
        "gender": "female"
    },
    "en_jenny": {
        "provider": "edge",
        "voice_id": "en-US-JennyNeural",
        "language": "en-US",
        "label": "English: Jenny (Clear Neural)",
        "gender": "female"
    },
    "en_female": {
        "provider": "edge",
        "voice_id": "en-US-JennyNeural",
        "language": "en-US",
        "label": "English: Jenny (Clear Neural)",
        "gender": "female"
    },
    "en_male": {
        "provider": "edge",
        "voice_id": "en-US-GuyNeural",
        "language": "en-US",
        "label": "English: Guy (Articulate Neural)",
        "gender": "male"
    },
    "en_sonia": {
        "provider": "edge",
        "voice_id": "en-GB-SoniaNeural",
        "language": "en-GB",
        "label": "British: Sonia (Refined Neural)",
        "gender": "female"
    },
    "en_ryan": {
        "provider": "edge",
        "voice_id": "en-GB-RyanNeural",
        "language": "en-GB",
        "label": "British: Ryan (Male Neural)",
        "gender": "male"
    },
    "en_neerja": {
        "provider": "edge",
        "voice_id": "en-IN-NeerjaNeural",
        "language": "en-IN",
        "label": "Indian English: Neerja (Warm Neural)",
        "gender": "female"
    },
    "en_indian": {
        "provider": "edge",
        "voice_id": "en-IN-NeerjaNeural",
        "language": "en-IN",
        "label": "Indian English: Neerja (Warm Neural)",
        "gender": "female"
    },
    "sarvam_bulbul": {
        "provider": "sarvam",
        "voice_id": "anushka",
        "language": "hi-IN",
        "label": "Sarvam: Anushka (Bulbul v2)",
        "gender": "female"
    },
    "elevenlabs": {
        "provider": "elevenlabs",
        "voice_id": "RDWdsTU6N02BFftbIEAp",
        "language": "multilingual",
        "label": "ElevenLabs: Custom AI HD Voice",
        "gender": "female"
    },
    "piper_offline": {
        "provider": "piper",
        "voice_id": "en_US-lessac-medium",
        "language": "en-US",
        "label": "Piper: Offline CPU Neural (0-Token)",
        "gender": "female"
    },
    "browser": {
        "provider": "browser",
        "voice_id": "browser_default",
        "language": "auto",
        "label": "Browser SpeechSynthesis Fallback",
        "gender": "auto"
    }
}


@dataclass(frozen=True)
class VoiceConfig:
    """Authoritative immutable voice configuration."""
    provider: str = "edge"
    voice_id: str = "hi-IN-SwaraNeural"
    language: str = "auto"
    speech_rate: float = 1.0
    pitch: float = 1.0
    volume: float = 1.0
    fallback_enabled: bool = True
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoiceConfig":
        if not data:
            return cls()
        return cls(
            provider=str(data.get("provider", "edge")),
            voice_id=str(data.get("voice_id", "hi-IN-SwaraNeural")),
            language=str(data.get("language", "auto")),
            speech_rate=float(data.get("speech_rate", 1.0)),
            pitch=float(data.get("pitch", 1.0)),
            volume=float(data.get("volume", 1.0)),
            fallback_enabled=bool(data.get("fallback_enabled", True)),
            version=int(data.get("version", 1)),
        )


class VoiceManager:
    """Authoritative singleton managing voice persistence and per-response snapshots."""

    _instance: Optional["VoiceManager"] = None
    _active_config: VoiceConfig
    _response_snapshots: Dict[str, VoiceConfig]

    def __new__(cls) -> "VoiceManager":
        if cls._instance is None:
            cls._instance = super(VoiceManager, cls).__new__(cls)
            cls._instance._response_snapshots = {}
            cls._instance._load_initial_config()
        return cls._instance

    def _load_initial_config(self) -> None:
        """Load persistent voice configuration from config.toml."""
        try:
            cfg = load_config()
            v_cfg = cfg.get("voice", {})
            raw_voice = v_cfg.get("tts_voice", "hi-IN-SwaraNeural")
            raw_engine = v_cfg.get("tts_engine", "edge")

            # Check if raw_voice matches a known catalog key
            if raw_voice in SUPPORTED_VOICE_CATALOG:
                cat = SUPPORTED_VOICE_CATALOG[raw_voice]
                provider = cat["provider"]
                voice_id = cat["voice_id"]
                language = cat["language"]
            else:
                provider = raw_engine
                voice_id = raw_voice
                language = "auto"

            self._active_config = VoiceConfig(
                provider=provider,
                voice_id=voice_id,
                language=language,
                speech_rate=1.0,
                pitch=1.0,
                volume=1.0,
                fallback_enabled=True,
                version=1
            )
        except Exception as e:
            logger.warning(f"Error loading voice config, falling back to default: {e}")
            self._active_config = VoiceConfig()

    def get_active_config(self) -> VoiceConfig:
        """Return the current user-selected voice configuration."""
        if not hasattr(self, "_active_config") or self._active_config is None:
            self._load_initial_config()
        return self._active_config

    def set_active_config(
        self,
        provider: Optional[str] = None,
        voice_id: Optional[str] = None,
        language: Optional[str] = None,
        speech_rate: Optional[float] = None,
        pitch: Optional[float] = None,
        volume: Optional[float] = None,
        fallback_enabled: Optional[bool] = None,
        persist: bool = True
    ) -> VoiceConfig:
        """Update and optionally persist the authoritative voice configuration."""
        curr = self._active_config

        # Check catalog resolution
        new_provider = provider or curr.provider
        new_voice_id = voice_id or curr.voice_id
        new_lang = language or curr.language

        if voice_id and voice_id in SUPPORTED_VOICE_CATALOG:
            cat = SUPPORTED_VOICE_CATALOG[voice_id]
            new_provider = cat["provider"]
            new_voice_id = cat["voice_id"]
            if not language or language == "auto":
                new_lang = cat["language"]

        new_config = VoiceConfig(
            provider=new_provider,
            voice_id=new_voice_id,
            language=new_lang,
            speech_rate=speech_rate if speech_rate is not None else curr.speech_rate,
            pitch=pitch if pitch is not None else curr.pitch,
            volume=volume if volume is not None else curr.volume,
            fallback_enabled=fallback_enabled if fallback_enabled is not None else curr.fallback_enabled,
            version=curr.version + 1
        )
        self._active_config = new_config

        if persist:
            try:
                cfg = load_config()
                cfg.setdefault("voice", {})["tts_engine"] = new_config.provider
                cfg["voice"]["tts_voice"] = new_config.voice_id
                save_config(cfg)
            except Exception as e:
                logger.error(f"Failed to persist voice configuration: {e}")

        return new_config

    def create_snapshot(self, response_id: str) -> VoiceConfig:
        """Create an immutable snapshot tied to a specific response ID.
        Every audio chunk belonging to that response must use this exact snapshot,
        guaranteeing zero accidental voice switching mid-response.
        """
        snapshot = copy.deepcopy(self._active_config)
        self._response_snapshots[response_id] = snapshot
        return snapshot

    def get_snapshot(self, response_id: Optional[str]) -> VoiceConfig:
        """Retrieve the immutable snapshot for a response, or return active config."""
        if response_id and response_id in self._response_snapshots:
            return self._response_snapshots[response_id]
        return self._active_config

    def release_snapshot(self, response_id: str) -> None:
        """Release memory for completed response snapshot."""
        self._response_snapshots.pop(response_id, None)


def get_voice_manager() -> VoiceManager:
    """Return the global VoiceManager singleton."""
    return VoiceManager()

