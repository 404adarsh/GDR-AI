"""Google Workspace client for GDR AI.
Supports unified inbox, priority triage, meeting/deadline extraction,
calendar conflict detection, drafting replies, and 'anything urgent?' queries
across multiple Google accounts.
"""

from datetime import datetime, timezone, timedelta
import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple

from gdr.google.auth import GoogleAuthManager
from gdr.safety.untrusted import wrap_untrusted_content

logger = logging.getLogger("gdr.google.service")


class GoogleWorkspaceManager:
    """Aggregates Gmail, Calendar, Drive, and Contacts across multiple accounts."""

    def __init__(self, auth_manager: Optional[GoogleAuthManager] = None):
        self.auth = auth_manager or GoogleAuthManager()
        # In-memory mock store for simulated or test accounts
        self._mock_data: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}

    def set_mock_data(self, account_id: str, data_type: str, items: List[Dict[str, Any]]) -> None:
        """Inject mock data for testing or offline usage."""
        if account_id not in self._mock_data:
            self._mock_data[account_id] = {"emails": [], "calendar": [], "drive": []}
        self._mock_data[account_id][data_type] = items

    def triage_message(self, subject: str, sender: str, body: str) -> str:
        """Classify email into: important, newsletter, spam-ish, transactional."""
        text = f"{subject} {sender} {body}".lower()

        # Spam-ish indicators
        if any(w in text for w in ["win a free", "lottery", "crypto profit", "viagra", "wire transfer", "claim your prize"]):
            return "spam-ish"

        # Newsletter / marketing
        if any(w in text for w in ["unsubscribe", "newsletter", "promotions", "view in browser", "special discount", "sale end"]):
            return "newsletter"

        # Important / Action required
        if any(w in text for w in ["urgent", "action required", "deadline", "asap", "interview", "review requested", "payment due", "contract", "offer letter", "flight"]):
            return "important"

        # Transactional
        if any(w in text for w in ["receipt", "order confirmation", "shipping update", "tracking number", "otp", "verification code"]):
            return "transactional"

        return "standard"

    def extract_deadlines_and_meetings(self, text: str) -> List[Dict[str, Any]]:
        """Extract potential deadlines, dates, and meeting promises from email text."""
        results = []
        # Pattern matching for dates/times like "tomorrow at 5pm", "Oct 24", "due Friday"
        patterns = [
            r"\b(due|deadline|by|before)\s+([A-Za-z]+ \d{1,2}|\d{1,2}/\d{1,2}|today|tomorrow|monday|tuesday|wednesday|thursday|friday)",
            r"\b(meeting|call|sync|discussion)\s+(?:at|on)\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?|[A-Za-z]+ \d{1,2})",
        ]
        for pat in patterns:
            for match in re.finditer(pat, text, re.IGNORECASE):
                results.append({
                    "type": "deadline" if "due" in match.group(0).lower() or "deadline" in match.group(0).lower() else "meeting",
                    "phrase": match.group(0),
                    "context": text[max(0, match.start() - 20) : min(len(text), match.end() + 20)].strip()
                })
        return results

    def get_unified_inbox(self, max_per_account: int = 5) -> List[Dict[str, Any]]:
        """Get recent emails from all active accounts, triaged and safely delimited."""
        accounts = self.auth.list_accounts()
        unified = []

        for acc in accounts:
            acc_id = acc["id"]
            label = acc.get("label", acc_id)
            items = []

            if acc.get("is_mock", False) or acc_id in self._mock_data:
                items = self._mock_data.get(acc_id, {}).get("emails", [])[:max_per_account]
            else:
                token = self.auth.get_token(acc_id)
                if token:
                    items = self._fetch_real_gmail(token, max_per_account)

            for email_item in items:
                subject = email_item.get("subject", "No Subject")
                sender = email_item.get("from", "Unknown")
                body = email_item.get("body", "")
                category = self.triage_message(subject, sender, body)
                deadlines = self.extract_deadlines_and_meetings(f"{subject} {body}")

                unified.append({
                    "account_id": acc_id,
                    "account_label": label,
                    "id": email_item.get("id", "msg_0"),
                    "subject": subject,
                    "from": sender,
                    "date": email_item.get("date", datetime.now().isoformat()),
                    "category": category,
                    "deadlines": deadlines,
                    # Safely wrap untrusted content to prevent prompt injection
                    "safe_body": wrap_untrusted_content("EMAIL_BODY", body),
                    "raw_body": body,
                })

        return unified

    def get_merged_calendar(self, days_ahead: int = 3) -> Dict[str, Any]:
        """Merge calendar events across accounts and detect conflicts/overlaps."""
        accounts = self.auth.list_accounts()
        all_events = []

        now = datetime.now()
        horizon = now + timedelta(days=days_ahead)

        for acc in accounts:
            acc_id = acc["id"]
            label = acc.get("label", acc_id)
            cal_items = []

            if acc.get("is_mock", False) or acc_id in self._mock_data:
                cal_items = self._mock_data.get(acc_id, {}).get("calendar", [])
            else:
                token = self.auth.get_token(acc_id)
                if token:
                    cal_items = self._fetch_real_calendar(token, days_ahead)

            for ev in cal_items:
                start_dt = ev.get("start")
                end_dt = ev.get("end")
                if isinstance(start_dt, str):
                    try:
                        start_dt = datetime.fromisoformat(start_dt)
                    except Exception:
                        start_dt = now
                if isinstance(end_dt, str):
                    try:
                        end_dt = datetime.fromisoformat(end_dt)
                    except Exception:
                        end_dt = start_dt + timedelta(hours=1)

                all_events.append({
                    "account_id": acc_id,
                    "account_label": label,
                    "summary": ev.get("summary", "Untitled Event"),
                    "start": start_dt,
                    "end": end_dt,
                    "location": ev.get("location", ""),
                })

        # Sort chronologically
        all_events.sort(key=lambda x: x["start"])

        # Detect conflicts
        conflicts = []
        for i in range(len(all_events)):
            for j in range(i + 1, len(all_events)):
                ev1 = all_events[i]
                ev2 = all_events[j]
                # If ev2 starts before ev1 ends, there is an overlap
                if ev2["start"] < ev1["end"]:
                    conflicts.append({
                        "event1": f"[{ev1['account_label']}] {ev1['summary']} ({ev1['start'].strftime('%H:%M')}-{ev1['end'].strftime('%H:%M')})",
                        "event2": f"[{ev2['account_label']}] {ev2['summary']} ({ev2['start'].strftime('%H:%M')}-{ev2['end'].strftime('%H:%M')})",
                        "date": ev1["start"].strftime("%Y-%m-%d"),
                    })

        return {
            "events": all_events,
            "conflicts": conflicts,
            "total_events": len(all_events),
        }

    def check_urgent(self) -> Dict[str, Any]:
        """Answer 'anything urgent today?' merged across all accounts."""
        inbox = self.get_unified_inbox(max_per_account=10)
        cal = self.get_merged_calendar(days_ahead=1)

        urgent_emails = [m for m in inbox if m["category"] == "important" or len(m["deadlines"]) > 0]
        conflicts = cal["conflicts"]
        today_events = [ev for ev in cal["events"] if ev["start"].date() == datetime.now().date()]

        # Generate aggregated summary with account labels
        summary_lines = []
        if not urgent_emails and not conflicts and not today_events:
            summary_lines.append("No urgent emails or calendar conflicts today. All clear!")
        else:
            if urgent_emails:
                summary_lines.append("🚨 Urgent Emails:")
                for em in urgent_emails:
                    dl_note = f" (Deadline: {em['deadlines'][0]['phrase']})" if em["deadlines"] else ""
                    summary_lines.append(f"  • [{em['account_label']}] From: {em['from']} | Subject: {em['subject']}{dl_note}")

            if conflicts:
                summary_lines.append("\n⚠️ Calendar Conflicts:")
                for c in conflicts:
                    summary_lines.append(f"  • {c['event1']} overlaps with {c['event2']}")

            if today_events:
                summary_lines.append("\n📅 Today's Schedule:")
                for ev in today_events:
                    summary_lines.append(f"  • [{ev['account_label']}] {ev['start'].strftime('%H:%M')} - {ev['summary']}")

        return {
            "urgent_emails": urgent_emails,
            "conflicts": conflicts,
            "today_events": today_events,
            "summary_text": "\n".join(summary_lines),
        }

    def draft_reply(self, account_id: str, message_id: str, reply_text: str) -> Dict[str, Any]:
        """Draft a reply to an email. Does NOT send. Returns draft object for approval."""
        account = self.auth.get_account(account_id)
        label = account.get("label", account_id) if account else account_id
        draft = {
            "draft_id": f"draft_{int(datetime.now().timestamp())}",
            "account_id": account_id,
            "account_label": label,
            "in_reply_to": message_id,
            "body": reply_text,
            "created_at": datetime.now().isoformat(),
            "status": "pending_approval",
        }
        logger.info(f"Drafted reply for {message_id} on [{label}] (pending user approval)")
        return draft

    def _fetch_real_gmail(self, token: str, limit: int) -> List[Dict[str, Any]]:
        """Fetch emails from Gmail REST API using OAuth token."""
        import urllib.request
        try:
            req = urllib.request.Request(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages?maxResults={limit}",
                headers={"Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                messages = data.get("messages", [])
                # Details can be fetched per message id
                return [{"id": m["id"], "subject": f"Google Message {m['id']}", "from": "sender@domain.com", "body": ""} for m in messages]
        except Exception as e:
            logger.warning(f"Failed to fetch real Gmail: {e}")
            return []

    def _fetch_real_calendar(self, token: str, days_ahead: int) -> List[Dict[str, Any]]:
        """Fetch events from Google Calendar REST API."""
        import urllib.request
        try:
            now_iso = datetime.now(timezone.utc).isoformat()
            req = urllib.request.Request(
                f"https://www.googleapis.com/calendar/v3/calendars/primary/events?timeMin={now_iso}&maxResults=10",
                headers={"Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("items", [])
                events = []
                for it in items:
                    events.append({
                        "summary": it.get("summary", "Meeting"),
                        "start": it.get("start", {}).get("dateTime", datetime.now().isoformat()),
                        "end": it.get("end", {}).get("dateTime", datetime.now().isoformat()),
                    })
                return events
        except Exception as e:
            logger.warning(f"Failed to fetch real Calendar: {e}")
            return []
