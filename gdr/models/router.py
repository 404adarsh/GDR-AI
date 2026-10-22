"""Privacy Router and Cloud-to-Local Failover Engine for GDR AI (Phase 8).
Ensures private user data never leaves the laptop, and seamlessly switches to local models during network or API outages.
"""

from typing import Dict, Any, Tuple
import re

from gdr.models.manager import LocalModelManager


class PrivacyRouter:
    """Classifies content privacy and enforces local-only processing for sensitive data."""

    PRIVATE_PATTERNS = [
        r"\b(?:email|inbox|password|secret|keyring|credential|token)\b",
        r"\b(?:bank|account|card|balance|salary|tax|payment)\b",
        r"\b(?:camera|webcam|photo|face|person|who is looking)\b",
        r"\b(?:memory|remember|what did i tell you|passport)\b",
        r"\b(?:doctor|medical|health|prescription|diagnosis)\b",
        r"\b(?:telegram|whatsapp|chat with|message from)\b",
    ]

    @classmethod
    def is_private_content(cls, prompt: str) -> Tuple[bool, str]:
        """Check if prompt contains private/sensitive personal data."""
        low = prompt.lower()
        for pat in cls.PRIVATE_PATTERNS:
            if re.search(pat, low):
                return True, f"Matched privacy pattern: {pat}"
        return False, "Public / general content"


class ModelRouter:
    def __init__(self):
        self.local_manager = LocalModelManager()
        self.lite_mode_active = False

    def route_and_generate(
        self,
        prompt: str,
        cloud_provider_func,
        force_local: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """Dispatch query according to privacy rules with automatic failover."""
        is_private, reason = PrivacyRouter.is_private_content(prompt)

        # 1. Private data -> Strictly Local
        if is_private or force_local:
            print(f"🔒 [Privacy Router] Routing to local model ({reason}).")
            res = self.local_manager.generate(prompt)
            return res.text, {
                "provider": "local",
                "lane": res.lane,
                "model": res.model_name,
                "tokens_per_sec": res.tokens_per_second,
                "private": True
            }

        # 2. Public / Low-Risk -> Try Cloud Provider
        try:
            cloud_reply = cloud_provider_func(prompt)
            self.lite_mode_active = False
            return cloud_reply, {"provider": "cloud", "private": False}

        except Exception as e:
            # 3. Failover on API quota / 429 / billing / network error
            print(f"⚠️ [Cloud Failover] Cloud API error: {e}. Switching to local lite mode.")
            self.lite_mode_active = True
            res = self.local_manager.generate(prompt, lane="LANE_1_FAST")
            lite_reply = f"[Running in lite mode] {res.text}"
            return lite_reply, {
                "provider": "local_failover",
                "lane": res.lane,
                "model": res.model_name,
                "tokens_per_sec": res.tokens_per_second,
                "private": False,
                "error": str(e)
            }


def meeting_mode_transcribe_and_summarize(audio_file_path: str) -> Dict[str, Any]:
    """Meeting mode pipeline:
    1. Consent check reminder.
    2. Local Whisper transcription.
    3. Structured summary & action items extraction.
    """
    consent_warning = "⚠️ Consent reminder: Please ensure you have explicit consent from all participants before recording."
    print(consent_warning)

    from gdr.voice.stt import SpeechToText
    stt = SpeechToText()
    transcript = stt.transcribe(audio_file_path)

    # Local structured summary extraction
    mgr = LocalModelManager()
    summary_prompt = f"Summarize this meeting transcript and extract action items:\n\n{transcript[:1500]}"
    res = mgr.generate(summary_prompt, lane="LANE_1_FAST")

    return {
        "consent_notice": consent_warning,
        "transcript": transcript,
        "summary": res.text,
        "lane": res.lane,
    }

