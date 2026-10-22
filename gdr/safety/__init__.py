"""Safety subsystem for GDR AI.
Provides secrets isolation, permission tiers, audit logging, untrusted data guards,
kill switch, and spending limits.
"""

from gdr.safety.secrets import get_secret, set_keyring_secret, mask_secret, sanitize_text
from gdr.safety.tiers import PermissionTier, classify_action
from gdr.safety.audit import log_action, get_recent_audit_logs
from gdr.safety.untrusted import wrap_untrusted_content, mark_session_tainted, is_session_tainted
from gdr.safety.panic import trigger_panic, clear_panic, is_panicked
from gdr.safety.limits import record_cost, check_spending_cap
from gdr.safety.request_db import RequestStore, get_request_store, log_inbound_request

__all__ = [
    "get_secret",
    "set_keyring_secret",
    "mask_secret",
    "sanitize_text",
    "PermissionTier",
    "classify_action",
    "log_action",
    "get_recent_audit_logs",
    "wrap_untrusted_content",
    "mark_session_tainted",
    "is_session_tainted",
    "trigger_panic",
    "clear_panic",
    "is_panicked",
    "record_cost",
    "check_spending_cap",
    "RequestStore",
    "get_request_store",
    "log_inbound_request",
]

