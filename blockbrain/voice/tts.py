"""Text-to-Speech (TTS) engine for blockbrain AI.
Supports Edge-TTS Neural (studio-grade Hindi & English), Piper offline neural,
Sarvam Bulbul TTS for Indian languages, gTTS, and espeak-ng fallback.
"""

from datetime import datetime, timezone
import io
import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Optional, Dict, Any, List
import wave

from blockbrain.safety.secrets import get_secret

logger = logging.getLogger("blockbrain.voice.tts")

_PIPER_VOICE_CACHE = {}
_ACTIVE_PLAYBACK_PROC = None

# Studio-grade Neural Voice Registry
VOICE_PROFILES = {
    "hi_male": {
        "engine": "edge",
        "voice": "hi-IN-MadhurNeural",
        "lang": "hi-IN",
        "label": "Hindi (Madhur Neural - मधुर)",
        "description": "Studio-grade natural Hindi male voice, crystal-clear Hindi and Hinglish pronunciation."
    },
    "hi_female": {
        "engine": "edge",
        "voice": "hi-IN-SwaraNeural",
        "lang": "hi-IN",
        "label": "Hindi (Swara Neural - स्वरा)",
        "description": "Studio-grade natural Hindi female voice, expressive and fluent."
    },
    "en_male": {
        "engine": "edge",
        "voice": "en-US-GuyNeural",
        "lang": "en-US",
        "label": "English (Guy Neural - Jarvis Style)",
        "description": "Deep, articulate, studio-grade natural American English male voice."
    },
    "en_female": {
        "engine": "edge",
        "voice": "en-US-JennyNeural",
        "lang": "en-US",
        "label": "English (Jenny Neural)",
        "description": "Natural, pleasant American English female voice."
    },
    "en_aria": {
        "engine": "edge",
        "voice": "en-US-AriaNeural",
        "lang": "en-US",
        "label": "English (Aria Neural - Expressive)",
        "description": "Warm, expressive, high-clarity American female voice."
    },
    "en_christopher": {
        "engine": "edge",
        "voice": "en-US-ChristopherNeural",
        "lang": "en-US",
        "label": "English (Christopher Neural - Executive)",
        "description": "Authoritative, resonant American male voice."
    },
    "en_ryan": {
        "engine": "edge",
        "voice": "en-GB-RyanNeural",
        "lang": "en-GB",
        "label": "British English (Ryan Neural - Butler Jarvis)",
        "description": "Polite, sophisticated British English male voice."
    },
    "en_sonia": {
        "engine": "edge",
        "voice": "en-GB-SoniaNeural",
        "lang": "en-GB",
        "label": "British English (Sonia Neural)",
        "description": "Refined British English female voice."
    },
    "en_indian": {
        "engine": "edge",
        "voice": "en-IN-PrabhatNeural",
        "lang": "en-IN",
        "label": "Indian English (Prabhat Neural)",
        "description": "Clear Indian English accent with natural pacing for Hinglish terms."
    },
    "en_neerja": {
        "engine": "edge",
        "voice": "en-IN-NeerjaNeural",
        "lang": "en-IN",
        "label": "Indian English (Neerja Neural)",
        "description": "Fluent, warm Indian English female voice."
    },
    "piper_offline": {
        "engine": "piper",
        "voice": "en_US-lessac-medium",
        "lang": "en-US",
        "label": "Piper Offline Neural (Lessac)",
        "description": "100% offline neural voice running on CPU without internet."
    }
}


