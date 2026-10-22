"""Email management tools for blockbrain AI.
Supports reading emails via IMAP, drafting, and sending via SMTP with APPROVAL tier.
Secrets come exclusively from environment/keyring.
"""

from datetime import datetime
import email
from email.header import decode_header
import imaplib
import json
import os
from pathlib import Path
import smtplib
from typing import Dict, Any, List, Optional

from blockbrain.tools.registry import tool
from blockbrain.safety.secrets import get_secret
from blockbrain.safety.untrusted import wrap_untrusted_content

DRAFTS_FILE = Path(os.environ.get("blockbrain_CONFIG_DIR", Path.home() / ".config" / "blockbrain")) / "drafts.json"


@tool(name="read_emails", description="Read recent emails from inbox.", category="email", tier="AUTO")
def read_emails(max_count: int = 5) -> str:
    addr = get_secret("EMAIL_ADDRESS")
    pwd = get_secret("EMAIL_APP_PASSWORD")
    host = get_secret("EMAIL_IMAP_HOST", "imap.gmail.com")

    if not addr or not pwd:
        return "Email is not configured. Set EMAIL_ADDRESS and EMAIL_APP_PASSWORD in environment."

    try:
        mail = imaplib.IMAP4_SSL(host)
        mail.login(addr, pwd)
        mail.select("inbox")

        _, data = mail.search(None, "ALL")
        ids = data[0].split()
        if not ids:
            return "Inbox is empty."

        recent_ids = ids[-max_count:]
        summaries = []

        for msg_id in reversed(recent_ids):
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            subject = ""
            for sub, enc in decode_header(msg.get("Subject", "No Subject")):
                if isinstance(sub, bytes):
                    subject += sub.decode(enc or "utf-8", errors="replace")
                else:
                    subject += str(sub)

            sender = msg.get("From", "Unknown")
            date_str = msg.get("Date", "")
            summaries.append(f"• From: {sender}\n  Date: {date_str}\n  Subject: {subject}")

        mail.logout()
        return wrap_untrusted_content("inbox emails", "\n\n".join(summaries))
    except Exception as e:
        return f"Error reading email: {e}"


@tool(name="draft_email", description="Create an email draft for review. Does NOT send immediately.", category="email", tier="AUTO")
def draft_email(recipient: str, subject: str, body: str) -> str:
    """Save an email to the drafts queue for morning review or approval."""
    try:
        DRAFTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        drafts = []
        if DRAFTS_FILE.exists():
            try:
                with open(DRAFTS_FILE, "r") as f:
                    drafts = json.load(f)
            except Exception:
                drafts = []

        draft_id = f"draft_{int(datetime.now().timestamp())}"
        drafts.append({
            "id": draft_id,
            "created_at": datetime.now().isoformat(),
            "recipient": recipient,
            "subject": subject,
            "body": body,
            "status": "pending_approval",
        })

        with open(DRAFTS_FILE, "w") as f:
            json.dump(drafts, f, indent=2)

        return f"Draft '{draft_id}' saved successfully to approval queue. Recipient: {recipient}, Subject: '{subject}'."
    except Exception as e:
        return f"Error saving draft: {e}"


@tool(name="send_email", description="Send an email via SMTP. Requires APPROVAL.", category="email", tier="APPROVAL", requires_approval=True)
def send_email(recipient: str, subject: str, body: str) -> str:
    """Send email after user confirmation."""
    addr = get_secret("EMAIL_ADDRESS")
    pwd = get_secret("EMAIL_APP_PASSWORD")
    host = get_secret("EMAIL_SMTP_HOST", "smtp.gmail.com")
    port = int(get_secret("EMAIL_SMTP_PORT", "587"))

    if not addr or not pwd:
        return "Cannot send email: EMAIL_ADDRESS or EMAIL_APP_PASSWORD unset."

    try:
        from email.mime.text import MIMEText
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = addr
        msg["To"] = recipient

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(addr, pwd)
            server.send_message(msg)

        return f"Successfully sent email to {recipient} with subject '{subject}'."
    except Exception as e:
        return f"Error sending email: {e}"

