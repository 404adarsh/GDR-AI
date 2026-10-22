"""GDR Voice Subsystem.
Includes VAD audio capture, OpenWakeWord detection, STT (Whisper & Sarvam), and TTS (Piper, espeak, Sarvam).
"""

from gdr.voice.vad import (
    VADRecorder,
    check_and_boost_mic,
    query_audio_devices,
    fix_and_boost_microphones,
    test_microphone_input,
    ensure_audio_environment,
)
from gdr.voice.wakeword import WakeWordDetector
from gdr.voice.stt import SpeechToText
from gdr.voice.tts import TextToSpeech, stop_speaking
from gdr.voice.loop import run_voice_loop

__all__ = [
    "VADRecorder",
    "check_and_boost_mic",
    "query_audio_devices",
    "fix_and_boost_microphones",
    "test_microphone_input",
    "ensure_audio_environment",
    "WakeWordDetector",
    "SpeechToText",
    "TextToSpeech",
    "stop_speaking",
    "run_voice_loop",
]

