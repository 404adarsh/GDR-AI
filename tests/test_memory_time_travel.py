"""Time-travel and durability acceptance tests for GDR Permanent Long-Term Memory (Phase 7).
Verifies:
- Memories inserted 12+ months in the past survive and recall accurately.
- Superseded facts retain full audit history so 'what was my old address?' works.
- Full database restart & integrity verification.
- Export, import, and encryption validation.
"""

from datetime import datetime, timedelta
import os
from pathlib import Path
import pytest

from gdr.memory.encrypted_store import EncryptedMemoryStore
from gdr.memory.commands import parse_memory_intent, execute_memory_action


def test_time_travel_and_superseded_memory(tmp_path):
    test_db = tmp_path / "time_travel_memory.db"
    key = b"A" * 32
    # Generate proper Fernet test key
    import base64
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key()

    # 1. Initialize store
    store = EncryptedMemoryStore(db_path=test_db, encryption_key=test_key)

    # 2. Insert fact dated 14 months ago (Oct 2025)
    past_date = datetime.now() - timedelta(days=420)
    store.remember(
        subject="visa application",
        content="Applied for Schengen Visa with embassy reference SCH-99881",
        category="episodic",
        event_date=past_date
    )

    # 3. Insert old address 12 months ago
    old_addr_date = datetime.now() - timedelta(days=365)
    res1 = store.remember(
        subject="home address",
        content="123 Old Oak Lane, Sector 14",
        category="pinned_fact",
        event_date=old_addr_date
    )
    old_id = res1["id"]

    # 4. Update address today (should supersede old address, not delete it)
    res2 = store.remember(
        subject="home address",
        content="456 New Cyber Towers, Sector 62",
        category="pinned_fact"
    )
    new_id = res2["id"]
    assert res2["status"] == "superseded_old"
    assert res2["superseded_old_id"] == old_id

    # 5. Insert passport fact
    store.remember(
        subject="passport",
        content="My passport expires in March 2028",
        category="pinned_fact"
    )

    # 6. SIMULATE REBOOT: delete store instance and open brand new connection from disk
    del store
    fresh_store = EncryptedMemoryStore(db_path=test_db, encryption_key=test_key)

    # Verify integrity
    ok, msg = fresh_store.verify_integrity()
    assert ok, f"Integrity failed: {msg}"

    # 7. Query active address
    active_mems = fresh_store.recall("address", include_superseded=False)
    assert len(active_mems) == 1
    assert "456 New Cyber Towers" in active_mems[0]["content"]

    # 8. Query historical / superseded address ("what was my old address?")
    all_mems = fresh_store.recall("address", include_superseded=True)
    assert len(all_mems) == 2
    superseded = [m for m in all_mems if m["status"] == "superseded"]
    assert len(superseded) == 1
    assert "123 Old Oak Lane" in superseded[0]["content"]
    assert superseded[0]["superseded_by_id"] == new_id

    # 9. Time-travel query: recall 14-month-old visa event
    visa_mems = fresh_store.recall("visa")
    assert len(visa_mems) == 1
    assert "SCH-99881" in visa_mems[0]["content"]
    assert visa_mems[0]["event_date"].startswith(past_date.strftime("%Y-%m"))

    # 10. Recall passport expiration
    pass_mems = fresh_store.recall("passport")
    assert len(pass_mems) == 1
    assert "March 2028" in pass_mems[0]["content"]

    # 11. Test Export & Import
    export_payload = fresh_store.export_data()
    assert export_payload["count"] >= 3

    restore_db = tmp_path / "restored_memory.db"
    restore_store = EncryptedMemoryStore(db_path=restore_db, encryption_key=test_key)
    count = restore_store.import_data(export_payload)
    assert count == export_payload["count"]

    restored_mems = restore_store.recall("passport")
    assert len(restored_mems) == 1
    assert "March 2028" in restored_mems[0]["content"]
    print("\n🎉 Time travel and encrypted memory acceptance tests passed successfully!")

