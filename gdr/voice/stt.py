"""Speech-to-Text (STT) engine for GDR AI.
Supports local faster-whisper (tiny/base/small) with optional Sarvam STT for Hindi/Hinglish.
"""

import io
import os
import wave
from typing import Optional, Union
import numpy as np

from gdr.safety.secrets import get_secret

_WHISPER_INSTANCE = None


def get_whisper_model(model_name: str = "tiny"):
    global _WHISPER_INSTANCE
    if _WHISPER_INSTANCE is None:
        from faster_whisper import WhisperModel
        # 1. Try local cache first for fast offline startup
        for m in [model_name, "tiny"]:
            try:
                _WHISPER_INSTANCE = WhisperModel(
                    m,
                    device="cpu",
                    compute_type="int8",
                    local_files_only=True
                )
                return _WHISPER_INSTANCE
            except Exception:
                continue

        # 2. If not cached locally, allow downloading online
        try:
            _WHISPER_INSTANCE = WhisperModel(
                "tiny",
                device="cpu",
                compute_type="int8",
                local_files_only=False
            )
            return _WHISPER_INSTANCE
        except Exception as e:
            raise e
    return _WHISPER_INSTANCE


class SpeechToText:
    def __init__(self, engine: str = "faster-whisper", model_name: str = "tiny"):
        self.engine = engine.lower()
        self.model_name = model_name

    def transcribe(
        self,
        audio_data: Union[np.ndarray, bytes, str],
        sample_rate: int = 16000,
        language: Optional[str] = None
    ) -> str:
        """Transcribe audio to text.
        audio_data: float32 numpy array, WAV bytes, or path to audio file.
        """
        sarvam_key = get_secret("SARVAM_API_KEY")
        if sarvam_key:
            try:
                text = self._transcribe_sarvam(audio_data, sample_rate, sarvam_key, language)
                if text and text.strip():
                    return text.strip()
            except Exception as e:
                print(f"⚠️ Sarvam STT failed ({e}), falling back to local Whisper.")

        return self._transcribe_local(audio_data, language)

    def _transcribe_local(self, audio_data: Union[np.ndarray, bytes, str], language: Optional[str]) -> str:
        model = get_whisper_model(self.model_name)
        audio_arr: Optional[np.ndarray] = None

        if isinstance(audio_data, np.ndarray):
            audio_arr = audio_data.astype(np.float32)

        elif isinstance(audio_data, str):
            try:
                import soundfile as sf
                data, sr = sf.read(audio_data, dtype="float32")
                if data.ndim > 1:
                    data = data.mean(axis=1)
                if sr != 16000 and len(data) > 0:
                    target_len = int(len(data) * 16000 / sr)
                    data = np.interp(
                        np.linspace(0, len(data), target_len, endpoint=False),
                        np.arange(len(data)),
                        data
                    ).astype(np.float32)
                audio_arr = data.astype(np.float32)
            except Exception as e:
                print(f"Failed to read audio file via soundfile: {e}")

        elif isinstance(audio_data, bytes):
            if len(audio_data) == 0:
                return ""

            # 1. PyAV safe container decode (handles WebM, Opus, OGG, MP3, WAV from browser)
            try:
                import av
                container = av.open(io.BytesIO(audio_data))
                if container.streams.audio:
                    stream = container.streams.audio[0]
                    resampler = av.audio.resampler.AudioResampler(
                        format='flt',
                        layout='mono',
                        rate=16000
                    )
                    all_frames = []
                    for frame in container.decode(stream):
                        resampled_list = resampler.resample(frame)
                        if resampled_list:
                            for rf in resampled_list:
                                all_frames.append(rf.to_ndarray()[0])
                    resampled_list = resampler.resample(None)
                    if resampled_list:
                        for rf in resampled_list:
                            all_frames.append(rf.to_ndarray()[0])
                    if all_frames:
                        audio_arr = np.concatenate(all_frames).astype(np.float32)
            except Exception:
                pass

            # 2. Soundfile decode (WAV, FLAC, AIFF) fallback
            if audio_arr is None:
                try:
                    import soundfile as sf
                    data, sr = sf.read(io.BytesIO(audio_data), dtype="float32")
                    if data.ndim > 1:
                        data = data.mean(axis=1)
                    if sr != 16000 and len(data) > 0:
                        target_len = int(len(data) * 16000 / sr)
                        data = np.interp(
                            np.linspace(0, len(data), target_len, endpoint=False),
                            np.arange(len(data)),
                            data
                        ).astype(np.float32)
                    audio_arr = data.astype(np.float32)
                except Exception:
                    pass

        if audio_arr is None or len(audio_arr) < 1600:
            return ""

        # Remove DC offset to zero-center audio
        audio_arr = audio_arr - np.mean(audio_arr)

        # Check RMS energy to reject pure silence while keeping soft laptop speech
        rms = float(np.sqrt(np.mean(audio_arr ** 2)))
        if rms < 0.0015:
            return ""

        # Normalize amplitude for genuine speech so Whisper gets high SNR signal
        max_v = float(np.max(np.abs(audio_arr)))
        if max_v >= 0.002:
            audio_arr = (audio_arr / max_v) * 0.95

        u_name = os.environ.get("USER_NAME", "User")
        a_name = os.environ.get("ASSISTANT_NAME", "Aarushi")
        transcribe_kwargs = {
            "beam_size": 5,
            "vad_filter": True,
            "vad_parameters": dict(
                min_silence_duration_ms=250,
                speech_pad_ms=300,
                threshold=0.20
            ),
            "initial_prompt": f"{a_name}, {u_name}, सुनो, बताओ, क्या हाल है, Hindi, English, Hinglish, conversation, chat, hello, sweetheart",
            "condition_on_previous_text": False
        }
        if language:
            transcribe_kwargs["language"] = language

        try:
            segments, _ = model.transcribe(audio_arr, **transcribe_kwargs)
            raw_text = " ".join(s.text.strip() for s in segments).strip()

            # Hallucination and repetition filter
            import re
            cleaned_lower = re.sub(r"[^\w\s]", "", raw_text.lower()).strip()
            known_hallucinations = {
                "you", "thank you", "thanks for watching", "thank you for watching",
                "please subscribe", "subtitles by", "you cant get out of the way",
                "1st st", "1st street", "mbc", "bye", "amaraorg", ""
            }
            if cleaned_lower in known_hallucinations:
                return ""

            # Filter repetitive hallucination loops on ambient noise (e.g., "hello, hello, hello...")
            words = cleaned_lower.split()
            if len(words) >= 3:
                unique_words = set(words)
                if len(unique_words) <= 2 or (len(words) >= 6 and len(words) / len(unique_words) >= 2.5):
                    return ""

            return raw_text
        except Exception as e:
            print(f"Whisper transcription error: {e}")
            return ""

    def _transcribe_sarvam(
        self,
        audio_data: Union[np.ndarray, bytes, str],
        sample_rate: int,
        api_key: str,
        language: Optional[str]
    ) -> str:
        from sarvamai import SarvamAI
        client = SarvamAI(api_subscription_key=api_key)

        if isinstance(audio_data, str) and os.path.exists(audio_data):
            with open(audio_data, "rb") as f:
                res = client.speech_to_text.transcribe(
                    file=f,
                    model="saaras:v3",
                    language_code="hi-IN" if (language and "hi" in language) else "unknown"
                )
                return res.transcript.strip()
        else:
            # Build WAV buffer in-memory
            buf = io.BytesIO()
            if isinstance(audio_data, np.ndarray):
                int16_data = (np.clip(audio_data, -1.0, 1.0) * 32767.0).astype(np.int16)
                with wave.open(buf, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(sample_rate)
                    wf.writeframes(int16_data.tobytes())
                buf.name = "audio.wav"
            else:
                buf.write(audio_data)
                if isinstance(audio_data, (bytes, bytearray)) and audio_data.startswith(b"RIFF"):
                    buf.name = "audio.wav"
                else:
                    buf.name = "audio.webm"

            buf.seek(0)
            res = client.speech_to_text.transcribe(
                file=buf,
                model="saaras:v3",
                language_code="hi-IN" if (language and "hi" in language) else "unknown"
            )
            return res.transcript.strip()

