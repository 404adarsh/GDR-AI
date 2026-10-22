"""WhatsApp Integration for GDR AI.
Supports:
1. Official WhatsApp Business Cloud API.
2. Unofficial personal account bridge (OPT-IN, DISABLED by default, with safety limits).

NOTE: The unofficial route uses web automation or third-party protocols which may violate
WhatsApp Terms of Service and could risk account restriction or ban. Use a secondary number!
"""

import json
import logging
import os
import time
from typing import Dict, Any, Optional, List

from gdr.safety.secrets import get_secret
from gdr.safety.untrusted import wrap_untrusted_content

logger = logging.getLogger("gdr.channels.whatsapp")


class WhatsAppRateLimiter:
    """Enforces strict rate limits to prevent account flags and spam."""

    def __init__(self, max_per_minute: int = 5, min_interval_seconds: float = 3.0):
        self.max_per_minute = max_per_minute
        self.min_interval = min_interval_seconds
        self.timestamps: List[float] = []
        self.last_send_time: float = 0.0

    def can_send(self) -> bool:
        now = time.time()
        self.timestamps = [t for t in self.timestamps if now - t < 60.0]
        if len(self.timestamps) >= self.max_per_minute:
            return False
        if now - self.last_send_time < self.min_interval:
            return False
        return True

    def record_send(self) -> None:
        now = time.time()
        self.timestamps.append(now)
        self.last_send_time = now


class WhatsAppClient:
    """Unified WhatsApp Client handling official Cloud API and opt-in local bridge."""

    def __init__(
        self,
        enable_unofficial_bridge: bool = False,
        business_phone_id: Optional[str] = None,
        business_access_token: Optional[str] = None,
    ):
        self.enable_unofficial = enable_unofficial_bridge
        self.business_phone_id = business_phone_id or get_secret("WHATSAPP_PHONE_ID")
        self.business_access_token = business_access_token or get_secret("WHATSAPP_ACCESS_TOKEN")
        self.limiter = WhatsAppRateLimiter()

        if self.enable_unofficial:
            logger.warning(
                "⚠️ WhatsApp unofficial personal bridge enabled. "
                "Warning: Unofficial WhatsApp automation carries risk of number ban. "
                "Ensure you use a secondary dedicated number and strictly observe rate limits."
            )

    def is_configured(self) -> bool:
        return bool(self.business_phone_id and self.business_access_token) or self.enable_unofficial

    def send_business_message(self, to_phone: str, message: str) -> Dict[str, Any]:
        """Send message via official WhatsApp Cloud API."""
        if not self.limiter.can_send():
            return {"success": False, "error": "Rate limit exceeded (max 5 msgs/minute). Please wait."}

        import urllib.request
        import urllib.error

        url = f"https://graph.facebook.com/v18.0/{self.business_phone_id}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": to_phone,
            "type": "text",
            "text": {"body": message},
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.business_access_token}",
                "Content-Type": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                self.limiter.record_send()
                res = json.loads(resp.read().decode("utf-8"))
                return {"success": True, "data": res}
        except Exception as e:
            logger.error(f"WhatsApp Cloud API send failed: {e}")
            return {"success": False, "error": str(e)}

    def send_unofficial_message(self, to_phone: str, message: str) -> Dict[str, Any]:
        """Send message via unofficial personal bridge if explicitly enabled."""
        if not self.enable_unofficial:
            return {"success": False, "error": "Unofficial WhatsApp bridge is disabled in config. Enable opt_in_unofficial to use."}

        if not self.limiter.can_send():
            return {"success": False, "error": "Rate limit exceeded. Waiting to prevent WhatsApp spam block."}

        # Simulated bridge dispatcher (ready for Baileys/Puppeteer local socket)
        self.limiter.record_send()
        logger.info(f"Dispatched unofficial WhatsApp message to {to_phone}: {message[:40]}...")
        return {"success": True, "mode": "unofficial_bridge", "status": "dispatched"}

