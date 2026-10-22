"""blockbrain Voice Subsystem.
Includes VAD audio capture, OpenWakeWord detection, STT (Whisper & Sarvam), and TTS (Piper, espeak, Sarvam).
"""

from blockbrain.voice.vad import VADRecorder, check_and_boost_mic
from blockbrain.voice.wakeword import WakeWordDetector
from blockbrain.voice.stt import SpeechToText
from blockbrain.voice.tts import TextToSpeech, stop_speaking
from blockbrain.voice.loop import run_voice_loop

__all__ = [
    "VADRecorder",
    "check_and_boost_mic",
    "WakeWordDetector",
    "SpeechToText",
    "TextToSpeech",
    "stop_speaking",
    "run_voice_loop",
]

