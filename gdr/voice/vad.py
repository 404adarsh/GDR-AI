"""Robust Voice Activity Detection (VAD) audio recording for GDR AI.
Uses webrtcvad with silero-vad fallback, rolling pre-buffer, and clean cancellation.
"""

import collections
import subprocess
import threading
import time
from typing import Optional, Tuple, Union, Dict, Any, List
import numpy as np

# Lazy / safe import of sounddevice — PortAudio may not be initializable on
# headless machines or when ALSA xruns corrupt its state.  We defer the actual
# init failure to the point where audio recording is attempted rather than
# crashing the entire application on module import.
try:
    import sounddevice as sd
    _SD_AVAILABLE = True
except Exception as _sd_import_error:
    sd = None  # type: ignore
    _SD_AVAILABLE = False
    import logging as _log
    _log.getLogger("gdr.voice.vad").warning(
        f"sounddevice/PortAudio failed to initialize: {_sd_import_error}. "
        "Voice recording is disabled. Fix ALSA/PipeWire and restart."
    )

try:
    import webrtcvad
except ImportError:
    webrtcvad = None


import os

# Guarantee XDG_RUNTIME_DIR and ALSA duplex configuration
def ensure_audio_environment():
    """Ensure audio runtime environment is properly set up for duplex audio capture.
    On Linux: configures ALSA/PipeWire/PulseAudio.
    On Windows: ensures microphone access and sets UTF-8 encoding for console output.
    """
    import os
    import sys
    from pathlib import Path

    # Windows-specific audio environment setup
    if sys.platform == "win32":
        # Ensure UTF-8 encoding so audio device names with special chars don't crash
        if not os.environ.get("PYTHONUTF8"):
            os.environ["PYTHONUTF8"] = "1"
        if not os.environ.get("PYTHONIOENCODING"):
            os.environ["PYTHONIOENCODING"] = "utf-8"
        # Windows uses Windows Audio Session API (WASAPI) via PortAudio — no further config needed
        return

    # Linux/macOS: Guarantee XDG_RUNTIME_DIR is set for PipeWire / PortAudio
    if "XDG_RUNTIME_DIR" not in os.environ or not os.environ["XDG_RUNTIME_DIR"]:
        try:
            os.environ["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
        except Exception:
            os.environ["XDG_RUNTIME_DIR"] = "/run/user/1000"

    # If PipeWire or PulseAudio is running, preserve system ALSA routing so audio is shared (e.g. with Google Meet)
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    has_sound_server = False
    if runtime:
        if (Path(runtime) / "pipewire-0").exists() or (Path(runtime) / "pulse" / "native").exists():
            has_sound_server = True

    # Only fall back to dmix/dsnoop if no sound server exists, user has no ~/.asoundrc, and hw:0,0 is physically present
    asound_user = Path(os.path.expanduser("~/.asoundrc"))
    if not has_sound_server and "ALSA_CONFIG_PATH" not in os.environ and not asound_user.exists():
        if Path("/proc/asound/card0").exists():
            cfg_path = Path("/tmp/gdr_asound.conf")
            if not cfg_path.exists():
                try:
                    cfg_path.write_text("""# GDR Audio — dmix/dsnoop sharing
pcm.!default {
    type asym
    playback.pcm "dmixed"
    capture.pcm "dsnoop_cap"
}
pcm.dmixed {
    type dmix
    ipc_key 1024
    ipc_key_add_uid true
    slave { pcm "hw:0,0"; rate 48000; channels 2; period_size 1024; buffer_size 8192 }
}
pcm.dsnoop_cap {
    type dsnoop
    ipc_key 1025
    ipc_key_add_uid true
    slave { pcm "hw:0,0"; rate 48000; channels 2; period_size 1024; buffer_size 8192 }
}
ctl.!default { type hw; card 0 }
""")
                except Exception:
                    pass
            if cfg_path.exists():
                os.environ["ALSA_CONFIG_PATH"] = str(cfg_path)


ensure_audio_environment()


def check_and_boost_mic(min_volume: float = 0.85) -> float:
    """Ensure microphone source volume is adequately set without clipping.
    Works on Windows (via pycaw/Windows Core Audio), Linux (PipeWire/ALSA).
    """
    ensure_audio_environment()
    env = os.environ.copy()

    # Windows: use pycaw (Windows Core Audio API)
    import sys
    if sys.platform == "win32":
        try:
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from ctypes import POINTER, cast
            from comtypes import CLSCTX_ALL
            devices = AudioUtilities.GetAllDevices()
            for device in devices:
                if device.state != 1:  # 1 = Active
                    continue
                name = (device.FriendlyName or "").lower()
                if "microphone" not in name and "mic" not in name:
                    continue
                try:
                    interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    muted = volume.GetMute()
                    vol = volume.GetMasterVolumeLevelScalar()
                    if muted:
                        volume.SetMute(0, None)
                    if vol < min_volume:
                        volume.SetMasterVolumeLevelScalar(1.0, None)
                        return 1.0
                    return vol
                except Exception:
                    continue
        except ImportError:
            pass  # pycaw not installed — mic volume unchanged
        return min_volume

    # Linux/macOS: Try PipeWire / WirePlumber
    try:
        out = subprocess.check_output(
            ["wpctl", "get-volume", "@DEFAULT_AUDIO_SOURCE@"],
            stderr=subprocess.DEVNULL,
            env=env,
            text=True
        ).strip()
        parts = out.split()
        if len(parts) >= 2:
            vol = float(parts[1])
            is_muted = "[MUTED]" in out
            if vol < 0.40 or is_muted:
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

    # Linux fallback: Try ALSA amixer
    try:
        subprocess.run(["amixer", "-c", "0", "sset", "Capture", "cap", "unmute", f"{int(min_volume*100)}%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["amixer", "-c", "0", "sset", "Master", "unmute", f"{int(min_volume*100)}%"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

    return min_volume


def query_audio_devices() -> dict:
    """Query available input (microphone) and output (speaker) devices across the system."""
    ensure_audio_environment()

    if not _SD_AVAILABLE:
        return {
            "inputs": [], "outputs": [],
            "default_input": -1, "default_output": -1,
            "selected_input": -1, "selected_output": -1,
            "error": "PortAudio not available. Run: sudo apt install portaudio19-dev && pip install sounddevice"
        }

    try:
        from gdr.config import load_config
        cfg = load_config()
        v_cfg = cfg.get("voice", {})
        selected_in = v_cfg.get("input_device")
        selected_out = v_cfg.get("output_device")
    except Exception:
        selected_in = None
        selected_out = None

    try:
        devices = sd.query_devices()
        default_in, default_out = sd.default.device
    except Exception:
        devices = []
        default_in, default_out = -1, -1

    input_devices = []
    output_devices = []

    for i, d in enumerate(devices):
        if d.get("max_input_channels", 0) > 0:
            is_sel = (selected_in is not None and str(selected_in) == str(i)) or (selected_in is None and i == default_in)
            input_devices.append({
                "id": i,
                "name": d.get("name", f"Microphone #{i}"),
                "channels": d.get("max_input_channels"),
                "default_samplerate": int(d.get("default_samplerate", 44100)),
                "is_default": (i == default_in),
                "is_selected": is_sel
            })
        if d.get("max_output_channels", 0) > 0:
            is_sel = (selected_out is not None and str(selected_out) == str(i)) or (selected_out is None and i == default_out)
            output_devices.append({
                "id": i,
                "name": d.get("name", f"Speaker/Headphone #{i}"),
                "channels": d.get("max_output_channels"),
                "default_samplerate": int(d.get("default_samplerate", 44100)),
                "is_default": (i == default_out),
                "is_selected": is_sel
            })

    return {
        "inputs": input_devices,
        "outputs": output_devices,
        "default_input": default_in,
        "default_output": default_out,
        "selected_input": selected_in if selected_in is not None else default_in,
        "selected_output": selected_out if selected_out is not None else default_out
    }


def fix_and_boost_microphones() -> dict:
    """Unmutes system audio sources, boosts volume to 85%, and verifies stream opening."""
    ensure_audio_environment()
    vol = check_and_boost_mic(0.85)
    devs = query_audio_devices()
    test_res = test_microphone_input()
    return {
        "success": test_res.get("success", False),
        "message": "Microphone unmuted and boosted to 85% volume." if test_res.get("success") else "Microphone unmuted, but recording check failed. Check permissions.",
        "volume": vol,
        "test": test_res,
        "devices": devs
    }


def _sort_input_devices(dev_ids: List[int]) -> List[int]:
    """Sort input devices prioritizing virtual/shared sound servers (pulse, pipewire, default)
    over exclusive direct ALSA hardware (hw:) to prevent Google Meet / ALSA locking conflicts.
    """
    if not _SD_AVAILABLE or not dev_ids:
        return dev_ids

    def _priority(dev_id: int) -> int:
        try:
            d = sd.query_devices(dev_id)
            name = (d.get("name") or "").lower()
            if "pulse" in name or "pipewire" in name:
                return 0
            if "default" in name or "sysdefault" in name:
                return 1
            if "hw:" in name:
                return 10
            return 5
        except Exception:
            return 20

    return sorted(dev_ids, key=_priority)


def test_microphone_input(device=None, duration: float = 0.5) -> dict:
    """Perform a short capture test on the designated microphone and measure audio signal."""
    ensure_audio_environment()

    if not _SD_AVAILABLE:
        return {
            "success": False,
            "error": "PortAudio/sounddevice not available. Cannot record. Fix ALSA and restart GDR."
        }

    chosen_dev = device
    if chosen_dev is None:
        try:
            from gdr.config import load_config
            cfg = load_config()
            chosen_dev = cfg.get("voice", {}).get("input_device")
        except Exception:
            chosen_dev = None

    # Discover devices with verified input channels to prevent ALSA crashes on output-only devices
    valid_input_ids = []
    try:
        devs = sd.query_devices()
        for i, d in enumerate(devs):
            if d.get("max_input_channels", 0) > 0:
                valid_input_ids.append(i)
    except Exception:
        pass

    valid_input_ids = _sort_input_devices(valid_input_ids)

    if not valid_input_ids and chosen_dev is None:
        return {
            "success": False,
            "error": "No microphone hardware input detected on this system. Use browser microphone in Web UI."
        }

    candidates = []
    if chosen_dev is not None:
        candidates.append(chosen_dev)
    if None not in candidates:
        candidates.append(None)
    for dev_id in valid_input_ids:
        if dev_id not in candidates:
            candidates.append(dev_id)

    for dev in candidates:
        for r in [48000, 16000, 44100]:
            for ch in [1, 2]:
                try:
                    sd.check_input_settings(device=dev, samplerate=r, channels=ch, dtype="int16")
                    with sd.InputStream(device=dev, samplerate=r, channels=ch, dtype="int16") as stream:
                        samples = int(r * duration)
                        data, overflowed = stream.read(samples)
                        audio = data.astype(np.float32) / 32768.0
                        rms = float(np.sqrt(np.mean(audio ** 2)))
                        peak = float(np.max(np.abs(audio)))
                        dev_name = f"Microphone #{dev}"
                        try:
                            dinfo = sd.query_devices(dev, "input")
                            dev_name = dinfo.get("name", str(dev))
                        except Exception:
                            pass
                        return {
                            "success": True,
                            "device": dev,
                            "device_name": dev_name,
                            "sample_rate": r,
                            "channels": ch,
                            "rms": round(rms, 4),
                            "peak": round(peak, 4),
                            "is_silent": rms < 0.005
                        }
                except Exception:
                    continue

    return {
        "success": False,
        "error": "Unable to capture audio from available microphones. Use browser microphone."
    }


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
        max_seconds: float = 60.0,
        wait_seconds: float = 10.0,
        silence_seconds: float = 0.75,
        stop_event: Optional[threading.Event] = None,
        device: Optional[Union[int, str]] = None
    ) -> Tuple[bool, np.ndarray, str]:
        """Record audio until user stops speaking with dynamic endpointing.
        Returns: (success: bool, audio_float32: np.ndarray, error_or_info: str)
        """
        if not _SD_AVAILABLE:
            return False, np.array([], dtype=np.float32), "PortAudio not available. Cannot record."

        # Ensure mic volume is not muted or critically low
        check_and_boost_mic(0.85)

        # Dynamic sample rate & device negotiation to prevent ALSA paInvalidSampleRate
        sample_rate = 16000
        channels = 1
        capture_device = None

        try:
            from gdr.config import load_config
            cfg = load_config()
            configured_dev = device if device is not None else cfg.get("voice", {}).get("input_device")
        except Exception:
            configured_dev = device

        # Discover actual input devices to prevent ALSA errors on output-only devices
        valid_input_ids = []
        try:
            devs = sd.query_devices()
            for i, d in enumerate(devs):
                if d.get("max_input_channels", 0) > 0:
                    valid_input_ids.append(i)
        except Exception:
            pass

        valid_input_ids = _sort_input_devices(valid_input_ids)

        candidate_devices = []
        if configured_dev is not None:
            candidate_devices.append(configured_dev)
        if None not in candidate_devices:
            candidate_devices.append(None)
        for dev_id in valid_input_ids:
            if dev_id not in candidate_devices:
                candidate_devices.append(dev_id)

        if not candidate_devices:
            return False, np.array([], dtype=np.float32), "No hardware microphone input device found on host."

        stream = None
        for dev in candidate_devices:
            for r in [48000, 16000, 44100]:
                for ch in [1, 2]:
                    fsize = int(r * (self.frame_duration_ms / 1000.0))
                    try:
                        sd.check_input_settings(device=dev, samplerate=r, channels=ch, dtype="int16")
                        s = sd.RawInputStream(
                            samplerate=r,
                            blocksize=fsize,
                            dtype="int16",
                            channels=ch,
                            device=dev
                        )
                        s.start()
                        stream = s
                        sample_rate = r
                        channels = ch
                        capture_device = dev
                        frame_size = fsize
                        break
                    except Exception:
                        continue
                if stream is not None:
                    break
            if stream is not None:
                break

        if stream is None:
            return False, np.array([], dtype=np.float32), "Could not initialize any hardware microphone stream (in use or busy)."

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
            with stream:
                while True:
                    if stop_event and stop_event.is_set():
                        return False, np.array([], dtype=np.float32), "Cancelled."

                    data, overflowed = stream.read(frame_size)
                    chunk = np.frombuffer(data, dtype=np.int16)
                    if channels > 1:
                        chunk = chunk.reshape(-1, channels)[:, 0]
                    pcm_bytes = chunk.tobytes()

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

                        # Dynamic endpointing: short phrases (e.g. "Hello") end in ~500ms;
                        # longer sentences allow natural 750ms breathing pauses without cutting off.
                        speech_sec = (total_frames * self.frame_duration_ms) / 1000.0
                        needed_silence_frames = (
                            int(0.50 / (self.frame_duration_ms / 1000.0))
                            if speech_sec < 1.2
                            else int(0.75 / (self.frame_duration_ms / 1000.0))
                        )

                        if consecutive_silence >= needed_silence_frames:
                            # User naturally finished speaking
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