def clean_text_for_speech(text: str) -> str:
    """Strip markdown, URLs, code blocks, emojis, model tags, and code punctuation for speech."""
    t = str(text or "")

    # 1. Strip bracketed model prefixes and system tags (prevents TTS pronouncing model names/brackets)
    t = re.sub(r"\[(?:Offline Local AI Mode|blockbrain Fast Lane|blockbrain Heavy MoE Lane|Local System AI|vol|FACT|PREFERENCE|PERSONA|STYLE|Query Ingestion|Policy Verification|Agent Response)[^\]]*\]", " ", t, flags=re.I)
    t = re.sub(r"\[[^\]]*\b(?:Mode|Engine|Model|Lane|tokens?)\b[^\]]*\]", " ", t, flags=re.I)

    # 2. Clean code blocks and URLs
    t = re.sub(r"```.*?```", " ", t, flags=re.S)
    t = re.sub(r"`.*?`", " ", t)
    t = re.sub(r"https?://\S+", " link ", t)

    # 3. Strip code formatting symbols, underscores, brackets, and markdown
    t = re.sub(r"[{}()\[\]|~*#_\\<>=^/@]", " ", t)

    # 4. Replace musical notes, bullets, and symbols
    for sym in ["♪", "♫", "♩", "♬", "•", "●", "◆", "■", "★", "→", "►"]:
        t = t.replace(sym, " ")

    # 5. Clean repeated dots, dashes, and colons
    t = re.sub(r"\.{2,}", ". ", t)
    t = re.sub(r":\s+", ", ", t)
    t = re.sub(r"-{2,}", " ", t)

    # 6. Strip emojis and special Unicode symbols
    t = re.sub(r"[\U00010000-\U0010ffff\u2600-\u2669\u266C-\u27BF\u2B00-\u2BFF]", "", t)

    return re.sub(r"\s+", " ", t).strip()[:1200]


def detect_language(text: str) -> str:
    """Detect whether text is Hindi (Devanagari or Hinglish) or English."""
    clean = str(text or "").strip()
    if not clean:
        return "en-US"

    # 1. Direct Devanagari script detection
    if re.search(r"[\u0900-\u097F]", clean):
        return "hi-IN"

    # 2. Hinglish / Transliterated Hindi words detection
    hinglish_keywords = {
        "namaste", "namaskar", "kaise", "kaisi", "kaisa", "haal", "kya", "kyun", "kyon",
        "acche", "achhe", "theek", "shukriya", "dhanyavad", "dhanyawad", "batao", "bataiye",
        "karo", "kariye", "mera", "meri", "mere", "tumhara", "tumhari", "aapka", "aapki",
        "hum", "humara", "kahan", "kidhar", "suno", "sunao", "bolo", "bhai", "dost", "yaar",
        "aaj", "kal", "mausam", "kripya", "alvida", "samajh", "aaya", "nahin", "nahi", "haan",
        "accha", "achha", "bahut", "thoda", "kuch", "sab", "log", "apna", "apne", "chalo"
    }
    words = re.findall(r"\b[a-zA-Z]+\b", clean.lower())
    if words:
        matches = sum(1 for w in words if w in hinglish_keywords)
        if matches >= 2 or (len(words) <= 5 and matches >= 1):
            return "hi-IN"

    return "en-US"


def stop_speaking():
    """Immediately kill any audio playback currently running."""
    global _ACTIVE_PLAYBACK_PROC
    if _ACTIVE_PLAYBACK_PROC and _ACTIVE_PLAYBACK_PROC.poll() is None:
        try:
            _ACTIVE_PLAYBACK_PROC.terminate()
            _ACTIVE_PLAYBACK_PROC.wait(timeout=0.5)
        except Exception:
            try:
                _ACTIVE_PLAYBACK_PROC.kill()
            except Exception:
                pass
    _ACTIVE_PLAYBACK_PROC = None


def _play_audio(file_path: str):
    """Play any audio file (MP3, WAV, etc.) using PipeWire pw-play, paplay, or aplay."""
    global _ACTIVE_PLAYBACK_PROC
    stop_speaking()

    # If it is MP3 and pw-play or aplay is used, convert to temporary WAV via soundfile
    play_path = file_path
    temp_wav = None
    if file_path.lower().endswith(".mp3"):
        try:
            import soundfile as sf
            data, samplerate = sf.read(file_path)
            fd, temp_wav = tempfile.mkstemp(suffix=".wav", prefix="blockbrain_play_")
            os.close(fd)
            sf.write(temp_wav, data, samplerate)
            play_path = temp_wav
        except Exception as e:
            logger.warning(f"Failed to convert MP3 to WAV via soundfile: {e}")

    cmd = None
    if shutil.which("pw-play"):
        cmd = ["pw-play", play_path]
    elif shutil.which("paplay"):
        cmd = ["paplay", play_path]
    elif shutil.which("aplay"):
        cmd = ["aplay", "-q", play_path]

    try:
        if cmd:
            env = os.environ.copy()
            if "XDG_RUNTIME_DIR" not in env or not env["XDG_RUNTIME_DIR"]:
                env["XDG_RUNTIME_DIR"] = f"/run/user/{os.getuid()}"
            _ACTIVE_PLAYBACK_PROC = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            _ACTIVE_PLAYBACK_PROC.wait(timeout=180)
    finally:
        if temp_wav and os.path.exists(temp_wav):
            try:
                os.remove(temp_wav)
            except Exception:
                pass


