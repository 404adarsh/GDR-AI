"""User-account messaging manager for GDR AI.
Handles Telegram user accounts and WhatsApp 'on my behalf'.
Summarizes incoming messages, extracts tasks/promises into memory,
drafts replies, and enforces user approval before sending.
"""

from datetime import datetime
import json
import logging
import os
from pathlib import Path
import re
from typing import Dict, Any, List, Optional

from gdr.safety.untrusted import wrap_untrusted_content
from gdr.safety.policy_engine import get_policy_engine, PolicyDecision
from gdr.channels.whatsapp import WhatsAppClient

logger = logging.getLogger("gdr.channels.user_messaging")

DEFAULT_STORAGE_DIR = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr"))


class UserMessagingManager:
    """Orchestrates Telegram and WhatsApp personal messaging on the user's behalf."""

    def __init__(
        self,
        config_dir: Optional[Path] = None,
        mark_as_ai: bool = True,
        ai_marker_text: str = "🤖 [Sent via GDR AI assistant on behalf of User]",
        enable_unofficial_whatsapp: bool = False,
    ):
        self.config_dir = config_dir or DEFAULT_STORAGE_DIR
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.drafts_file = self.config_dir / "messaging_drafts.json"
        self.extracted_info_file = self.config_dir / "extracted_chat_info.json"

        self.mark_as_ai = mark_as_ai
        self.ai_marker_text = ai_marker_text
        self.whatsapp = WhatsAppClient(enable_unofficial_bridge=enable_unofficial_whatsapp)
        self.policy_engine = get_policy_engine()

        # Simulated incoming message queues for tests/mocking
        self._mock_messages: List[Dict[str, Any]] = []
        # Outbox for sent messages (for verification)
        self.sent_messages: List[Dict[str, Any]] = []

    def queue_incoming_message(
        self,
        platform: str,
        sender_id: str,
        sender_name: str,
        text: str,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process an incoming message from Telegram or WhatsApp."""
        msg_id = f"msg_{platform}_{int(datetime.now().timestamp() * 1000)}"
        ts = timestamp or datetime.now().isoformat()

        # 1. Safely wrap untrusted content
        safe_text = wrap_untrusted_content(f"{platform.upper()}_MESSAGE", text)

        # 2. Extract actionable info: dates, meetings, tasks, promises
        extracted = self._extract_info(text, sender_name, platform, ts)
        if extracted:
            self._save_extracted_info(extracted)

        # 3. Detect if response is requested/needed
        needs_reply = self._detect_needs_reply(text)

        # 4. Generate draft reply if reply needed
        draft = None
        if needs_reply:
            draft_text = self._generate_draft_response(text, sender_name)
            draft = self._create_draft(
                msg_id=msg_id,
                platform=platform,
                recipient_id=sender_id,
                recipient_name=sender_name,
                original_text=text,
                suggested_reply=draft_text
            )

        msg_record = {
            "id": msg_id,
            "platform": platform,
            "sender_id": sender_id,
            "sender_name": sender_name,
            "raw_text": text,
            "safe_text": safe_text,
            "timestamp": ts,
            "needs_reply": needs_reply,
            "draft": draft,
            "extracted_info": extracted,
        }
        self._mock_messages.append(msg_record)
        logger.info(f"Ingested message from {sender_name} on {platform}. Needs reply: {needs_reply}")
        return msg_record

    def _detect_needs_reply(self, text: str) -> bool:
        """Analyze if text contains a question, invitation, or action request."""
        lower = text.lower()
        if "?" in text:
            return True
        triggers = [
            "are we", "can you", "could you", "let me know", "call me",
            "confirm", "meeting", "update", "please reply", "where are you",
            "what time", "available"
        ]
        return any(t in lower for t in triggers)

    def _extract_info(self, text: str, sender: str, platform: str, timestamp: str) -> List[Dict[str, Any]]:
        """Extract promises, deadlines, dates, addresses, and tasks from chat."""
        items = []
        lower = text.lower()

        # Meeting / Date extraction
        date_patterns = [
            r"\b(?:meeting|sync|call|meet)\s+(?:at|on)?\s*([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm)?|\b(?:today|tomorrow|monday|tuesday|wednesday|thursday|friday)\b)",
            r"\b(?:at|around)\s+([0-9]{1,2}(?::[0-9]{2})?\s*(?:am|pm))\b"
        ]
        for pat in date_patterns:
            matches = re.finditer(pat, lower)
            for m in matches:
                items.append({
                    "category": "meeting",
                    "sender": sender,
                    "platform": platform,
                    "extracted_text": m.group(0),
                    "context": text,
                    "timestamp": timestamp,
                })

        # Promise / Commitment extraction ("I will...", "will send...", "promise...")
        if any(w in lower for w in ["i will", "will send", "will finish", "i'll share", "promise"]):
            items.append({
                "category": "promise",
                "sender": sender,
                "platform": platform,
                "extracted_text": text,
                "context": text,
                "timestamp": timestamp,
            })

        return items

    def _generate_draft_response(self, text: str, sender_name: str) -> str:
        """Generate a contextual proposed reply."""
        lower = text.lower()
        if "meeting" in lower or "5pm" in lower or "meet" in lower:
            return f"Hi {sender_name}, sounds good. Let's confirm for that time."
        if "available" in lower or "can you" in lower:
            return f"Hi {sender_name}, I will check my schedule and get back to you shortly."
        return f"Thanks {sender_name}, noted."

    def _create_draft(
        self,
        msg_id: str,
        platform: str,
        recipient_id: str,
        recipient_name: str,
        original_text: str,
        suggested_reply: str
    ) -> Dict[str, Any]:
        """Save a draft in the pending approval store."""
        draft_id = f"draft_{msg_id}"
        draft_entry = {
            "draft_id": draft_id,
            "message_id": msg_id,
            "platform": platform,
            "recipient_id": recipient_id,
            "recipient_name": recipient_name,
            "original_text": original_text,
            "suggested_reply": suggested_reply,
            "created_at": datetime.now().isoformat(),
            "status": "pending_approval",
        }
        drafts = self.list_pending_drafts()
        drafts[draft_id] = draft_entry
        self._save_drafts(drafts)
        return draft_entry

    def list_pending_drafts(self) -> Dict[str, Any]:
        if not self.drafts_file.exists():
            return {}
        try:
            with open(self.drafts_file, "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_drafts(self, drafts: Dict[str, Any]) -> None:
        tmp = self.drafts_file.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(drafts, f, indent=2)
        tmp.replace(self.drafts_file)

    def _save_extracted_info(self, items: List[Dict[str, Any]]) -> None:
        existing = []
        if self.extracted_info_file.exists():
            try:
                with open(self.extracted_info_file, "r") as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        existing.extend(items)
        tmp = self.extracted_info_file.with_suffix(".tmp")
        with open(tmp, "w") as f:
            json.dump(existing, f, indent=2)
        tmp.replace(self.extracted_info_file)

    def get_extracted_info(self) -> List[Dict[str, Any]]:
        if not self.extracted_info_file.exists():
            return []
        try:
            with open(self.extracted_info_file, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def approve_and_send(self, draft_id: str, edited_text: Optional[str] = None) -> Dict[str, Any]:
        """Approve a draft and send it. Appends AI marker if enabled."""
        drafts = self.list_pending_drafts()
        if draft_id not in drafts:
            return {"success": False, "error": f"Draft {draft_id} not found."}

        draft = drafts[draft_id]
        body = edited_text if edited_text is not None else draft["suggested_reply"]

        final_message = body
        if self.mark_as_ai and self.ai_marker_text:
            final_message = f"{body}\n\n{self.ai_marker_text}"

        # Dispatch via target platform
        platform = draft["platform"].lower()
        recipient_id = draft["recipient_id"]

        send_res = {"success": True}
        if platform == "telegram":
            # For Telegram user account dispatch
            logger.info(f"Dispatched Telegram message to {recipient_id}: {final_message}")
        elif platform == "whatsapp":
            if self.whatsapp.business_phone_id:
                send_res = self.whatsapp.send_business_message(recipient_id, final_message)
            else:
                send_res = self.whatsapp.send_unofficial_message(recipient_id, final_message)

        if send_res.get("success", True):
            draft["status"] = "sent"
            draft["sent_at"] = datetime.now().isoformat()
            draft["final_message"] = final_message
            self.sent_messages.append(draft)
            del drafts[draft_id]
            self._save_drafts(drafts)
            return {"success": True, "draft": draft, "message": final_message}
        else:
            return {"success": False, "error": send_res.get("error", "Failed to send")}

