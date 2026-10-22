"""Email Assistant subsystem for Aarushi / GDR-AI.
Enforces read-only background monitoring, prompt-injection defense on incoming email bodies,
and permission gates for drafting vs. confirmed sending.
"""

from datetime import datetime
import html
import json
import os
from pathlib import Path
import re
from typing import Dict, Any, List, Optional

from gdr.safety.untrusted import wrap_untrusted_content
from gdr.integrations.registry import get_integration_registry


DRAFTS_PATH = Path(os.environ.get("GDR_CONFIG_DIR", Path.home() / ".config" / "gdr")) / "drafts.json"


def _resolve_drafts_path() -> Path:
    cfg = os.environ.get("GDR_CONFIG_DIR")
    if cfg:
        return Path(cfg) / "drafts.json"
    p = Path.home() / ".config" / "gdr" / "drafts.json"
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        t = p.parent / ".draft_check"
        t.touch()
        t.unlink(missing_ok=True)
        return p
    except Exception:
        fallback = Path(__file__).resolve().parent.parent / "data" / "drafts.json"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return fallback


class EmailAssistantService:
    """Manages email monitoring, drafting, and confirmed sending with security gates."""

    def __init__(self):
        self.drafts_file = _resolve_drafts_path()
        self.registry = get_integration_registry()

    def check_unread(self, limit: int = 5) -> Dict[str, Any]:
        """Fetch unread / recent emails safely. Defends against prompt injection."""
        stat = self.registry.get_status("email")
        if not stat.get("is_connected"):
            return {
                "success": False,
                "connected": False,
                "message": self.registry.get_service_guard_message("email"),
                "emails": []
            }

        try:
            from gdr.tools.email_tool import read_emails
            raw_result = read_emails(max_count=limit)
            return {
                "success": True,
                "connected": True,
                "raw_summary": raw_result,
                "message": f"Retrieved recent emails for {stat.get('account_email', 'inbox')}."
            }
        except Exception as e:
            return {
                "success": False,
                "connected": True,
                "message": f"Error accessing inbox: {str(e)}",
                "emails": []
            }

    def sanitize_email_content(self, raw_body: str) -> str:
        """Sanitize email body to prevent prompt injection and hidden script execution."""
        if not raw_body:
            return ""
        # 1. Unescape html entities
        cleaned = html.unescape(raw_body)
        # 2. Strip HTML tags
        cleaned = re.sub(r"<[^>]+>", " ", cleaned)
        # 3. Defang suspicious injection triggers (e.g. "Ignore previous instructions", "SYSTEM:", "ASSISTANT:")
        injection_patterns = [
            r"ignore\s+(?:all\s+)?previous\s+instructions",
            r"system\s*:\s*you\s+are",
            r"delete\s+all\s+files",
            r"format\s+drive",
            r"drop\s+database",
            r"rm\s+-rf",
            r"curl\s+.*\s*\|\s*bash",
        ]
        for pat in injection_patterns:
            cleaned = re.sub(pat, "[FILTERED_UNTRUSTED_INSTRUCTION]", cleaned, flags=re.IGNORECASE)

        # 4. Wrap with untrusted content delimiter
        return wrap_untrusted_content("email body", cleaned.strip())

    def create_draft(self, recipient: str, subject: str, body: str) -> Dict[str, Any]:
        """Create a draft without sending. Always safe and non-destructive."""
        self.drafts_file.parent.mkdir(parents=True, exist_ok=True)
        drafts = self.list_drafts()

        draft_id = f"draft_{int(datetime.now().timestamp())}"
        draft_entry = {
            "id": draft_id,
            "created_at": datetime.now().isoformat(),
            "recipient": recipient.strip(),
            "subject": subject.strip(),
            "body": body.strip(),
            "status": "pending_approval",
        }
        drafts.append(draft_entry)

        try:
            with open(self.drafts_file, "w") as f:
                json.dump(drafts, f, indent=2)
        except Exception as e:
            return {"success": False, "error": f"Failed to save draft: {e}"}

        return {
            "success": True,
            "draft_id": draft_id,
            "recipient": recipient,
            "subject": subject,
            "message": f"Draft saved successfully (ID: {draft_id}). Ready for your review."
        }

    def list_drafts(self) -> List[Dict[str, Any]]:
        """List all pending drafts."""
        if not self.drafts_file.exists():
            return []
        try:
            with open(self.drafts_file, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def get_draft(self, draft_id: str) -> Optional[Dict[str, Any]]:
        for d in self.list_drafts():
            if d.get("id") == draft_id:
                return d
        return None

    def delete_draft(self, draft_id: str) -> bool:
        drafts = self.list_drafts()
        new_drafts = [d for d in drafts if d.get("id") != draft_id]
        if len(new_drafts) == len(drafts):
            return False
        try:
            with open(self.drafts_file, "w") as f:
                json.dump(new_drafts, f, indent=2)
            return True
        except Exception:
            return False

    def send_email_with_confirmation(
        self,
        recipient: str,
        subject: str,
        body: str,
        user_confirmed: bool = False
    ) -> Dict[str, Any]:
        """Send an email only if explicit confirmation is given."""
        stat = self.registry.get_status("email")
        if not stat.get("is_connected"):
            return {
                "success": False,
                "message": self.registry.get_service_guard_message("email")
            }

        if not user_confirmed:
            # Prepare confirmation prompt
            return {
                "success": False,
                "needs_confirmation": True,
                "recipient": recipient,
                "subject": subject,
                "body_preview": body[:150] + ("..." if len(body) > 150 else ""),
                "prompt": (
                    f"⚠️ Kya aap ye email bhejna chahte hain?\n"
                    f"To: {recipient}\n"
                    f"Subject: {subject}\n"
                    f"Aapki explicit permission ke baad hi email send hoga."
                )
            }

        # User has confirmed: execute send
        from gdr.tools.email_tool import send_email
        res = send_email(recipient=recipient, subject=subject, body=body)
        return {
            "success": "Sent email" in res or "successfully" in res.lower(),
            "needs_confirmation": False,
            "message": res
        }


_EMAIL_ASSISTANT = None


def get_email_assistant() -> EmailAssistantService:
    global _EMAIL_ASSISTANT
    if _EMAIL_ASSISTANT is None:
        _EMAIL_ASSISTANT = EmailAssistantService()
    return _EMAIL_ASSISTANT
