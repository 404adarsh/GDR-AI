"""OpenWakeWord detector for GDR AI.
Uses local onnx model (hey_jarvis) without any cloud dependency.
"""

import threading
from typing import Optional, List, Union
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

    def wait_for_wake_word(
        self,
        stop_event: Optional[threading.Event] = None,
        timeout: Optional[float] = None,
        device: Optional[Union[int, str]] = None
    ) -> bool:
        """Stream microphone audio and wait until wake word is detected or timeout expires.
        Returns True if detected, False if stopped/interrupted/timed out.
        """
        import time
        if not self.is_available():
            # If no wake word model available, return True immediately to continue
            return True

        self.model.reset()
        start_time = time.time()

        # Discover candidate devices prioritizing shared sound servers (pulse, pipewire, default)
        valid_input_ids = []
        try:
            devs = sd.query_devices()
            for i, d in enumerate(devs):
                if d.get("max_input_channels", 0) > 0:
                    valid_input_ids.append(i)
        except Exception:
            pass

        try:
            from gdr.voice.vad import _sort_input_devices
            sorted_devs = _sort_input_devices(valid_input_ids)
        except Exception:
            sorted_devs = valid_input_ids

        candidates = []
        if device is not None:
            candidates.append(device)
        if None not in candidates:
            candidates.append(None)
        for d_id in sorted_devs:
            if d_id not in candidates:
                candidates.append(d_id)

        stream = None
        for dev in candidates:
            for ch in [1, 2]:
                try:
                    sd.check_input_settings(device=dev, samplerate=self.sample_rate, channels=ch, dtype="int16")
                    s = sd.RawInputStream(
                        samplerate=self.sample_rate,
                        blocksize=self.chunk_size,
                        dtype="int16",
                        channels=ch,
                        device=dev
                    )
                    s.start()
                    stream = s
                    channels = ch
                    break
                except Exception:
                    continue
            if stream is not None:
                break

        if stream is None:
            return True  # Continue gracefully if stream cannot be opened

        try:
            with stream:
                while True:
                    if stop_event and stop_event.is_set():
                        return False

                    if timeout is not None and (time.time() - start_time >= timeout):
                        return False

                    data, _ = stream.read(self.chunk_size)
                    chunk = np.frombuffer(data, dtype=np.int16)
                    if channels > 1:
                        chunk = chunk.reshape(-1, channels)[:, 0]

                    prediction = self.model.predict(chunk)
                    score = prediction.get(self.model_key, 0.0)

                    if score >= self.threshold:
                        return True

        except KeyboardInterrupt:
            return False
        except Exception as e:
            print(f"⚠️ Wake word listener error: {e}")
            return False

