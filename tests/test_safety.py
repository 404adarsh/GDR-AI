"""Tests for GDR safety subsystem: tiers, panic, audit, and secrets."""

import os
from pathlib import Path
import pytest

from gdr.safety.tiers import classify_action, PermissionTier
import gdr.safety.panic as panic_mod
import gdr.safety.audit as audit_mod
from gdr.safety.secrets import sanitize_text, mask_secret


def test_permission_tiers():
    # Read action is AUTO
    assert classify_action("read_file", {"path": "/tmp/test.txt"}) == PermissionTier.AUTO

    # Send/delete actions are APPROVAL
    assert classify_action("delete_file", {"path": "/tmp/test.txt"}) == PermissionTier.APPROVAL
    assert classify_action("send_email", {"recipient": "a@b.com"}) == PermissionTier.APPROVAL

    # Destructive root actions are NEVER
    assert classify_action("run_shell", {"command": "rm -rf / --no-preserve-root"}) == PermissionTier.NEVER
    assert classify_action("run_privileged", {"command": ":(){ :|:& };:"}) == PermissionTier.NEVER


def test_panic_kill_switch(tmp_path, monkeypatch):
    test_lock = tmp_path / "panic.lock"
    monkeypatch.setattr(panic_mod, "PANIC_LOCK_FILE", test_lock)

    panic_mod.clear_panic()
    assert not panic_mod.is_panicked()

    msg = panic_mod.trigger_panic()
    assert "EMERGENCY STOP TRIGGERED" in msg
    assert panic_mod.is_panicked()

    panic_mod.clear_panic()
    assert not panic_mod.is_panicked()


def test_audit_logging(tmp_path, monkeypatch):
    test_audit = tmp_path / "audit.log"
    monkeypatch.setattr(audit_mod, "AUDIT_DIR", tmp_path)
    monkeypatch.setattr(audit_mod, "AUDIT_LOG_FILE", test_audit)

    audit_mod.log_action("test_audit_tool", {"arg1": "value1"}, "AUTO", "SUCCESS", "Execution ok")
    logs = audit_mod.get_recent_audit_logs(limit=10)
    assert len(logs) > 0
    last = logs[-1]
    assert last["tool"] == "test_audit_tool"
    assert last["args"]["arg1"] == "value1"
    assert last["status"] == "SUCCESS"


def test_secret_masking_and_sanitization(monkeypatch):
    monkeypatch.setenv("SARVAM_API_KEY", "sk_test_secret_123456789")
    masked = mask_secret("sk_test_secret_123456789")
    assert masked == "sk_...789"

    text = "Logging with sk_test_secret_123456789 included"
    clean = sanitize_text(text)
    assert "sk_test_secret_123456789" not in clean
    assert "[REDACTED_SARVAM_API_KEY]" in clean

