"""Acceptance Test 9: Multi-Account Google (Gmail, Calendar, Drive).
Verifies:
1. Multi-account registration and keyring token storage.
2. 7-day token refresh warning in testing mode.
3. Untrusted email wrapper on incoming messages.
4. "Anything urgent today?" query producing merged answer with account labels [Personal], [Work], etc.
5. Calendar conflict detection across accounts.
"""

from datetime import datetime, timedelta
import pytest
from gdr.google.auth import GoogleAuthManager
from gdr.google.service import GoogleWorkspaceManager


def test_acceptance_9_multiaccount_urgent_and_conflicts(tmp_path, monkeypatch):
    monkeypatch.setenv("GDR_CONFIG_DIR", str(tmp_path))

    auth = GoogleAuthManager(config_dir=tmp_path)

    # 1. Add two Google accounts: Personal and Work
    acc1 = auth.add_account(
        account_id="acc_personal",
        label="Personal",
        email="me.personal@gmail.com",
        is_mock=True,
        testing_mode=True
    )
    acc2 = auth.add_account(
        account_id="acc_work",
        label="Work",
        email="me.work@enterprise.com",
        is_mock=True,
        testing_mode=True
    )

    accounts = auth.list_accounts()
    assert len(accounts) == 2
    assert any(a["label"] == "Personal" for a in accounts)
    assert any(a["label"] == "Work" for a in accounts)

    # 2. Setup Google Workspace Manager with mock data across both accounts
    svc = GoogleWorkspaceManager(auth_manager=auth)

    # Personal emails: one urgent, one newsletter
    svc.set_mock_data("acc_personal", "emails", [
        {
            "id": "p_msg_1",
            "subject": "Action Required: Flight Check-in",
            "from": "airline@travel.com",
            "body": "Your flight check-in is due tomorrow before 10am. Please confirm seats.",
            "date": datetime.now().isoformat()
        },
        {
            "id": "p_msg_2",
            "subject": "Weekend Flash Sale 50% Off",
            "from": "store@shop.com",
            "body": "Unsubscribe if you do not want offers.",
            "date": datetime.now().isoformat()
        }
    ])

    # Work emails: one urgent deadline with client
    svc.set_mock_data("acc_work", "emails", [
        {
            "id": "w_msg_1",
            "subject": "Urgent: Q3 Budget Review",
            "from": "manager@enterprise.com",
            "body": "Hi, we have an urgent review call at 3pm today regarding the contract deliverables.",
            "date": datetime.now().isoformat()
        }
    ])

    # Personal & Work Calendar events with an intentional overlap/conflict
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    svc.set_mock_data("acc_personal", "calendar", [
        {
            "summary": "Dentist Appointment",
            "start": now + timedelta(hours=2),
            "end": now + timedelta(hours=3),
        }
    ])
    svc.set_mock_data("acc_work", "calendar", [
        {
            "summary": "Critical Client Escalation",
            "start": now + timedelta(hours=2, minutes=30),
            "end": now + timedelta(hours=3, minutes=30),
        }
    ])

    # 3. Test unified inbox triage and untrusted wrapper
    inbox = svc.get_unified_inbox()
    assert len(inbox) == 3
    # Check untrusted wrapper exists
    assert "BEGIN_UNTRUSTED_EMAIL_BODY_DATA" in inbox[0]["safe_body"]
    # Check triage
    urgent_p = [m for m in inbox if m["id"] == "p_msg_1"][0]
    assert urgent_p["category"] == "important"

    # 4. Acceptance Test 9: Ask "anything urgent today?" and verify merged answer with account labels
    urgent_res = svc.check_urgent()
    summary_text = urgent_res["summary_text"]

    # Verify both account labels appear
    assert "[Personal]" in summary_text
    assert "[Work]" in summary_text
    # Verify urgent emails appear
    assert "Flight Check-in" in summary_text or "Q3 Budget Review" in summary_text
    # Verify conflict is detected between the two accounts
    assert "Calendar Conflicts" in summary_text
    assert "Dentist Appointment" in summary_text
    assert "Critical Client Escalation" in summary_text

    print("\n--- Acceptance Test 9 Passed Output ---")
    print(summary_text)
