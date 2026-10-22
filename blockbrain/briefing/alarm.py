"""Escalating multi-stage alarm for blockbrain AI.
Stage 1: Loud alarm + local spoken message on laptop.
Stage 2: High-priority push to phone via Telegram/ntfy.
Stage 3: Phone call via Twilio reading briefing aloud, repeating until acknowledged.
"""

from datetime import datetime
import threading
import time
from typing import Optional

from blockbrain.config import load_config
from blockbrain.voice.tts import TextToSpeech
from blockbrain.channels.push import send_push
from blockbrain.channels.phone import PhoneChannel
from blockbrain.briefing.generator import generate_morning_briefing


class StagedAlarm:
    def __init__(self):
        self.cfg = load_config()
        self.tts = TextToSpeech()
        self.phone = PhoneChannel()
        self.acknowledged = False

    def trigger_alarm(self, stop_event: Optional[threading.Event] = None):
        """Execute the escalating alarm workflow."""
        self.acknowledged = False
        brief_cfg = self.cfg.get("briefing", {})
        delay_sec = int(brief_cfg.get("escalation_delay_seconds", 120))

        spoken_briefing, md_briefing = generate_morning_briefing()

        print("\n" + "🔔" * 25)
        print("⏰ STAGE 1: LOCAL LOUD ALARM & SPOKEN BRIEFING")
        print("🔔" * 25)

        # Stage 1: Local loud sound & spoken announcement
        self.tts.speak("Alarm! Good morning! It is time to wake up.")
        self.tts.speak(spoken_briefing)

        # Check for immediate acknowledgment
        if self._check_ack(timeout=15, stop_event=stop_event):
            print("✅ Alarm acknowledged at Stage 1.")
            return

        # Stage 2: High-priority push to phone
        print("\n📲 STAGE 2: HIGH-PRIORITY PHONE PUSH NOTIFICATION")
        send_push(
            title="⏰ WAKE UP ALARM",
            message=f"Good morning! Your alarm is ringing.\n\n{md_briefing[:250]}...",
            priority="urgent"
        )

        if self._check_ack(timeout=delay_sec, stop_event=stop_event):
            print("✅ Alarm acknowledged at Stage 2.")
            return

        # Stage 3: Phone call via Twilio (with repeat until acknowledged)
        print("\n📞 STAGE 3: ESCALATING PHONE CALL READOUT")
        call_count = 0
        while not self.acknowledged:
            if stop_event and stop_event.is_set():
                break

            call_count += 1
            print(f"👉 Initiating Stage 3 phone call attempt #{call_count}...")
            call_msg = f"Good morning! This is blockbrain AI waking you up. {spoken_briefing}"
            res = self.phone.make_call(call_msg)

            if self._check_ack(timeout=delay_sec, stop_event=stop_event):
                print(f"✅ Alarm acknowledged after Stage 3 call #{call_count}.")
                break

    def _check_ack(self, timeout: int, stop_event: Optional[threading.Event] = None) -> bool:
        """Check for user acknowledgement within timeout window."""
        start = time.time()
        while time.time() - start < timeout:
            if stop_event and stop_event.is_set():
                self.acknowledged = True
                return True
            time.sleep(0.5)
        return self.acknowledged

    def acknowledge(self):
        """Acknowledge and silence the alarm."""
        self.acknowledged = True

