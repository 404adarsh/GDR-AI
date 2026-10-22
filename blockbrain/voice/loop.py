"""Voice interaction loop for blockbrain AI (`blockbrain --voice`).
Handles wake-word detection, robust VAD phrase capture, STT, agent execution, and TTS readout.
Properly handles SIGINT (Ctrl+C) and exit commands without trapping the user.
"""

import os
import signal
import sys
import threading
import time
from typing import Callable, Optional

from blockbrain.config import load_config
from blockbrain.voice.vad import VADRecorder
from blockbrain.voice.wakeword import WakeWordDetector
from blockbrain.voice.stt import SpeechToText
from blockbrain.voice.tts import TextToSpeech, stop_speaking

_EXIT_PHRASES = ("stop listening", "exit voice", "voice off", "goodbye blockbrain", "goodbye jarvis", "exit", "quit")


def run_voice_loop(agent_executor: Optional[Callable[[str], str]] = None):
    """Run interactive hands-free voice loop."""
    config = load_config()
    voice_cfg = config.get("voice", {})

    wake_word = voice_cfg.get("wake_word", "hey jarvis").strip().lower()
    wake_threshold = float(voice_cfg.get("wake_threshold", 0.45))
    use_wake = bool(wake_word and wake_word != "none")

    recorder = VADRecorder(sensitivity=int(voice_cfg.get("vad_sensitivity", 2)))
    stt = SpeechToText(
        engine=voice_cfg.get("stt_engine", "faster-whisper"),
        model_name=voice_cfg.get("stt_model", "tiny")
    )
    tts = TextToSpeech(
        engine=voice_cfg.get("tts_engine", "piper"),
        piper_model_path=voice_cfg.get("tts_piper_model_path")
    )
    detector = WakeWordDetector(threshold=wake_threshold) if use_wake else None

    stop_event = threading.Event()

    def handle_sigint(signum, frame):
        print("\n👋 Voice mode exiting...")
        stop_event.set()
        stop_speaking()
        sys.exit(0)

    original_sigint = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGINT, handle_sigint)

    print("\n" + "=" * 50)
    print("🎙️  blockbrain AI Voice Mode Active")
    if use_wake and detector and detector.is_available():
        print(f"👉 Wake word: '{wake_word.title()}' (or just start talking)")
    else:
        print("👉 Listening directly for your speech (no wake word required)")
    print("👉 Say 'Stop listening' or press Ctrl+C to exit.")
    print("=" * 50 + "\n")

    tts.speak("Voice mode active. How can I help?")

    conversation_active = False
    last_turn_time = 0.0

    try:
        while not stop_event.is_set():
            now = time.time()
            # If in active conversation within 25 seconds, don't wait for wake word
            in_conversation = conversation_active and (now - last_turn_time < 25.0)

            if use_wake and detector and detector.is_available() and not in_conversation:
                print("💤 Waiting for wake word ('Hey Jarvis') or speak directly...")
                detected = detector.wait_for_wake_word(stop_event=stop_event)
                if not detected or stop_event.is_set():
                    break
                print("\n🔔 Wake word detected! Listening...")
            else:
                if in_conversation:
                    print(f"\n🎙️ Listening (conversational mode - {max(0, int(25 - (now - last_turn_time)))}s remaining)...")
                else:
                    print("\n🎙️ Listening for your voice...")

            # Capture user speech via VAD with 0.75s silence detection for snappy response
            success, audio, info = recorder.record_phrase(
                max_seconds=20.0,
                wait_seconds=7.0,
                silence_seconds=0.75,
                stop_event=stop_event
            )

            if stop_event.is_set():
                break

            if not success:
                if "Cancelled" in info or "KeyboardInterrupt" in info:
                    break
                time.sleep(0.3)
                continue

            if len(audio) == 0:
                continue

            print("⚡ Transcribing...")
            text = stt.transcribe(audio)
            if not text or len(text.strip()) == 0:
                continue

            print(f"\n👤 You: \"{text}\"")

            clean_lower = text.lower().strip()
            if any(p in clean_lower for p in _EXIT_PHRASES):
                tts.speak("Goodbye!")
                print("👋 Exiting voice mode.")
                break

            if agent_executor:
                print("🧠 blockbrain AI thinking...")
                try:
                    reply = agent_executor(text)
                except Exception as e:
                    reply = f"Error executing request: {e}"
                print(f"🤖 blockbrain AI: {reply}")
                tts.speak(reply)
            else:
                print(f"🤖 Echo: {text}")
                tts.speak(f"You said: {text}")

            conversation_active = True
            last_turn_time = time.time()

    except KeyboardInterrupt:
        print("\n👋 Voice mode exiting...")
    finally:
        stop_speaking()
        signal.signal(signal.SIGINT, original_sigint)

