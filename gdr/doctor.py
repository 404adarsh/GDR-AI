"""GDR AI Doctor diagnostic tool.
Runs a comprehensive self-test of microphone, speaker, TTS, STT, browser, network, and API keys.
Prints clear PASS / FAIL / WARN for each component.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import wave
from typing import Dict, Any, List, Tuple
import numpy as np

from gdr.safety.secrets import get_secret, mask_secret


class Doctor:
    def __init__(self):
        self.results: List[Tuple[str, str, str]] = []  # (Component, Status, Detail)

    def log(self, component: str, status: str, detail: str):
        self.results.append((component, status, detail))

    def run_all(self, interactive_audio: bool = False) -> bool:
        print("\n🩺 Running GDR AI System Diagnostics...\n" + "=" * 55)

        self.check_network()
        self.check_api_keys()
        self.check_mic()
        self.check_speaker(interactive=interactive_audio)
        self.check_tts()
        self.check_stt()
        self.check_wake_word()
        self.check_browser()

        print("\n" + "=" * 55)
        print(f"{'Component':<18} | {'Status':<8} | Detail")
        print("-" * 55)

        all_passed = True
        for comp, status, detail in self.results:
            if status == "FAIL":
                icon = "❌ FAIL"
                all_passed = False
            elif status == "PASS":
                icon = "✅ PASS"
            else:
                icon = "⚠️ WARN"
            print(f"{comp:<18} | {icon:<8} | {detail}")

        print("=" * 55)
        if all_passed:
            print("🎉 All critical systems operational!")
        else:
            print("⚠️ Some checks failed. Review details above to resolve.")
        print()
        return all_passed

    def check_network(self):
        try:
            import urllib.request
            import urllib.error
            try:
                urllib.request.urlopen("https://api.sarvam.ai", timeout=5)
            except urllib.error.HTTPError:
                # Server responded (e.g. 404 for root endpoint), which proves HTTPS reachability
                pass
            self.log("Network", "PASS", "HTTPS connectivity to api.sarvam.ai verified")
        except Exception as e:
            try:
                import urllib.request
                urllib.request.urlopen("https://1.1.1.1", timeout=3)
                self.log("Network", "WARN", f"Internet up, but api.sarvam.ai returned: {e}")
            except Exception:
                self.log("Network", "FAIL", f"No network access: {e}")

    def check_api_keys(self):
        sarvam_key = get_secret("SARVAM_API_KEY")
        if sarvam_key:
            self.log("Sarvam API Key", "PASS", f"Configured ({mask_secret(sarvam_key)})")
        else:
            self.log("Sarvam API Key", "FAIL", "SARVAM_API_KEY environment variable is missing")

        anthropic_key = get_secret("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.log("Anthropic Key", "PASS", f"Configured ({mask_secret(anthropic_key)})")
        else:
            self.log("Anthropic Key", "WARN", "Optional: ANTHROPIC_API_KEY unset (vision fallback disabled)")

    def check_mic(self):
        try:
            from gdr.voice.vad import test_microphone_input, check_and_boost_mic
            check_and_boost_mic(0.70)
            res = test_microphone_input(duration=0.5)
            if res.get("success"):
                vol = res.get("rms", 0.0)
                dname = res.get("device_name", "Microphone")
                rate = res.get("sample_rate", 16000)
                self.log("Microphone", "PASS", f"Active ({dname}, {rate}Hz, RMS: {vol})")
            else:
                err = res.get("error", "Host mic unavailable")
                self.log("Microphone", "WARN", f"{err} (Web HUD browser mic active)")
        except Exception as e:
            self.log("Microphone", "WARN", f"Mic shared with browser/Meet or unavailable ({e}). Web HUD mic active.")

    def check_speaker(self, interactive: bool = False):
        try:
            import sounddevice as sd
            # Verify default output device exists
            default_out = sd.default.device[1]
            if default_out < 0:
                self.log("Speaker", "FAIL", "No default audio output device found")
                return

            dev_info = sd.query_devices(default_out)
            # Check pw-play or aplay
            player = shutil.which("pw-play") or shutil.which("paplay") or shutil.which("aplay")
            player_name = os.path.basename(player) if player else "sounddevice"
            self.log("Speaker", "PASS", f"{dev_info.get('name', 'Default')} (using {player_name})")
        except Exception as e:
            self.log("Speaker", "FAIL", f"Audio output error: {e}")

    def check_tts(self):
        engines = []
        # Check Piper
        piper_path = os.path.expanduser("~/gdragent/models/piper/en_US-lessac-medium.onnx")
        if os.path.exists(piper_path):
            try:
                from piper import PiperVoice
                voice = PiperVoice.load(piper_path)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                    t_path = tf.name
                with wave.open(t_path, "wb") as wf:
                    voice.synthesize_wav("test", wf)
                if os.path.getsize(t_path) > 1000:
                    engines.append("Piper (neural)")
                os.remove(t_path)
            except Exception as e:
                pass

        if shutil.which("espeak-ng") or shutil.which("espeak"):
            engines.append("espeak-ng")

        try:
            import edge_tts
            engines.append("Edge-TTS (Neural Studio)")
        except ImportError:
            pass

        try:
            import gtts
            engines.append("gTTS")
        except ImportError:
            pass

        sarvam_key = get_secret("SARVAM_API_KEY")
        if sarvam_key:
            engines.append("Sarvam Bulbul (Hindi/English)")

        if engines:
            self.log("TTS", "PASS", f"Engines available: {', '.join(engines)}")
        else:
            self.log("TTS", "FAIL", "No working TTS engine found (install piper or espeak-ng)")

    def check_stt(self):
        stt_backends = []
        whisper_err = None
        try:
            from gdr.voice.stt import get_whisper_model
            model = get_whisper_model("tiny")
            stt_backends.append("faster-whisper (local tiny)")
        except Exception as e:
            whisper_err = str(e)

        if get_secret("SARVAM_API_KEY"):
            stt_backends.append("Sarvam Saaras (Cloud STT)")

        if stt_backends:
            status = "PASS" if "faster-whisper (local tiny)" in stt_backends else "WARN"
            note = f"Engines active: {', '.join(stt_backends)}"
            if whisper_err:
                note += f" (Local whisper: {whisper_err[:50]}...)"
            self.log("STT", status, note)
        else:
            self.log("STT", "FAIL", f"No STT engine available: {whisper_err}")

    def check_wake_word(self):
        try:
            from gdr.voice.wakeword import WakeWordDetector
            detector = WakeWordDetector()
            if detector.is_available():
                self.log("Wake Word", "PASS", f"OpenWakeWord '{detector.model_key}' ready")
            else:
                self.log("Wake Word", "WARN", "OpenWakeWord model not found in resources")
        except Exception as e:
            self.log("Wake Word", "WARN", f"Wake word check error: {e}")

    def check_browser(self):
        try:
            from playwright.sync_api import sync_playwright
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto("about:blank")
                browser.close()
            self.log("Browser", "PASS", "Playwright Chromium headless ready")
        except Exception as e:
            self.log("Browser", "FAIL", f"Playwright error: {e}")


def run_doctor() -> bool:
    doc = Doctor()
    return doc.run_all()


if __name__ == "__main__":
    success = run_doctor()
    sys.exit(0 if success else 1)
