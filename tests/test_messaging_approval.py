"""Acceptance Test 10: Telegram & WhatsApp On-My-Behalf Messaging.
Verifies:
1. Incoming Telegram message triggers untrusted wrapping and response detection.
2. GDR extracts commitments/dates into long-term info store.
3. GDR drafts a reply and places it in pending approval queue.
4. Reply is NOT sent automatically.
5. Upon explicit user approval, the reply is dispatched with AI marker attached.
"""

from pathlib import Path
import pytest
from gdr.channels.user_messaging import UserMessagingManager


def test_acceptance_10_telegram_message_summary_draft_and_approval(tmp_path):
    mgr = UserMessagingManager(config_dir=tmp_path, mark_as_ai=True)

    # 1. Incoming message arrives from contact Rahul
    contact_name = "Rahul"
    incoming_text = "Hey! Are we still meeting today at 5pm to discuss the project?"

    msg_record = mgr.queue_incoming_message(
        platform="telegram",
        sender_id="user_rahul_99",
        sender_name=contact_name,
        text=incoming_text
    )

    # Verify untrusted wrapping
    assert "BEGIN_UNTRUSTED_TELEGRAM_MESSAGE_DATA" in msg_record["safe_text"]
    assert incoming_text in msg_record["safe_text"]

    # Verify response detection
    assert msg_record["needs_reply"] is True

    # 2. Verify extracted info (meeting date/time)
    extracted = mgr.get_extracted_info()
    assert len(extracted) >= 1
    assert any("5pm" in it["extracted_text"] for it in extracted)

    # 3. Verify draft was generated and placed in pending approvals
    pending = mgr.list_pending_drafts()
    assert len(pending) == 1
    draft_id = list(pending.keys())[0]
    draft = pending[draft_id]

    assert draft["status"] == "pending_approval"
    assert "sounds good" in draft["suggested_reply"].lower() or "confirm" in draft["suggested_reply"].lower()

    # 4. Verify message is NOT yet sent
    assert len(mgr.sent_messages) == 0

    # 5. User approves the draft
    result = mgr.approve_and_send(draft_id)
    assert result["success"] is True

    # Verify message has now been dispatched
    assert len(mgr.sent_messages) == 1
    sent_item = mgr.sent_messages[0]
    assert sent_item["status"] == "sent"
    assert "Sent via GDR AI assistant" in sent_item["final_message"]

    # Verify pending queue is now empty
    assert len(mgr.list_pending_drafts()) == 0

    print("\n--- Acceptance Test 10 Passed Output ---")
    print(f"Original: {incoming_text}")
    print(f"Drafted & Approved Response Sent:\n{sent_item['final_message']}")

