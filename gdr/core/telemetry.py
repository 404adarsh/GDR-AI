"""Voice and Conversation Pipeline Telemetry and Latency Tracker.

Records timestamped milestones across:
- speech_started
- speech_ended
- transcription_started
- transcription_completed
- llm_request_started
- first_llm_token
- llm_response_completed
- tts_started
- first_audio_chunk_ready
- playback_started
- playback_completed

Calculates precision latency metrics and outputs diagnostics to logs and UI.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger("gdr.core.telemetry")


@dataclass
class PipelineMilestones:
    speech_started: Optional[float] = None
    speech_ended: Optional[float] = None
    transcription_started: Optional[float] = None
    transcription_completed: Optional[float] = None
    llm_request_started: Optional[float] = None
    first_llm_token: Optional[float] = None
    llm_response_completed: Optional[float] = None
    tts_started: Optional[float] = None
    first_audio_chunk_ready: Optional[float] = None
    playback_started: Optional[float] = None
    playback_completed: Optional[float] = None


class PipelineTimer:
    """Tracks latency milestones for a single interaction turn."""

    def __init__(self, utterance_id: Optional[str] = None):
        self.utterance_id = utterance_id or f"turn_{int(time.time() * 1000)}"
        self.milestones = PipelineMilestones()
        self._created_at = time.time()

    def record(self, milestone_name: str, timestamp: Optional[float] = None):
        """Record milestone with current high-resolution monotonic/wall time."""
        t = timestamp if timestamp is not None else time.time()
        if hasattr(self.milestones, milestone_name):
            setattr(self.milestones, milestone_name, t)
        else:
            logger.debug(f"Unknown milestone: {milestone_name}")

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Compute key stage durations in milliseconds."""
        m = self.milestones

        def delta_ms(start: Optional[float], end: Optional[float]) -> Optional[int]:
            if start is not None and end is not None and end >= start:
                return int((end - start) * 1000)
            return None

        # Key Latency Metrics
        vad_speech_ms = delta_ms(m.speech_started, m.speech_ended)
        end_of_speech_to_transcript_ms = delta_ms(m.speech_ended, m.transcription_completed)
        stt_duration_ms = delta_ms(m.transcription_started, m.transcription_completed)
        transcript_to_first_token_ms = delta_ms(m.transcription_completed, m.first_llm_token)
        ttft_ms = delta_ms(m.llm_request_started, m.first_llm_token)
        llm_generation_ms = delta_ms(m.llm_request_started, m.llm_response_completed)
        tts_synthesis_ms = delta_ms(m.tts_started, m.first_audio_chunk_ready)
        time_to_first_audio_ms = delta_ms(m.llm_request_started, m.first_audio_chunk_ready)
        playback_latency_ms = delta_ms(m.first_audio_chunk_ready, m.playback_started)
        total_end_to_end_ms = delta_ms(
            m.speech_ended or m.llm_request_started,
            m.playback_started or m.first_audio_chunk_ready or m.llm_response_completed
        )

        metrics = {
            "utterance_id": self.utterance_id,
            "vad_speech_ms": vad_speech_ms,
            "end_of_speech_to_transcript_ms": end_of_speech_to_transcript_ms,
            "stt_duration_ms": stt_duration_ms,
            "transcript_to_first_token_ms": transcript_to_first_token_ms,
            "time_to_first_token_ms": ttft_ms,
            "llm_generation_ms": llm_generation_ms,
            "tts_synthesis_ms": tts_synthesis_ms,
            "time_to_first_audio_ms": time_to_first_audio_ms,
            "playback_latency_ms": playback_latency_ms,
            "total_end_to_end_ms": total_end_to_end_ms,
            "milestones": {k: v for k, v in asdict(m).items() if v is not None}
        }
        return metrics

    def log_report(self):
        """Log concise timing breakdown."""
        metrics = self.get_metrics_summary()
        e2e = metrics.get("total_end_to_end_ms") or 0
        ttft = metrics.get("time_to_first_token_ms") or 0
        llm = metrics.get("llm_generation_ms") or 0
        tts = metrics.get("tts_synthesis_ms") or 0
        logger.info(
            f"⏱️ [Turn Latency]: E2E: {e2e}ms | TTFT: {ttft}ms | LLM: {llm}ms | TTS: {tts}ms (ID: {self.utterance_id})"
        )


_ACTIVE_TIMERS: Dict[str, PipelineTimer] = {}


def get_pipeline_timer(utterance_id: Optional[str] = None) -> PipelineTimer:
    """Retrieve or create a pipeline timer."""
    global _ACTIVE_TIMERS
    uid = utterance_id or "default_turn"
    if uid not in _ACTIVE_TIMERS:
        _ACTIVE_TIMERS[uid] = PipelineTimer(utterance_id=uid)
    return _ACTIVE_TIMERS[uid]


def clear_pipeline_timer(utterance_id: str):
    """Clean up finished timer."""
    global _ACTIVE_TIMERS
    _ACTIVE_TIMERS.pop(utterance_id, None)

