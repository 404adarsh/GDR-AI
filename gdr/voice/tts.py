"""Text-to-Speech (TTS) engine for GDR AI.
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

from gdr.safety.secrets import get_secret
from gdr.voice.processor import SpeechTextProcessor, clean_text_for_speech as _clean_proc
from gdr.voice.config import get_voice_manager, VoiceConfig, SUPPORTED_VOICE_CATALOG

logger = logging.getLogger("gdr.voice.tts")

_PIPER_VOICE_CACHE = {}
_ACTIVE_PLAYBACK_PROC = None

# Studio-grade Neural Voice Registry with Female Voice Defaults for Aarushi
VOICE_PROFILES = {
    "sarvam_bulbul": {
        "engine": "sarvam",
        "voice": "anushka",
        "lang": "hi-IN",
        "label": "Sarvam (Anushka Neural - Bulbul v2)",
        "description": "Natural Indian regional voice from Sarvam AI for Hindi and Indian English."
    },
    "hi_swara": {
        "engine": "edge",
        "voice": "hi-IN-SwaraNeural",
        "lang": "hi-IN",
        "label": "Hindi (Swara Neural - स्वरा)",
        "description": "Studio-grade expressive Hindi female voice, perfectly fluent and warm for Hindi & Hinglish."
    },
    "hi_female": {
        "engine": "edge",
        "voice": "hi-IN-SwaraNeural",
        "lang": "hi-IN",
        "label": "Hindi (Swara Neural - स्वरा)",
        "description": "Studio-grade natural Hindi female voice, expressive and fluent."
    },
    "hi_male": {
        "engine": "edge",
        "voice": "hi-IN-MadhurNeural",
        "lang": "hi-IN",
        "label": "Hindi (Madhur Neural - मधुर)",
        "description": "Studio-grade natural Hindi voice."
    },
    "en_aria": {
        "engine": "edge",
        "voice": "en-US-AriaNeural",
        "lang": "en-US",
        "label": "English (Aria Neural - Expressive & Flirty)",
        "description": "Warm, charming, expressive, and flirty American female voice."
    },
    "en_female": {
        "engine": "edge",
        "voice": "en-US-JennyNeural",
        "lang": "en-US",
        "label": "English (Jenny Neural - Sweet Studio)",
        "description": "Sweet, natural, pleasant American English female voice."
    },
    "en_jenny": {
        "engine": "edge",
        "voice": "en-US-JennyNeural",
        "lang": "en-US",
        "label": "English (Jenny Neural - Sweet Studio)",
        "description": "Sweet, natural, pleasant American English female voice."
    },
    "en_male": {
        "engine": "edge",
        "voice": "en-US-GuyNeural",
        "lang": "en-US",
        "label": "English (Guy Neural - Male HD)",
        "description": "Articulate American English voice."
    },
    "en_christopher": {
        "engine": "edge",
        "voice": "en-US-ChristopherNeural",
        "lang": "en-US",
        "label": "English (Christopher Neural)",
        "description": "Executive English voice."
    },
    "en_ryan": {
        "engine": "edge",
        "voice": "en-GB-RyanNeural",
        "lang": "en-GB",
        "label": "British English (Ryan Neural)",
        "description": "British English voice."
    },
    "en_sonia": {
        "engine": "edge",
        "voice": "en-GB-SoniaNeural",
        "lang": "en-GB",
        "label": "British English (Sonia Neural - Refined Female)",
        "description": "Refined, gentle British English female voice."
    },
    "en_indian": {
        "engine": "edge",
        "voice": "en-IN-NeerjaNeural",
        "lang": "en-IN",
        "label": "Indian English (Neerja Neural - Warm Female)",
        "description": "Fluent, warm, melodious Indian English female voice with natural pacing."
    },
    "en_neerja": {
        "engine": "edge",
        "voice": "en-IN-NeerjaNeural",
        "lang": "en-IN",
        "label": "Indian English (Neerja Neural - Warm Female)",
        "description": "Fluent, warm, melodious Indian English female voice with natural pacing."
    },
    "elevenlabs": {
        "engine": "elevenlabs",
        "voice": "elevenlabs_custom",
        "lang": "multilingual",
        "label": "ElevenLabs (Custom AI Female Voice)",
        "description": "Ultra-realistic emotional AI female voice using ElevenLabs Multilingual v2."
    },
    "piper_offline": {
        "engine": "piper",
        "voice": "en_US-lessac-medium",
        "lang": "en-US",
        "label": "Piper Offline Female (0-Token CPU)",
        "description": "100% offline neural voice running on CPU without internet."
    }
}


def clean_text_for_speech(text: str) -> str:
    """Strip markdown, URLs, code blocks, emojis, model tags, and code punctuation for speech."""
    t = str(text or "")

    # 1. Strip bracketed model prefixes and system tags (prevents TTS pronouncing model names/brackets)
    t = re.sub(r"\[(?:Offline Local AI Mode|GDR Fast Lane|GDR Heavy MoE Lane|Local System AI|vol|FACT|PREFERENCE|PERSONA|STYLE|Query Ingestion|Policy Verification|Agent Response)[^\]]*\]", " ", t, flags=re.I)
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

    # If it is MP3 and player requires WAV (like aplay or paplay), convert cleanly
    play_path = file_path
    temp_wav = None
    if file_path.lower().endswith(".mp3") and not shutil.which("pw-play"):
        if shutil.which("ffmpeg"):
            try:
                fd, temp_wav = tempfile.mkstemp(suffix=".wav", prefix="gdr_play_")
                os.close(fd)
                subprocess.run(
                    ["ffmpeg", "-y", "-i", file_path, "-ar", "24000", "-ac", "1", temp_wav],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=5
                )
                if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 100:
                    play_path = temp_wav
            except Exception:
                pass

        if play_path == file_path:
            try:
                import soundfile as sf
                data, samplerate = sf.read(file_path)
                fd, temp_wav = tempfile.mkstemp(suffix=".wav", prefix="gdr_play_")
                os.close(fd)
                sf.write(temp_wav, data, samplerate)
                play_path = temp_wav
            except Exception as e:
                logger.debug(f"Soundfile conversion note: {e}")

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
        Path.home() / "gdragent" / "models" / "piper" / "en_US-lessac-medium.onnx",
        Path(__file__).resolve().parent.parent.parent / "models" / "piper" / "en_US-lessac-medium.onnx",
        Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr")) / "models" / "piper" / "en_US-lessac-medium.onnx",
    ]
    for c in candidates:
        if c.exists() and c.stat().st_size > 1000000:
            return c
    return None


def play_chime():
    """Play a pleasant cool audio chime for Aarushi's proactive check-in."""
    try:
        from gdr.core.proactive import generate_chime_wav
        wav_path = generate_chime_wav()
        _play_audio(wav_path)
        try:
            os.remove(wav_path)
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"Failed to play chime: {e}")


