"""Phone call channel for blockbrain AI with Twilio integration and mock fallback.
Used for stage-3 alarm escalation and spoken morning briefing delivery.
"""

from datetime import datetime
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import requests

from blockbrain.safety.secrets import get_secret
from blockbrain.safety.limits import record_cost

MOCK_CALL_LOG = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain")) / "calls.log"


class PhoneChannel:
    def __init__(self):
        self.account_sid = get_secret("TWILIO_ACCOUNT_SID")
        self.auth_token = get_secret("TWILIO_AUTH_TOKEN")
        self.from_number = get_secret("TWILIO_FROM_NUMBER")
        self.to_number = get_secret("USER_PHONE_NUMBER")

    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token and self.from_number and self.to_number)

    def make_call(self, message: str) -> Dict[str, Any]:
        """Initiate phone call to user reading the message aloud."""
        if self.is_configured():
            try:
                # Twilio REST API
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Calls.json"
                twiml = f"<Response><Say voice='Polly.Aditi'>{message}</Say></Response>"
                resp = requests.post(
                    url,
                    auth=(self.account_sid, self.auth_token),
                    data={
                        "To": self.to_number,
                        "From": self.from_number,
                        "Twiml": twiml
                    },
                    timeout=10
                )
                if resp.status_code in (200, 201):
                    record_cost("twilio-call-minute", 0.015)
                    return {"success": True, "provider": "twilio", "sid": resp.json().get("sid")}
                else:
                    return {"success": False, "error": f"Twilio HTTP {resp.status_code}: {resp.text}"}
            except Exception as e:
                return {"success": False, "error": f"Twilio call failed: {e}"}

        # Mock / Simulation mode when keys are not configured
        call_record = {
            "timestamp": datetime.now().isoformat(),
            "to": self.to_number or "<USER_PHONE_NUMBER unset>",
            "message": message[:300],
            "mode": "SIMULATION (Twilio credentials not configured)",
        }
        try:
            MOCK_CALL_LOG.parent.mkdir(parents=True, exist_ok=True)
            with open(MOCK_CALL_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(call_record) + "\n")
        except Exception:
            pass

        print(f"\n📞 [MOCK PHONE CALL] Dialing {self.to_number or 'User'}...")
        print(f"   Spoken audio payload: \"{message[:120]}...\"")
        return {"success": True, "provider": "mock", "record": call_record}

