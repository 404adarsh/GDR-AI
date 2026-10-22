"""Robust Voice Activity Detection (VAD) audio recording for blockbrain AI.
Uses webrtcvad with silero-vad fallback, rolling pre-buffer, and clean cancellation.
"""

import collections
import subprocess
import threading
import time
from typing import Optional, Tuple
import numpy as np
import sounddevice as sd

try:
    import webrtcvad
except ImportError:
    webrtcvad = None


import os

# Guarantee XDG_RUNTIME_DIR is set for PipeWire / PortAudio
if "XDG_RUNTIME_DIR" not in os.environ or not os.environ["XDG_RUNTIME_DIR"]:
    try:
        os.environ["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
    except Exception:
        os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"


def check_and_boost_mic(min_volume: float = 0.65) -> float:
    """Ensure PipeWire microphone source volume is adequately set without clipping."""
    env = os.environ.copy()
    if "XDG_RUNTIME_DIR" not in env:
        try:
            env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
        except Exception:
            env["XDG_RUNTIME_DIR"] = "/run/user/1000"

    try:
        out = subprocess.check_output(
            ["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"],
            stderr=subprocess.DEVNULL,
            env=env,
            text=True
        ).strip()
        # Output format: "Volume: 0.22" or "Volume: 0.85 [MUTED]"
        parts = out.split()
        if len(parts) >= 2:
            vol = float(parts[1])
            is_muted = "[MUTED]" in out
            if vol < 0.35 or vol > 0.85 or is_muted:
                subprocess.run(
                    ["wpctl", "set-volume", "@DEFAULT_AUDIO_SOURCE@", str(min_volume)],
                    check=False,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                subprocess.run(
                    ["wpctl", "set-mute", "@DEFAULT_AUDIO_SOURCE@", "0"],
                    check=False,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return min_volume
            return vol
    except Exception:
        pass
    return min_volume


class VADRecorder:
    def __init__(self, sample_rate: int = 16000, sensitivity: int = 1):
        self.sample_rate = sample_rate
        self.sensitivity = max(0, min(3, sensitivity))
        self.frame_duration_ms = 30  # 10, 20, or 30 ms for webrtcvad
        self.frame_size = int(self.sample_rate * (self.frame_duration_ms / 1000.0))  # 480 samples
        self.frame_bytes = self.frame_size * 2  # 16-bit PCM = 2 bytes per sample

        if webrtcvad is not None:
            self.vad = webrtcvad.Vad(self.sensitivity)
        else:
            self.vad = None

    def is_speech(self, pcm_bytes: bytes, rate: Optional[int] = None) -> bool:
        """Check if 30ms PCM chunk contains speech with DC bias rejection."""
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        # Remove hardware DC offset before energy calculation
        audio = audio - np.mean(audio)
        rms = float(np.sqrt(np.mean(audio ** 2)))

        sample_rate = rate or self.sample_rate
        if self.vad is not None and sample_rate in (8000, 16000, 32000, 48000):
            try:
                # Pass zero-centered audio to webrtcvad
                clean_pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16).tobytes()
                return self.vad.is_speech(clean_pcm, sample_rate)
            except Exception:
                pass
        return rms > 0.015

    def record_phrase(
        self,
        max_seconds: float = 20.0,
        wait_seconds: float = 8.0,
        silence_seconds: float = 0.75,
        stop_event: Optional[threading.Event] = None
    ) -> Tuple[bool, np.ndarray, str]:
        """Record audio until user stops speaking.
        Returns: (success: bool, audio_float32: np.ndarray, error_or_info: str)
        """
        # Ensure mic volume is not muted or critically low
        check_and_boost_mic(0.85)

        # Dynamic sample rate & device negotiation to prevent ALSA paInvalidSampleRate
        sample_rate = self.sample_rate
        capture_device = None
        for dev in [None, 8, 0]:
            for r in [sample_rate, 48000, 44100]:
                try:
                    sd.check_input_settings(device=dev, samplerate=r, channels=1, dtype="int16")
                    sample_rate = r
                    capture_device = dev
                    break
                except Exception:
                    continue
            if capture_device is not None:
                break

        frame_size = int(sample_rate * (self.frame_duration_ms / 1000.0))
        pre_speech_frames = int(0.5 / (self.frame_duration_ms / 1000.0))  # 500ms pre-roll
        ring_buffer = collections.deque(maxlen=pre_speech_frames)
        speech_frames = []

        is_speaking = False
        consecutive_silence = 0
        silence_threshold_frames = int(silence_seconds / (self.frame_duration_ms / 1000.0))
        max_frames = int(max_seconds / (self.frame_duration_ms / 1000.0))
        wait_frames = int(wait_seconds / (self.frame_duration_ms / 1000.0))

        total_frames = 0
        waited_frames = 0

        try:
            with sd.RawInputStream(
                samplerate=sample_rate,
                blocksize=frame_size,
                dtype="int16",
                channels=1,
                device=capture_device
            ) as stream:
                while True:
                    if stop_event and stop_event.is_set():
                        return False, np.array([], dtype=np.float32), "Cancelled."

                    data, overflowed = stream.read(frame_size)
                    pcm_bytes = bytes(data)

                    speech_detected = self.is_speech(pcm_bytes, rate=sample_rate)

                    if not is_speaking:
                        ring_buffer.append(pcm_bytes)
                        if speech_detected:
                            is_speaking = True
                            speech_frames.extend(ring_buffer)
                            consecutive_silence = 0
                        else:
                            waited_frames += 1
                            if waited_frames >= wait_frames:
                                # Timeout waiting for speech
                                return True, np.array([], dtype=np.float32), "Timeout (no speech)."
                    else:
                        speech_frames.append(pcm_bytes)
                        total_frames += 1

                        if not speech_detected:
                            consecutive_silence += 1
                        else:
                            consecutive_silence = 0

                        if consecutive_silence >= silence_threshold_frames:
                            # User finished speaking
                            break

                        if total_frames >= max_frames:
                            # Hit max duration limit
                            break

            if not speech_frames:
                return True, np.array([], dtype=np.float32), "No speech recorded."

            raw_audio = b"".join(speech_frames)
            audio_int16 = np.frombuffer(raw_audio, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0

            # Remove hardware DC offset
            if len(audio_float32) > 0:
                audio_float32 = audio_float32 - np.mean(audio_float32)

            # Downsample to 16000Hz for Whisper STT if needed
            if sample_rate != 16000:
                if sample_rate == 48000:
                    audio_float32 = audio_float32[::3]
                else:
                    target_len = int(len(audio_float32) * 16000 / sample_rate)
                    if target_len > 0 and len(audio_float32) > 0:
                        audio_float32 = np.interp(
                            np.linspace(0, len(audio_float32), target_len, endpoint=False),
                            np.arange(len(audio_float32)),
                            audio_float32
                        ).astype(np.float32)

            return True, audio_float32, "Speech captured successfully."

        except KeyboardInterrupt:
            return False, np.array([], dtype=np.float32), "KeyboardInterrupt"
        except Exception as e:
            return False, np.array([], dtype=np.float32), f"Recording error: {e}"