def _play_wav(wav_path: str):
    """Backwards-compatible wrapper for playing WAV files."""
    _play_audio(wav_path)


def get_piper_model_path() -> Optional[Path]:
    """Dynamically resolve Piper ONNX model path across host directories."""
    candidates = [
        Path.home() / "blockbrainagent" / "models" / "piper" / "en_US-lessac-medium.onnx",
        Path(__file__).resolve().parent.parent.parent / "models" / "piper" / "en_US-lessac-medium.onnx",
        Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain")) / "models" / "piper" / "en_US-lessac-medium.onnx",
    ]
    for c in candidates:
        if c.exists() and c.stat().st_size > 1000000:
            return c
    return None


def synthesize_speech_file(
    text: str,
    output_path: Optional[str] = None,
    lang: str = "auto",
    voice: Optional[str] = None,
    target_format: str = "mp3"
) -> str:
    """Synthesize speech into a high-quality audio file (MP3 or WAV).
    Uses Edge-TTS Neural for studio quality Hindi & English when online,
    and instantly fails over to local Piper neural on CPU when offline.
    """
    global _PIPER_VOICE_CACHE
    clean = clean_text_for_speech(text)
    if not clean:
        raise ValueError("Empty text after cleaning")

    resolved_lang = detect_language(clean) if (not lang or lang == "auto") else lang
    is_hindi = "hi" in resolved_lang.lower()

    if not voice or voice in ("auto", "neural_auto", "default"):
        voice = "hi-IN-MadhurNeural" if is_hindi else "en-US-GuyNeural"
    elif voice in VOICE_PROFILES:
        voice = VOICE_PROFILES[voice]["voice"]
    else:
        alias_map = {
            "hi_madhur": "hi-IN-MadhurNeural",
            "hi_swara": "hi-IN-SwaraNeural",
            "en_guy": "en-US-GuyNeural",
            "en_jenny": "en-US-JennyNeural",
            "en_aria": "en-US-AriaNeural",
            "en_christopher": "en-US-ChristopherNeural",
            "en_ryan": "en-GB-RyanNeural",
            "en_sonia": "en-GB-SoniaNeural",
            "en_indian": "en-IN-PrabhatNeural",
            "en_prabhat": "en-IN-PrabhatNeural",
            "en_neerja": "en-IN-NeerjaNeural",
            "piper": "en_US-lessac-medium",
        }
        voice = alias_map.get(voice, voice)

    if not output_path:
        suffix = f".{target_format.lower()}"
        fd, output_path = tempfile.mkstemp(suffix=suffix, prefix="blockbrain_tts_")
        os.close(fd)

    from blockbrain.core.network import is_online
    online = is_online()
    is_piper_requested = (voice and "piper" in voice.lower()) or (not online)

    # 1. If offline or explicitly requesting Piper, synthesize locally immediately without network lag
    if is_piper_requested:
        piper_path = get_piper_model_path()
        if piper_path and (not is_hindi or not shutil.which("espeak-ng")):
            try:
                from piper import PiperVoice
                p_str = str(piper_path)
                if p_str not in _PIPER_VOICE_CACHE:
                    _PIPER_VOICE_CACHE[p_str] = PiperVoice.load(p_str)
                p_voice = _PIPER_VOICE_CACHE[p_str]
                with wave.open(output_path, "wb") as wf:
                    p_voice.synthesize_wav(clean, wf)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                    return output_path
            except Exception as e:
                logger.warning(f"Piper offline synthesis failed: {e}")

        # Local fallback: espeak-ng / espeak for Hindi offline or if Piper fails
        bin_name = "espeak-ng" if shutil.which("espeak-ng") else ("espeak" if shutil.which("espeak") else None)
        if bin_name:
            cmd = [bin_name, "-v", "hi" if is_hindi else "en", "-s", "140", "-w", output_path, clean]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                return output_path

    # 2. Try Edge-TTS Neural when online (Studio quality, zero API key)
    if online:
        try:
            import edge_tts
            import asyncio

            async def _synth():
                communicate = edge_tts.Communicate(clean, voice)
                await communicate.save(output_path)

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        pool.submit(asyncio.run, _synth()).result(timeout=4)
                else:
                    loop.run_until_complete(_synth())
            except RuntimeError:
                asyncio.run(_synth())

            if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                return output_path
        except Exception as e:
            logger.warning(f"Edge-TTS synthesis failed: {e}")

    # 3. Try Sarvam if Hindi and API key available
    sarvam_key = get_secret("SARVAM_API_KEY")
    if is_hindi and sarvam_key and online:
        try:
            import base64
            from sarvamai import SarvamAI
            client = SarvamAI(api_subscription_key=sarvam_key)
            res = client.text_to_speech.convert(
                text=clean,
                language_code="hi-IN",
                speaker="shubh",
                model="bulbul:v2"
            )
            if res.audios:
                raw_wav = base64.b64decode(res.audios[0])
                Path(output_path).write_bytes(raw_wav)
                return output_path
        except Exception as e:
            logger.warning(f"Sarvam TTS failed: {e}")

    # 4. Try local Piper if not already attempted
    piper_path = get_piper_model_path()
    if piper_path and not is_hindi:
        try:
            from piper import PiperVoice
            p_str = str(piper_path)
            if p_str not in _PIPER_VOICE_CACHE:
                _PIPER_VOICE_CACHE[p_str] = PiperVoice.load(p_str)
            p_voice = _PIPER_VOICE_CACHE[p_str]
            with wave.open(output_path, "wb") as wf:
                p_voice.synthesize_wav(clean, wf)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                return output_path
        except Exception as e:
            logger.warning(f"Piper fallback failed: {e}")

    # 5. Try gTTS (Google TTS) if online
    if online:
        try:
            from gtts import gTTS
            tts = gTTS(text=clean, lang="hi" if is_hindi else "en")
            tts.save(output_path)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                return output_path
        except Exception as e:
            logger.warning(f"gTTS failed: {e}")

    # 6. Last resort: espeak-ng / espeak to WAV
    bin_name = "espeak-ng" if shutil.which("espeak-ng") else ("espeak" if shutil.which("espeak") else None)
    if bin_name:
        cmd = [bin_name, "-v", "hi" if is_hindi else "en", "-s", "140", "-w", output_path, clean]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        return output_path

    raise RuntimeError("No working TTS synthesis engine available.")

    raise RuntimeError("No working TTS synthesis engine available.")


