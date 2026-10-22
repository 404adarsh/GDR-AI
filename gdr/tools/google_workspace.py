"""Google Workspace tools for GDR AI."""

import json
from typing import Dict, Any, Optional

from gdr.tools.registry import tool
from gdr.google.service import GoogleWorkspaceManager

_manager: Optional[GoogleWorkspaceManager] = None


def get_google_manager() -> GoogleWorkspaceManager:
    global _manager
    if _manager is None:
        _manager = GoogleWorkspaceManager()
    return _manager


@tool(name="google_urgent_check", description="Check for urgent emails, deadlines, and calendar conflicts across all Google accounts.", category="google", tier="AUTO")
def google_urgent_check() -> str:
    mgr = get_google_manager()
    res = mgr.check_urgent()
    return res["summary_text"]


@tool(name="google_unified_inbox", description="Read recent emails across all connected Google accounts (Personal, Work, College).", category="google", tier="AUTO")
def google_unified_inbox(max_per_account: int = 5) -> str:
    mgr = get_google_manager()
    emails = mgr.get_unified_inbox(max_per_account=max_per_account)
    if not emails:
        return "No emails found across connected Google accounts."

    lines = []
    for em in emails:
        lines.append(
            f"• [{em['account_label']}] [{em['category'].upper()}] From: {em['from']}\n"
            f"  Subject: {em['subject']}\n"
            f"  Date: {em['date']}\n"
            f"  Body Preview: {em['safe_body'][:200]}..."
        )
    return "\n\n".join(lines)


@tool(name="google_merged_calendar", description="Get merged calendar schedule and detect scheduling conflicts across all Google accounts.", category="google", tier="AUTO")
def google_merged_calendar(days_ahead: int = 3) -> str:
    mgr = get_google_manager()
    cal = mgr.get_merged_calendar(days_ahead=days_ahead)

    lines = []
    if cal["conflicts"]:
        lines.append("⚠️ DETECTED CONFLICTS:")
        for c in cal["conflicts"]:
            lines.append(f"  • {c['event1']} OVERLAPS WITH {c['event2']}")
        lines.append("")

    lines.append(f"📅 UPCOMING EVENTS ({cal['total_events']}):")
    for ev in cal["events"]:
        start_str = ev["start"].strftime("%Y-%m-%d %H:%M")
        end_str = ev["end"].strftime("%H:%M")
        lines.append(f"  • [{ev['account_label']}] {start_str} - {end_str}: {ev['summary']}")

    return "\n".join(lines)


@tool(name="google_draft_reply", description="Draft an email reply. Saves draft in queue for user approval before sending.", category="google", tier="AUTO")
def google_draft_reply(account_id: str, message_id: str, reply_text: str) -> str:
    mgr = get_google_manager()
    draft = mgr.draft_reply(account_id, message_id, reply_text)
    return f"Draft created for [{draft['account_label']}] to {message_id}. Status: {draft['status']}. Body:\n{reply_text}"


@tool(name="google_list_accounts", description="List all connected Google accounts and token health status.", category="google", tier="AUTO")
def google_list_accounts() -> str:
    mgr = get_google_manager()
    accounts = mgr.auth.list_accounts()
    if not accounts:
        return "No Google accounts currently configured."

    lines = ["Connected Google Accounts:"]
    for acc in accounts:
        warn = f" [WARNING: {acc['warning']}]" if "warning" in acc else ""
        lines.append(f"• ID: {acc['id']} | Label: {acc['label']} | Email: {acc.get('email', '')} | Status: {acc.get('status', 'active')}{warn}")
    return "\n".join(lines)