def extract_elevenlabs_voice_id(val: Optional[str]) -> str:
    """Extract 20-character ElevenLabs Voice ID from raw ID or ElevenLabs voice URLs.

    Supports:
    - Raw ID: 'RDWdsTU6N02BFftbIEAp'
    - Voice URLs: 'https://elevenlabs.io/voices/RDWdsTU6N02BFftbIEAp'
    - Voice library URLs: 'https://elevenlabs.io/app/voice-library/share/.../RDWdsTU6N02BFftbIEAp'
    - API URLs: 'https://api.elevenlabs.io/v1/voices/RDWdsTU6N02BFftbIEAp'
    """
    if not val:
        return "RDWdsTU6N02BFftbIEAp"
    s = str(val).strip().strip("\"'<>")
    if not s:
        return "RDWdsTU6N02BFftbIEAp"

    clean_s = s.split("?")[0].split("#")[0].rstrip("/")
    segments = [p for p in clean_s.split("/") if p]
    if segments:
        last = segments[-1]
        if re.match(r"^[a-zA-Z0-9_-]{15,50}$", last):
            return last

    matches = re.findall(r"\b([a-zA-Z0-9]{18,35})\b", s)
    if matches:
        return matches[-1]
    return s


_LAST_ELEVENLABS_ERROR: Optional[str] = None


def get_last_elevenlabs_error() -> Optional[str]:
    """Return the most recent error message from ElevenLabs API call, if any."""
    return _LAST_ELEVENLABS_ERROR


def synthesize_elevenlabs(
    text: str,
    output_path: str,
    voice_id: Optional[str] = None,
    api_key: Optional[str] = None
) -> Optional[str]:
    """Synthesize speech using ElevenLabs API with high expressive emotional tone."""
    global _LAST_ELEVENLABS_ERROR
    _LAST_ELEVENLABS_ERROR = None

    key = api_key or get_secret("ELEVENLABS_API_KEY")
    if not key:
        _LAST_ELEVENLABS_ERROR = "ELEVENLABS_API_KEY is not configured."
        return None

    raw_vid = voice_id or "RDWdsTU6N02BFftbIEAp"
    vid = extract_elevenlabs_voice_id(raw_vid)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}"
    headers = {
        "xi-api-key": key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.40,
            "similarity_boost": 0.85,
            "style": 0.35,
            "use_speaker_boost": True
        }
    }
    try:
        import requests
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code == 200 and len(resp.content) > 500:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            return output_path
        else:
            err_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
            try:
                d = resp.json()
                err_msg = d.get("detail", {}).get("message", err_msg)
            except Exception:
                pass
            _LAST_ELEVENLABS_ERROR = err_msg
            logger.warning(f"ElevenLabs TTS failed: {err_msg}")
    except Exception as e:
        _LAST_ELEVENLABS_ERROR = str(e)
        logger.warning(f"ElevenLabs request error: {e}")
    return None