class TextToSpeech:
    def __init__(self, engine: str = "auto", piper_model_path: Optional[str] = None):
        self.engine = engine.lower()
        if not piper_model_path:
            # Check default path
            cand = Path.home() / "blockbrainagent" / "models" / "piper" / "en_US-lessac-medium.onnx"
            if cand.exists():
                self.piper_model_path = str(cand)
            else:
                self.piper_model_path = ""
        else:
            self.piper_model_path = piper_model_path

    def speak(self, text: str, lang: str = "", voice: str = "") -> Dict[str, Any]:
        """Convert text to speech and play aloud."""
        clean = clean_text_for_speech(text)
        if not clean:
            return {"success": False, "error": "Empty text after cleaning."}

        resolved_lang = detect_language(clean) if (not lang or lang == "auto") else lang
        is_hindi = "hi" in resolved_lang.lower()

        # 1. If user explicitly requested piper and English:
        if (self.engine == "piper" or voice == "piper") and not is_hindi and self.piper_model_path and os.path.exists(self.piper_model_path):
            try:
                return self._speak_piper(clean)
            except Exception as e:
                logger.warning(f"Piper TTS failed ({e}), falling back to neural.")

        # 2. Try Sarvam TTS if requested or if Hindi text and Sarvam API key available
        sarvam_key = get_secret("SARVAM_API_KEY")
        if self.engine == "sarvam" and sarvam_key:
            try:
                return self._speak_sarvam(clean, sarvam_key, lang="hi-IN" if is_hindi else "en-IN")
            except Exception as e:
                logger.warning(f"Sarvam TTS failed ({e}), falling back to neural.")

        # 3. Primary high-definition neural playback (Edge-TTS)
        try:
            target_voice = voice if voice else ("hi-IN-MadhurNeural" if is_hindi else "en-US-GuyNeural")
            temp_mp3 = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False).name
            synthesize_speech_file(clean, output_path=temp_mp3, lang=resolved_lang, voice=target_voice)
            _play_audio(temp_mp3)
            try:
                os.remove(temp_mp3)
            except Exception:
                pass
            return {"success": True, "engine": "edge-neural", "lang": resolved_lang, "voice": target_voice, "spoken": clean[:80]}
        except Exception as e:
            logger.warning(f"Neural speech playback failed: {e}")

        # 4. Fallback to Piper for English if available
        if not is_hindi and self.piper_model_path and os.path.exists(self.piper_model_path):
            try:
                return self._speak_piper(clean)
            except Exception:
                pass

        # 5. Fallback to espeak-ng / espeak
        return self._speak_espeak(clean, lang="hi" if is_hindi else "en")

    def _speak_piper(self, text: str) -> Dict[str, Any]:
        from piper import PiperVoice
        global _PIPER_VOICE_CACHE
        if self.piper_model_path not in _PIPER_VOICE_CACHE:
            _PIPER_VOICE_CACHE[self.piper_model_path] = PiperVoice.load(self.piper_model_path)
        voice = _PIPER_VOICE_CACHE[self.piper_model_path]

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            wav_path = tf.name

        try:
            with wave.open(wav_path, "wb") as wf:
                voice.synthesize_wav(text, wf)
            _play_wav(wav_path)
            return {"success": True, "engine": "piper", "spoken": text[:80]}
        finally:
            try:
                os.remove(wav_path)
            except Exception:
                pass

    def _speak_espeak(self, text: str, lang: str = "en") -> Dict[str, Any]:
        global _ACTIVE_PLAYBACK_PROC
        stop_speaking()

        binary = "espeak-ng" if shutil.which("espeak-ng") else ("espeak" if shutil.which("espeak") else None)
        if not binary:
            return {"success": False, "error": "No TTS engine found (espeak-ng or piper required)."}

        # Tuned speed: 140 for Hindi, 160 for English with clean inflection
        speed = "140" if lang == "hi" else "160"
        cmd = [binary, "-v", lang, "-s", speed, text]
        _ACTIVE_PLAYBACK_PROC = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        _ACTIVE_PLAYBACK_PROC.wait(timeout=180)
        return {"success": True, "engine": binary, "spoken": text[:80]}

    def _speak_sarvam(self, text: str, api_key: str, lang: str = "hi-IN") -> Dict[str, Any]:
        import base64
        from sarvamai import SarvamAI
        client = SarvamAI(api_subscription_key=api_key)

        res = client.text_to_speech.convert(
            text=text,
            language_code=lang,
            speaker="shubh" if "hi" in lang else "amelia_en_conversational",
            model="bulbul:v2"
        )
        if not res.audios:
            raise RuntimeError("Sarvam TTS returned no audio frames.")

        raw_wav = base64.b64decode(res.audios[0])
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            tf.write(raw_wav)
            wav_path = tf.name

        try:
            _play_wav(wav_path)
            return {"success": True, "engine": "sarvam", "spoken": text[:80]}
        finally:
            try:
                os.remove(wav_path)
            except Exception:
                pass


