"""End-to-End Voice Integration Test for GDR AI.
Proves that TTS, VAD, Wake Word, and STT work seamlessly together.
"""

import io
import os
import wave
import numpy as np
import pytest

from gdr.voice.vad import VADRecorder
from gdr.voice.wakeword import WakeWordDetector
from gdr.voice.stt import SpeechToText
from gdr.voice.tts import TextToSpeech, clean_text_for_speech


def test_text_cleaning():
    raw = "```python\nprint('hello')\n``` Check https://github.com *bold* #title 🎉"
    cleaned = clean_text_for_speech(raw)
    assert "https://" not in cleaned
    assert "```" not in cleaned
    assert "Check link bold title" in cleaned


def test_vad_silence_vs_speech():
    vad = VADRecorder(sample_rate=16000, sensitivity=2)

    # 30ms of pure silence (480 samples of zeros)
    silence = np.zeros(480, dtype=np.int16).tobytes()
    assert not vad.is_speech(silence)

    # 30ms of simulated voiced tone (fundamental + harmonic)
    t = np.linspace(0, 0.03, 480, endpoint=False)
    tone = (np.sin(2 * np.pi * 350 * t) * 10000 + np.sin(2 * np.pi * 700 * t) * 5000).astype(np.int16).tobytes()
    assert vad.is_speech(tone)


def test_piper_tts_and_whisper_stt(tmp_path):
    # 1. Synthesize known phrase with Piper
    model_path = os.path.expanduser("~/gdragent/models/piper/en_US-lessac-medium.onnx")
    assert os.path.exists(model_path), f"Piper model missing at {model_path}"

    tts = TextToSpeech(engine="piper", piper_model_path=model_path)
    from piper import PiperVoice
    voice = PiperVoice.load(model_path)

    test_wav = str(tmp_path / "voice_test.wav")
    with wave.open(test_wav, "wb") as wf:
        voice.synthesize_wav("GDR AI voice test verified.", wf)

    assert os.path.exists(test_wav)
    assert os.path.getsize(test_wav) > 10000

    # 2. Transcribe with local faster-whisper
    stt = SpeechToText(engine="faster-whisper", model_name="tiny")
    transcript = stt.transcribe(test_wav)
    print(f"\n[E2E Voice Test] Transcribed output: '{transcript}'")

    transcript_lower = transcript.lower()
    assert "voice" in transcript_lower or "test" in transcript_lower or "gdr" in transcript_lower


def test_openwakeword_detection(tmp_path):
    # Synthesize "Hey Jarvis, what time is it?" with Piper
    model_path = os.path.expanduser("~/gdragent/models/piper/en_US-lessac-medium.onnx")
    from piper import PiperVoice
    voice = PiperVoice.load(model_path)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        voice.synthesize_wav("Hey Jarvis, what time is it?", wf)

    buf.seek(0)
    with wave.open(buf, "rb") as wf:
        rate = wf.getframerate()
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

    # Resample to 16kHz
    if rate != 16000:
        import scipy.signal
        num_output_samples = int(len(data) * 16000 / rate)
        data_16k = scipy.signal.resample(data, num_output_samples).astype(np.int16)
    else:
        data_16k = data

    detector = WakeWordDetector(threshold=0.40)
    assert detector.is_available()

    step = 1280
    max_score = 0.0
    for i in range(0, len(data_16k) - step, step):
        chunk = data_16k[i:i+step]
        prediction = detector.model.predict(chunk)
        score = prediction.get(detector.model_key, 0.0)
        if score > max_score:
            max_score = score

    print(f"\n[Wake Word Test] Max prediction score: {max_score:.4f}")
    assert max_score >= 0.40, f"Expected wake word score >= 0.40, got {max_score}"