def get_elevenlabs_voices_list(api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch available voices from ElevenLabs account."""
    key = api_key or get_secret("ELEVENLABS_API_KEY")
    if not key:
        return []
    import requests
    try:
        resp = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            voices = []
            for v in data.get("voices", []):
                labels = v.get("labels", {})
                gender = labels.get("gender", "")
                voices.append({
                    "voice_id": v.get("voice_id"),
                    "name": v.get("name"),
                    "category": v.get("category", ""),
                    "gender": gender,
                    "description": labels.get("description", v.get("description", "")),
                    "preview_url": v.get("preview_url")
                })
            return voices
    except Exception as e:
        logger.warning(f"Failed to fetch ElevenLabs voices: {e}")
    return []


def synthesize_speech_file(
    text: str,
    output_path: Optional[str] = None,
    lang: str = "auto",
    voice: Optional[str] = None,
    target_format: str = "mp3",
    response_id: Optional[str] = None
) -> str:
    """Synthesize speech into a high-quality audio file (MP3 or WAV).
    Uses the authoritative VoiceManager snapshot for strict voice consistency.
    Supports Edge-TTS, Sarvam Bulbul, ElevenLabs, and offline Piper CPU neural.
    """
    global _PIPER_VOICE_CACHE
    clean = clean_text_for_speech(text)
    if not clean:
        raise ValueError("Empty text after cleaning")

    resolved_lang = detect_language(clean) if (not lang or lang == "auto") else lang
    is_hindi = "hi" in resolved_lang.lower()

    # Look up authoritative snapshot
    mgr = get_voice_manager()
    snapshot = mgr.get_snapshot(response_id) if response_id else mgr.get_active_config()

    # Resolve target voice and provider
    target_provider = snapshot.provider
    chosen_voice = voice or snapshot.voice_id

    alias_map = {
        "hi_swara": "hi-IN-SwaraNeural",
        "hi_female": "hi-IN-SwaraNeural",
        "hi_male": "hi-IN-MadhurNeural",
        "en_jenny": "en-US-JennyNeural",
        "en_female": "en-US-JennyNeural",
        "en_aria": "en-US-AriaNeural",
        "en_sonia": "en-GB-SoniaNeural",
        "en_ryan": "en-GB-RyanNeural",
        "en_neerja": "en-IN-NeerjaNeural",
        "en_indian": "en-IN-NeerjaNeural",
        "en_male": "en-US-GuyNeural",
        "elevenlabs": "elevenlabs_custom",
        "sarvam": "anushka",
        "sarvam_bulbul": "anushka",
        "piper": "en_US-lessac-medium",
        "piper_offline": "en_US-lessac-medium",
    }

    if chosen_voice in alias_map:
        chosen_voice = alias_map[chosen_voice]
    elif chosen_voice in VOICE_PROFILES:
        chosen_voice = VOICE_PROFILES[chosen_voice]["voice"]
    elif not chosen_voice or chosen_voice in ("auto", "neural_auto", "default", "aarushi"):
        chosen_voice = "hi-IN-SwaraNeural" if is_hindi else "en-US-AriaNeural"

    # Determine explicit provider preference
    if "piper" in chosen_voice.lower():
        target_provider = "piper"
    elif "eleven" in chosen_voice.lower():
        target_provider = "elevenlabs"
    elif chosen_voice in ("anushka", "priya", "bulbul"):
        target_provider = "sarvam"

    if not output_path:
        suffix = f".{target_format.lower()}"
        fd, output_path = tempfile.mkstemp(suffix=suffix, prefix="gdr_tts_")
        os.close(fd)

    from gdr.core.network import is_online
    online = is_online()

    # Primary Provider 1: ElevenLabs
    if target_provider == "elevenlabs" and online:
        from gdr.config import load_config
        cfg = load_config()
        voice_cfg = cfg.get("voice", {})
        eleven_key = get_secret("ELEVENLABS_API_KEY") or voice_cfg.get("elevenlabs_api_key", "")
        eleven_voice_id = voice_cfg.get("elevenlabs_voice_id", "RDWdsTU6N02BFftbIEAp")
        if chosen_voice and chosen_voice not in ("elevenlabs", "elevenlabs_custom"):
            eleven_voice_id = extract_elevenlabs_voice_id(chosen_voice)
        if eleven_key and len(eleven_key) > 20 and not eleven_key.startswith("your_"):
            try:
                res = synthesize_elevenlabs(clean, output_path, voice_id=eleven_voice_id, api_key=eleven_key)
                if res and os.path.exists(res) and os.path.getsize(res) > 500:
                    return res
            except Exception as e:
                logger.warning(f"ElevenLabs TTS failed: {e}")

    # Primary Provider 2: Sarvam Bulbul
    if target_provider == "sarvam" and online:
        sarvam_key = get_secret("SARVAM_API_KEY")
        if sarvam_key:
            try:
                import base64
                from sarvamai import SarvamAI
                client = SarvamAI(api_subscription_key=sarvam_key)
                lang_code = "hi-IN" if is_hindi else "en-IN"
                speaker_name = chosen_voice if chosen_voice in ("anushka", "priya", "vidya", "arya", "abhilash") else "anushka"
                res = client.text_to_speech.convert(
                    text=clean,
                    language_code=lang_code,
                    speaker=speaker_name,
                    model="bulbul:v2"
                )
                if res.audios:
                    raw_wav = base64.b64decode(res.audios[0])
                    Path(output_path).write_bytes(raw_wav)
                    return output_path
            except Exception as e:
                logger.warning(f"Sarvam Bulbul TTS failed: {e}")

    # Primary Provider 3: Piper Local Offline
    if (target_provider == "piper" or not online) and not is_hindi:
        piper_path = get_piper_model_path()
        if piper_path:
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
                logger.warning(f"Piper synthesis error: {e}")

    # Primary Provider 4: Edge-TTS Neural (Studio quality online)
    if online and target_provider in ("edge", "auto"):
        try:
            import edge_tts
            import asyncio

            async def _synth():
                communicate = edge_tts.Communicate(clean, chosen_voice)
                await communicate.save(output_path)

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        pool.submit(asyncio.run, _synth()).result(timeout=6)
                else:
                    loop.run_until_complete(_synth())
            except RuntimeError:
                asyncio.run(_synth())

            if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                return output_path
        except Exception as e:
            logger.warning(f"Edge-TTS synthesis error: {e}")

    # DETERMINISTIC FALLBACK POLICY (without overwriting user's persistent config)
    if snapshot.fallback_enabled:
        # Fallback A: Try Edge-TTS if not already tried
        if online and target_provider != "edge":
            try:
                import edge_tts
                import asyncio
                fallback_voice = "hi-IN-SwaraNeural" if is_hindi else "en-US-AriaNeural"
                async def _synth_fb():
                    communicate = edge_tts.Communicate(clean, fallback_voice)
                    await communicate.save(output_path)
                try:
                    asyncio.run(_synth_fb())
                except Exception:
                    pass
                if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                    return output_path
            except Exception:
                pass

        # Fallback B: Try Piper for English
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
            except Exception:
                pass

        # Fallback C: gTTS
        if online:
            try:
                from gtts import gTTS
                tts = gTTS(text=clean, lang="hi" if is_hindi else "en")
                tts.save(output_path)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                    return output_path
            except Exception:
                pass

        # Fallback D: espeak-ng / espeak
        bin_name = "espeak-ng" if shutil.which("espeak-ng") else ("espeak" if shutil.which("espeak") else None)
        if bin_name:
            cmd = [bin_name, "-v", "hi" if is_hindi else "en", "-s", "140", "-w", output_path, clean]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                return output_path

    raise RuntimeError("No working TTS synthesis engine available.")


class TextToSpeech:
    def __init__(self, engine: str = "auto", piper_model_path: Optional[str] = None):
        self.engine = engine.lower()
        if not piper_model_path:
            # Check default path
            cand = Path.home() / "gdragent" / "models" / "piper" / "en_US-lessac-medium.onnx"
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

        # 3. Primary high-definition neural playback (Edge-TTS or ElevenLabs)
        try:
            target_voice = voice if voice else ("hi-IN-SwaraNeural" if is_hindi else "en-US-AriaNeural")
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

        # bulbul:v2 valid female speakers: anushka, manisha, vidya, arya
        # bulbul:v2 valid male speakers: abhilash, karun, hitesh
        res = client.text_to_speech.convert(
            text=text,
            language_code=lang,
            speaker="anushka" if "hi" in lang else "anushka",
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


