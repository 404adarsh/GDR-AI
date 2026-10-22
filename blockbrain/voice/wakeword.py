"""OpenWakeWord detector for blockbrain AI.
Uses local onnx model (hey_jarvis) without any cloud dependency.
"""

import threading
from typing import Optional, List
import numpy as np
import sounddevice as sd





class WakeWordDetector:
    def __init__(self, target_word: str = "hey jarvis", threshold: float = 0.45):
        self.target_word = target_word.lower()
        self.threshold = threshold
        self.model: Optional[OWWModel] = None
        self.sample_rate = 16000
        self.chunk_size = 1280  # 80ms chunks at 16kHz
        self._init_model()

    def _init_model(self):
        try:
            import openwakeword
            from openwakeword.model import Model as OWWModel
            available = openwakeword.get_pretrained_model_paths()
            # Select matching model or default to hey_jarvis
            matched = [p for p in available if "hey_jarvis" in p]
            if not matched and available:
                matched = [available[0]]

            if matched:
                self.model = OWWModel(wakeword_model_paths=matched)
                self.model_key = list(self.model.models.keys())[0]
            else:
                self.model = None
        except Exception as e:
            print(f"⚠️ Wake word model init failed: {e}")
            self.model = None

    def is_available(self) -> bool:
        return self.model is not None

    def wait_for_wake_word(self, stop_event: Optional[threading.Event] = None) -> bool:
        """Stream microphone audio and block until wake word is detected.
        Returns True if detected, False if stopped/interrupted.
        """
        if not self.is_available():
            # If no wake word model available, return True immediately to continue
            return True

        self.model.reset()

        try:
            with sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=self.chunk_size,
                dtype="int16",
                channels=1
            ) as stream:
                while True:
                    if stop_event and stop_event.is_set():
                        return False

                    data, _ = stream.read(self.chunk_size)
                    chunk = np.frombuffer(data, dtype=np.int16)

                    prediction = self.model.predict(chunk)
                    score = prediction.get(self.model_key, 0.0)

                    if score >= self.threshold:
                        return True

        except KeyboardInterrupt:
            return False
        except Exception as e:
            print(f"⚠️ Wake word listener error: {e}")
            return False

